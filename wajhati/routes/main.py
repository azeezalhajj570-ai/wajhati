from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from wajhati import db
from wajhati.models import Destination, Favorite, Itinerary, ItineraryItem, Review
from wajhati.services.recommender import generate_itinerary, match_destinations

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    featured = Destination.query.order_by(Destination.created_at.desc()).limit(6).all()
    return render_template("index.html", destinations=featured)


@main_bp.route("/destinations")
def destinations():
    city = request.args.get("city", "").strip()
    category = request.args.get("category", "").strip()

    query = Destination.query
    if city:
        query = query.filter(Destination.city.ilike(f"%{city}%"))
    if category:
        query = query.filter(Destination.category.ilike(f"%{category}%"))

    data = query.order_by(Destination.name.asc()).all()
    return render_template("destinations.html", destinations=data, city=city, category=category)


@main_bp.route("/destinations/<int:destination_id>", methods=["GET", "POST"])
def destination_detail(destination_id):
    destination = Destination.query.get_or_404(destination_id)

    if request.method == "POST":
        if not current_user.is_authenticated:
            flash("Please log in to post a review.", "warning")
            return redirect(url_for("auth.login"))

        rating = int(request.form.get("rating", 0))
        comment = request.form.get("comment", "").strip()

        if rating < 1 or rating > 5 or not comment:
            flash("Provide a valid rating and comment.", "danger")
        else:
            review = Review(
                user_id=current_user.id,
                destination_id=destination.id,
                rating=rating,
                comment=comment,
            )
            db.session.add(review)
            db.session.commit()
            flash("Review submitted.", "success")
            return redirect(url_for("main.destination_detail", destination_id=destination.id))

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
    destination = Destination.query.get_or_404(destination_id)
    favorite = Favorite.query.filter_by(user_id=current_user.id, destination_id=destination.id).first()

    if favorite:
        db.session.delete(favorite)
        flash("Removed from favorites.", "info")
    else:
        db.session.add(Favorite(user_id=current_user.id, destination_id=destination.id))
        flash("Added to favorites.", "success")
    db.session.commit()
    return redirect(url_for("main.destination_detail", destination_id=destination.id))


@main_bp.route("/itinerary/new", methods=["GET", "POST"])
@login_required
def create_itinerary():
    if request.method == "POST":
        city = request.form.get("destination_city", "").strip()
        duration_days = int(request.form.get("duration_days", 1))
        budget = float(request.form.get("budget", 0))
        trip_type = request.form.get("trip_type", "leisure").strip().lower()
        interests = [item.strip() for item in request.form.get("interests", "").split(",") if item.strip()]

        destinations = Destination.query.all()
        matched = match_destinations(destinations, city=city, budget=budget, interests=interests)
        generated = generate_itinerary(
            matched,
            duration_days=duration_days,
            budget=budget,
            trip_type=trip_type,
            interests=interests,
        )

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
        flash("Itinerary generated successfully.", "success")
        return redirect(url_for("main.itinerary_detail", itinerary_id=itinerary.id))

    return render_template("create_itinerary.html")


@main_bp.route("/itineraries/<int:itinerary_id>")
@login_required
def itinerary_detail(itinerary_id):
    itinerary = Itinerary.query.get_or_404(itinerary_id)
    if itinerary.user_id != current_user.id:
        flash("Access denied.", "danger")
        return redirect(url_for("main.index"))
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
