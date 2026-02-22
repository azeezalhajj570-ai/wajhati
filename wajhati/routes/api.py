from flask import Blueprint, jsonify, request
from flask_login import current_user

from wajhati import db
from wajhati.models import Destination, Itinerary, ItineraryItem, Review
from wajhati.services.recommender import generate_itinerary, match_destinations

api_bp = Blueprint("api", __name__)


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
    duration_days = int(payload.get("duration_days", 1))
    budget = float(payload.get("budget", 0))
    trip_type = str(payload.get("trip_type", "leisure")).strip().lower()
    interests = payload.get("interests", [])

    if isinstance(interests, str):
        interests = [item.strip() for item in interests.split(",") if item.strip()]

    if not city:
        return jsonify({"error": "destination_city is required"}), 400
    if duration_days < 1:
        return jsonify({"error": "duration_days must be >= 1"}), 400
    if budget < 0:
        return jsonify({"error": "budget must be >= 0"}), 400

    destinations = Destination.query.all()
    matched = match_destinations(destinations, city=city, budget=budget, interests=interests)
    generated = generate_itinerary(matched, duration_days, budget, trip_type, interests)

    response = {
        "destination_city": city,
        "duration_days": duration_days,
        "budget": budget,
        "trip_type": trip_type,
        "interests": interests,
        "estimated_total_cost": generated["estimated_total_cost"],
        "items": generated["items"],
    }

    save = bool(payload.get("save", False))
    if save and current_user.is_authenticated:
        itinerary = Itinerary(
            user_id=current_user.id,
            destination_city=city,
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
