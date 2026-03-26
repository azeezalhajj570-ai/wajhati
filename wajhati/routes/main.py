from urllib.parse import parse_qs, urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from wajhati import db
from wajhati.models import Destination, Favorite, Itinerary, ItineraryItem, Review
from wajhati.services.recommender import generate_itinerary, match_destinations

main_bp = Blueprint("main", __name__)

TRIP_TYPES = ("family", "adventure", "cultural", "leisure")


def _get_ui_lang():
    lang = request.args.get("lang") or request.form.get("lang")
    if not lang and request.referrer:
        lang = parse_qs(urlparse(request.referrer).query).get("lang", [None])[0]
    lang = lang or "ar"
    return lang if lang in ("ar", "en") else "ar"


def _parse_interests(raw_value):
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


def _build_itinerary_form_data(form=None):
    form = form or {}
    return {
        "destination_city": str(form.get("destination_city", "")).strip(),
        "duration_days": str(form.get("duration_days", "3")).strip() or "3",
        "budget": str(form.get("budget", "2500")).strip() or "2500",
        "trip_type": str(form.get("trip_type", "leisure")).strip().lower() or "leisure",
        "interests": str(form.get("interests", "")).strip(),
    }


def _validate_itinerary_form(form_data, available_cities):
    errors = []

    city = form_data["destination_city"]
    if not city:
        errors.append("Please choose a destination city.")
    elif city not in available_cities:
        errors.append("Please choose a destination city from the available list.")

    try:
        duration_days = int(form_data["duration_days"])
        if duration_days < 1 or duration_days > 7:
            errors.append("Trip duration must be between 1 and 7 days.")
    except ValueError:
        duration_days = 3
        errors.append("Trip duration must be a valid number.")

    try:
        budget = float(form_data["budget"])
        if budget <= 0:
            errors.append("Budget must be greater than 0.")
    except ValueError:
        budget = 0
        errors.append("Budget must be a valid number.")

    trip_type = form_data["trip_type"]
    if trip_type not in TRIP_TYPES:
        errors.append("Trip type is invalid.")

    interests = _parse_interests(form_data["interests"])

    return {
        "city": city,
        "duration_days": duration_days,
        "budget": budget,
        "trip_type": trip_type,
        "interests": interests,
        "errors": errors,
    }


@main_bp.route("/")
def index():
    featured = Destination.query.order_by(Destination.created_at.desc()).limit(6).all()
    recent_itineraries = []
    itinerary_count = 0
    favorites_count = 0
    reviews_count = 0

    if current_user.is_authenticated:
        recent_itineraries = (
            Itinerary.query.filter_by(user_id=current_user.id)
            .order_by(Itinerary.created_at.desc())
            .limit(3)
            .all()
        )
        itinerary_count = Itinerary.query.filter_by(user_id=current_user.id).count()
        favorites_count = Favorite.query.filter_by(user_id=current_user.id).count()
        reviews_count = Review.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "index.html",
        destinations=featured,
        recent_itineraries=recent_itineraries,
        itinerary_count=itinerary_count,
        favorites_count=favorites_count,
        reviews_count=reviews_count,
    )


@main_bp.route("/destinations")
def destinations():
    city = request.args.get("city", "").strip()
    category = request.args.get("category", "").strip()
    cities = [
        row[0]
        for row in db.session.query(Destination.city)
        .filter(Destination.city.isnot(None))
        .distinct()
        .order_by(Destination.city.asc())
        .all()
    ]
    categories = [
        row[0]
        for row in db.session.query(Destination.category)
        .filter(Destination.category.isnot(None))
        .distinct()
        .order_by(Destination.category.asc())
        .all()
    ]

    if city and city not in cities:
        city = ""
    if category and category not in categories:
        category = ""

    query = Destination.query
    if city:
        query = query.filter(Destination.city == city)
    if category:
        query = query.filter(Destination.category == category)

    data = query.order_by(Destination.name.asc()).all()
    return render_template(
        "destinations.html",
        destinations=data,
        city=city,
        category=category,
        cities=cities,
        categories=categories,
    )


@main_bp.route("/destinations/<int:destination_id>", methods=["GET", "POST"])
def destination_detail(destination_id):
    destination = Destination.query.get_or_404(destination_id)
    lang = _get_ui_lang()

    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("يرجى تسجيل الدخول لإضافة تقييم.", "warning")
            return redirect(url_for("auth.login", lang=lang))

        try:
            rating = int(request.form.get("rating", 0))
        except ValueError:
            rating = 0
        comment = request.form.get("comment", "").strip()

        if rating < 1 or rating > 5 or not comment:
            flash("يرجى إدخال تقييم وتعليق صالحين.", "danger")
        else:
            review = Review(
                user_id=current_user.id,
                destination_id=destination.id,
                rating=rating,
                comment=comment,
            )
            db.session.add(review)
            db.session.commit()
            flash("تم إرسال التقييم بنجاح.", "success")
            return redirect(url_for("main.destination_detail", destination_id=destination.id, lang=lang))

    reviews = Review.query.filter_by(destination_id=destination.id).order_by(Review.created_at.desc()).all()
    is_favorite = False
    if current_user.is_authenticated:
        is_favorite = Favorite.query.filter_by(
            user_id=current_user.id, destination_id=destination.id
        ).first() is not None
    return render_template(
        "destination_detail.html",
        destination=destination,
        reviews=reviews,
        is_favorite=is_favorite,
    )


