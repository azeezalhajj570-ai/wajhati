from flask import Blueprint, jsonify, request
from flask_login import current_user

from wajhati import db
from wajhati.models import Destination, Itinerary, ItineraryItem, Review
from wajhati.services.recommender import generate_itinerary, get_ai_settings, match_destinations

api_bp = Blueprint("api", __name__)

TRIP_TYPES = {"family", "adventure", "cultural", "leisure"}


def _parse_interests(raw_value):
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


def _current_user_profile_context():
    if not current_user.is_authenticated:
        return {"age_range": "", "gender": "", "favorite_tags": []}
    return {
        "age_range": current_user.age_range or "",
        "gender": current_user.gender or "",
        "favorite_tags": current_user.favorite_tags_list(),
    }


@api_bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "wajhati-api"})


@api_bp.get("/destinations")
def get_destinations():
    city = request.args.get("city")
    category = request.args.get("category")

    query = Destination.query
    if city:
        query = query.filter(Destination.city.ilike(f"%{city}%"))
    if category:
        query = query.filter(Destination.category.ilike(f"%{category}%"))

    data = [
        {
            "id": d.id,
            "name": d.name,
            "city": d.city,
            "category": d.category,
            "description": d.description,
            "estimated_cost": d.estimated_cost,
            "latitude": d.latitude,
            "longitude": d.longitude,
            "season": d.season,
        }
        for d in query.order_by(Destination.name.asc()).all()
    ]
    return jsonify(data)


@api_bp.post("/itineraries/generate")
def api_generate_itinerary():
    payload = request.get_json(silent=True) or {}
    city = str(payload.get("destination_city", "")).strip()
    trip_type = str(payload.get("trip_type", "leisure")).strip().lower()
    interests = _parse_interests(payload.get("interests", []))

    try:
        duration_days = int(payload.get("duration_days", 1))
    except (TypeError, ValueError):
        return jsonify({"error": "duration_days must be an integer"}), 400
    if duration_days < 1 or duration_days > 7:
        return jsonify({"error": "duration_days must be between 1 and 7"}), 400

    try:
        budget = float(payload.get("budget", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "budget must be a number"}), 400
    if budget <= 0:
        return jsonify({"error": "budget must be greater than 0"}), 400
    if trip_type not in TRIP_TYPES:
        return jsonify({"error": "trip_type is invalid"}), 400

    destinations = Destination.query.all()
    profile_context = _current_user_profile_context()
    matched = match_destinations(destinations, city=city, budget=budget, interests=interests, profile_context=profile_context)
    if not matched:
        return jsonify({"error": "No destinations matched the selected preferences"}), 404

    generated = generate_itinerary(
        matched,
        duration_days,
        budget,
        trip_type,
        interests,
        profile_context=profile_context,
        ai_settings=get_ai_settings(),
    )
    if not generated["items"]:
        return jsonify({"error": "Unable to generate itinerary items"}), 422

    response = {
        "destination_city": city,
        "duration_days": duration_days,
        "budget": budget,
        "trip_type": trip_type,
        "interests": interests,
        "profile_context": profile_context,
        "estimated_total_cost": generated["estimated_total_cost"],
        "items": generated["items"],
    }

    save = bool(payload.get("save", False))
    if save and current_user.is_authenticated:
        itinerary = Itinerary(
            user_id=current_user.id,
            destination_city=city or "Flexible",
            trip_type=trip_type,
            duration_days=duration_days,
            budget=budget,
            interests=", ".join(interests),
            estimated_total_cost=generated["estimated_total_cost"],
        )
        db.session.add(itinerary)
        db.session.flush()
        for item in generated["items"]:
            db.session.add(
                ItineraryItem(
                    itinerary_id=itinerary.id,
                    day_number=item["day_number"],
                    title=item["title"],
                    notes=item["notes"],
                    estimated_cost=item["estimated_cost"],
                )
            )
        db.session.commit()
        response["saved_itinerary_id"] = itinerary.id

    return jsonify(response)


@api_bp.get("/destinations/<int:destination_id>/reviews")
def get_reviews(destination_id):
    Destination.query.get_or_404(destination_id)
    reviews = Review.query.filter_by(destination_id=destination_id).order_by(Review.created_at.desc()).all()
    return jsonify(
        [
            {
                "id": review.id,
                "user": review.user.name,
                "rating": review.rating,
                "comment": review.comment,
                "created_at": review.created_at.isoformat(),
            }
            for review in reviews
        ]
    )