@main_bp.route("/favorites/toggle/<int:destination_id>", methods=["POST"])
@login_required
def toggle_favorite(destination_id):
    lang = _get_ui_lang()
    destination = Destination.query.get_or_404(destination_id)
    favorite = Favorite.query.filter_by(user_id=current_user.id, destination_id=destination.id).first()

    if favorite:
        db.session.delete(favorite)
        flash("تمت الإزالة من المفضلة.", "info")
    else:
        db.session.add(Favorite(user_id=current_user.id, destination_id=destination.id))
        flash("تمت الإضافة إلى المفضلة.", "success")
    db.session.commit()
    return redirect(url_for("main.destination_detail", destination_id=destination.id, lang=lang))


@main_bp.route("/itinerary/new", methods=["GET", "POST"])
@login_required
def create_itinerary():
    lang = _get_ui_lang()
    cities = [
        row[0]
        for row in db.session.query(Destination.city)
        .distinct()
        .order_by(Destination.city.asc())
        .all()
    ]
    suggested_interests = [
        row[0]
        for row in db.session.query(Destination.category)
        .filter(Destination.category.isnot(None))
        .distinct()
        .order_by(Destination.category.asc())
        .all()
    ]
    form_data = _build_itinerary_form_data(request.form if request.method == "POST" else None)

    if request.method == "POST":
        parsed = _validate_itinerary_form(form_data, cities)
        for error in parsed["errors"]:
            flash(error, "danger")
        if parsed["errors"]:
            return render_template(
                "create_itinerary.html",
                cities=cities,
                suggested_interests=suggested_interests,
                form_data=form_data,
                trip_types=TRIP_TYPES,
            )

        destinations = Destination.query.all()
        matched = match_destinations(
            destinations,
            city=parsed["city"],
            budget=parsed["budget"],
            interests=parsed["interests"],
        )
        if not matched:
            flash("No destinations matched your current preferences. Try a different city, budget, or interests.", "warning")
            return render_template(
                "create_itinerary.html",
                cities=cities,
                suggested_interests=suggested_interests,
                form_data=form_data,
                trip_types=TRIP_TYPES,
            )

        generated = generate_itinerary(
            matched,
            duration_days=parsed["duration_days"],
            budget=parsed["budget"],
            trip_type=parsed["trip_type"],
            interests=parsed["interests"],
        )
        if not generated["items"]:
            flash("We could not generate an itinerary from the selected preferences.", "warning")
            return render_template(
                "create_itinerary.html",
                cities=cities,
                suggested_interests=suggested_interests,
                form_data=form_data,
                trip_types=TRIP_TYPES,
            )

        itinerary = Itinerary(
            user_id=current_user.id,
            destination_city=parsed["city"],
            trip_type=parsed["trip_type"],
            duration_days=parsed["duration_days"],
            budget=parsed["budget"],
            interests=", ".join(parsed["interests"]),
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
        flash("تم إنشاء خطة الرحلة بنجاح.", "success")
        return redirect(url_for("main.itinerary_detail", itinerary_id=itinerary.id))

    return render_template(
        "create_itinerary.html",
        cities=cities,
        suggested_interests=suggested_interests,
        form_data=form_data,
        trip_types=TRIP_TYPES,
    )


@main_bp.route("/itineraries/<int:itinerary_id>")
@login_required
def itinerary_detail(itinerary_id):
    lang = _get_ui_lang()
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    if itinerary.user_id != current_user.id:
        flash("غير مسموح بالوصول.", "danger")
        return redirect(url_for("main.index", lang=lang))
    items = (
        ItineraryItem.query.filter_by(itinerary_id=itinerary.id)
        .order_by(ItineraryItem.day_number.asc(), ItineraryItem.id.asc())
        .all()
    )
    return render_template("itinerary_detail.html", itinerary=itinerary, items=items)


@main_bp.route("/my-itineraries")
@login_required
def my_itineraries():
    data = Itinerary.query.filter_by(user_id=current_user.id).order_by(Itinerary.created_at.desc()).all()
    return render_template("my_itineraries.html", itineraries=data)


@main_bp.route("/itineraries/<int:itinerary_id>/delete", methods=["POST"])
@login_required
def delete_itinerary(itinerary_id):
    lang = _get_ui_lang()
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    if itinerary.user_id != current_user.id:
        flash("You are not allowed to delete this itinerary.", "danger")
        return redirect(url_for("main.index", lang=lang))

    db.session.delete(itinerary)
    db.session.commit()
    flash("Itinerary deleted successfully.", "info")
    return redirect(url_for("main.my_itineraries", lang=lang))


@main_bp.route("/map")
def map_screen():
    city = request.args.get("city", "").strip()
    cities = [
        row[0]
        for row in db.session.query(Destination.city)
        .filter(Destination.city.isnot(None))
        .distinct()
        .order_by(Destination.city.asc())
        .all()
    ]
    if city and city not in cities:
        city = ""

    query = Destination.query.filter(
        Destination.latitude.isnot(None),
        Destination.longitude.isnot(None),
    )
    if city:
        query = query.filter(Destination.city == city)

    destinations = query.order_by(Destination.name.asc()).all()
    map_destinations = [
        {
            "id": destination.id,
            "name": destination.name,
            "city": destination.city,
            "category": destination.category,
            "description": destination.description,
            "estimated_cost": destination.estimated_cost,
            "latitude": destination.latitude,
            "longitude": destination.longitude,
            "season": destination.season,
            "detail_url": url_for(
                "main.destination_detail",
                destination_id=destination.id,
                lang=request.args.get("lang", "ar"),
            ),
        }
        for destination in destinations
    ]
    return render_template(
        "map.html",
        cities=cities,
        city=city,
        map_destinations=map_destinations,
    )
