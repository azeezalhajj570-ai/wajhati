from urllib.parse import parse_qs, urlparse

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from wajhati import db
from wajhati.models import Attraction, Destination, Favorite, Itinerary, ItineraryItem, Review, User
from wajhati.services.recommender import generate_itinerary, match_destinations
from wajhati.translations import SAUDI_CITIES, tr_category, tr_city, tr_destination, tr_season

main_bp = Blueprint("main", __name__)

TRIP_TYPES = ("family", "adventure", "cultural", "leisure")
AGE_RANGE_OPTIONS = ("under_18", "18_24", "25_34", "35_44", "45_54", "55_plus")
GENDER_OPTIONS = ("male", "female")
PROFILE_TAG_OPTIONS = (
    "cultural",
    "history",
    "museums",
    "art",
    "food",
    "shopping",
    "nature",
    "adventure",
    "family",
    "beaches",
    "nightlife",
    "wellness",
    "photography",
    "luxury",
    "budget",
    "road_trips",
    "camping",
    "wildlife",
    "romantic",
    "leisure",
)
DESTINATION_SEASONS = ("all", "winter", "spring", "summer", "autumn")


def _get_ui_lang():
    lang = request.args.get("lang") or request.form.get("lang")
    if not lang and request.referrer:
        lang = parse_qs(urlparse(request.referrer).query).get("lang", [None])[0]
    lang = lang or "ar"
    return lang if lang in ("ar", "en") else "ar"


def _parse_interests(raw_value):
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


def _ui_text(ar, en, lang=None):
    lang = lang or _get_ui_lang()
    return ar if lang == "ar" else en


def _require_admin():
    if not current_user.is_authenticated:
        abort(401)
    if not getattr(current_user, "is_admin", False):
        abort(403)


def _parse_profile_tags(raw_values, manual_value=""):
    tags = []
    seen = set()
    for raw in list(raw_values or []) + _parse_interests(manual_value):
        normalized = raw.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        tags.append(normalized)
    return tags


def _build_profile_form_data(form=None, user=None):
    form = form or {}
    if form:
        selected_tags = _parse_profile_tags(form.getlist("favorite_tags"), form.get("favorite_tags_custom", ""))
        age_range = str(form.get("age_range", "")).strip()
        gender = str(form.get("gender", "")).strip()
    else:
        selected_tags = user.favorite_tags_list() if user else []
        age_range = (user.age_range or "") if user else ""
        gender = (user.gender or "") if user else ""

    custom_tags = [tag for tag in selected_tags if tag not in PROFILE_TAG_OPTIONS]
    return {
        "age_range": age_range,
        "gender": gender,
        "favorite_tags": selected_tags,
        "favorite_tags_custom": ", ".join(custom_tags),
    }


def _validate_profile_form(form_data):
    errors = []
    age_range = form_data["age_range"]
    gender = form_data["gender"]

    if age_range and age_range not in AGE_RANGE_OPTIONS:
        errors.append(("يرجى اختيار فئة عمرية صحيحة.", "Please choose a valid age range."))
    if gender and gender not in GENDER_OPTIONS:
        errors.append(("يرجى اختيار نوع صحيح.", "Please choose a valid gender option."))
    return {
        "age_range": age_range,
        "gender": gender,
        "favorite_tags": form_data["favorite_tags"],
        "errors": errors,
    }


def _user_profile_context(user):
    if not user or not getattr(user, "is_authenticated", False):
        return {"age_range": "", "gender": "", "favorite_tags": []}
    return {
        "age_range": user.age_range or "",
        "gender": user.gender or "",
        "favorite_tags": user.favorite_tags_list(),
    }


def _build_itinerary_form_data(form=None):
    form = form or {}
    return {
        "destination_city": str(form.get("destination_city", "")).strip(),
        "duration_days": str(form.get("duration_days", "3")).strip() or "3",
        "budget": str(form.get("budget", "2500")).strip() or "2500",
        "trip_type": str(form.get("trip_type", "leisure")).strip().lower() or "leisure",
        "interests": str(form.get("interests", "")).strip(),
    }


def _build_destination_form_data(form=None):
    form = form or {}
    return {
        "name": str(form.get("name", "")).strip(),
        "city": str(form.get("city", "")).strip(),
        "category": str(form.get("category", "")).strip().lower(),
        "description": str(form.get("description", "")).strip(),
        "estimated_cost": str(form.get("estimated_cost", "")).strip(),
        "latitude": str(form.get("latitude", "")).strip(),
        "longitude": str(form.get("longitude", "")).strip(),
        "season": str(form.get("season", "all")).strip().lower() or "all",
    }


def _build_attraction_form_data(form=None):
    form = form or {}
    return {
        "destination_id": str(form.get("destination_id", "")).strip(),
        "name": str(form.get("name", "")).strip(),
        "category": str(form.get("category", "")).strip().lower(),
        "description": str(form.get("description", "")).strip(),
        "entry_cost": str(form.get("entry_cost", "")).strip(),
        "duration_hours": str(form.get("duration_hours", "")).strip(),
        "latitude": str(form.get("latitude", "")).strip(),
        "longitude": str(form.get("longitude", "")).strip(),
    }


def _validate_destination_form(form_data, available_cities):
    errors = []

    if not form_data["name"]:
        errors.append(("يرجى إدخال اسم الوجهة.", "Please enter a destination name."))

    city = form_data["city"]
    if not city:
        errors.append(("يرجى اختيار مدينة.", "Please choose a city."))
    elif city not in available_cities:
        errors.append(("يرجى اختيار مدينة من القائمة المتاحة.", "Please choose a city from the available list."))

    category = form_data["category"]
    if category not in {"cultural", "leisure", "adventure", "nature"}:
        errors.append(("يرجى اختيار فئة صحيحة.", "Please choose a valid category."))

    if not form_data["description"]:
        errors.append(("يرجى إدخال وصف الوجهة.", "Please enter a destination description."))

    try:
        estimated_cost = float(form_data["estimated_cost"])
        if estimated_cost < 0:
            errors.append(("يجب أن تكون التكلفة التقديرية 0 أو أكثر.", "Estimated cost must be 0 or greater."))
    except ValueError:
        estimated_cost = 0.0
        errors.append(("يرجى إدخال تكلفة تقديرية صالحة.", "Please enter a valid estimated cost."))

    latitude = None
    if form_data["latitude"]:
        try:
            latitude = float(form_data["latitude"])
        except ValueError:
            errors.append(("يرجى إدخال خط عرض صالح.", "Please enter a valid latitude."))

    longitude = None
    if form_data["longitude"]:
        try:
            longitude = float(form_data["longitude"])
        except ValueError:
            errors.append(("يرجى إدخال خط طول صالح.", "Please enter a valid longitude."))

    season = form_data["season"]
    if season not in DESTINATION_SEASONS:
        errors.append(("يرجى اختيار موسم صالح.", "Please choose a valid season."))

    return {
        "name": form_data["name"],
        "city": city,
        "category": category,
        "description": form_data["description"],
        "estimated_cost": estimated_cost,
        "latitude": latitude,
        "longitude": longitude,
        "season": season,
        "errors": errors,
    }


def _validate_attraction_form(form_data, destinations):
    errors = []
    destination_ids = {str(destination.id): destination for destination in destinations}

    if form_data["destination_id"] not in destination_ids:
        errors.append(("يرجى اختيار وجهة صالحة.", "Please choose a valid destination."))
    if not form_data["name"]:
        errors.append(("يرجى إدخال اسم النشاط أو المعلم.", "Please enter an attraction name."))
    if not form_data["category"]:
        errors.append(("يرجى إدخال فئة النشاط.", "Please enter an attraction category."))
    if not form_data["description"]:
        errors.append(("يرجى إدخال وصف النشاط.", "Please enter an attraction description."))

    try:
        entry_cost = float(form_data["entry_cost"] or 0)
        if entry_cost < 0:
            errors.append(("يجب أن تكون تكلفة الدخول 0 أو أكثر.", "Entry cost must be 0 or greater."))
    except ValueError:
        entry_cost = 0.0
        errors.append(("يرجى إدخال تكلفة دخول صالحة.", "Please enter a valid entry cost."))

    try:
        duration_hours = float(form_data["duration_hours"] or 2)
        if duration_hours <= 0:
            errors.append(("يجب أن تكون مدة النشاط أكبر من 0.", "Duration must be greater than 0."))
    except ValueError:
        duration_hours = 2.0
        errors.append(("يرجى إدخال مدة صالحة.", "Please enter a valid duration."))

    latitude = None
    if form_data["latitude"]:
        try:
            latitude = float(form_data["latitude"])
        except ValueError:
            errors.append(("يرجى إدخال خط عرض صالح.", "Please enter a valid latitude."))

    longitude = None
    if form_data["longitude"]:
        try:
            longitude = float(form_data["longitude"])
        except ValueError:
            errors.append(("يرجى إدخال خط طول صالح.", "Please enter a valid longitude."))

    return {
        "destination_id": int(form_data["destination_id"]) if form_data["destination_id"] in destination_ids else None,
        "name": form_data["name"],
        "category": form_data["category"],
        "description": form_data["description"],
        "entry_cost": entry_cost,
        "duration_hours": duration_hours,
        "latitude": latitude,
        "longitude": longitude,
        "errors": errors,
    }


def _available_cities():
    db_cities = [
        row[0]
        for row in db.session.query(Destination.city)
        .filter(Destination.city.isnot(None))
        .distinct()
        .order_by(Destination.city.asc())
        .all()
    ]
    return sorted(dict.fromkeys([*SAUDI_CITIES, *db_cities]))


def _validate_itinerary_form(form_data, available_cities):
    errors = []

    city = form_data["destination_city"]
    if not city:
        errors.append(("يرجى اختيار مدينة الوجهة.", "Please choose a destination city."))
    elif city not in available_cities:
        errors.append(("يرجى اختيار مدينة وجهة من القائمة المتاحة.", "Please choose a destination city from the available list."))

    try:
        duration_days = int(form_data["duration_days"])
        if duration_days < 1 or duration_days > 7:
            errors.append(("يجب أن تكون مدة الرحلة بين يوم واحد و7 أيام.", "Trip duration must be between 1 and 7 days."))
    except ValueError:
        duration_days = 3
        errors.append(("يجب أن تكون مدة الرحلة رقمًا صالحًا.", "Trip duration must be a valid number."))

    try:
        budget = float(form_data["budget"])
        if budget <= 0:
            errors.append(("يجب أن تكون الميزانية أكبر من 0.", "Budget must be greater than 0."))
    except ValueError:
        budget = 0
        errors.append(("يجب أن تكون الميزانية رقمًا صالحًا.", "Budget must be a valid number."))

    trip_type = form_data["trip_type"]
    if trip_type not in TRIP_TYPES:
        errors.append(("نوع الرحلة غير صالح.", "Trip type is invalid."))

    interests = _parse_interests(form_data["interests"])

    return {
        "city": city,
        "duration_days": duration_days,
        "budget": budget,
        "trip_type": trip_type,
        "interests": interests,
        "errors": errors,
    }


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    lang = _get_ui_lang()
    form_data = _build_profile_form_data(request.form if request.method == "POST" else None, current_user)

    if request.method == "POST":
        parsed = _validate_profile_form(form_data)
        for error in parsed["errors"]:
            flash(_ui_text(error[0], error[1], lang), "danger")
        if parsed["errors"]:
            return render_template(
                "profile.html",
                form_data=form_data,
                age_range_options=AGE_RANGE_OPTIONS,
                gender_options=GENDER_OPTIONS,
                profile_tag_options=PROFILE_TAG_OPTIONS,
            )

        current_user.age_range = parsed["age_range"] or None
        current_user.gender = parsed["gender"] or None
        current_user.favorite_tags = ", ".join(parsed["favorite_tags"])
        db.session.commit()
        flash(_ui_text("تم تحديث الملف الشخصي بنجاح.", "Profile updated successfully.", lang), "success")
        return redirect(url_for("main.profile", lang=lang))

    return render_template(
        "profile.html",
        form_data=form_data,
        age_range_options=AGE_RANGE_OPTIONS,
        gender_options=GENDER_OPTIONS,
        profile_tag_options=PROFILE_TAG_OPTIONS,
    )


@main_bp.route("/admin/destinations", methods=["GET", "POST"])
@login_required
def admin_destinations():
    _require_admin()
    lang = _get_ui_lang()
    cities = _available_cities()
    form_data = _build_destination_form_data(request.form if request.method == "POST" else None)

    if request.method == "POST":
        parsed = _validate_destination_form(form_data, cities)
        for error in parsed["errors"]:
            flash(_ui_text(error[0], error[1], lang), "danger")
        if not parsed["errors"]:
            destination = Destination(
                name=parsed["name"],
                city=parsed["city"],
                category=parsed["category"],
                description=parsed["description"],
                estimated_cost=parsed["estimated_cost"],
                latitude=parsed["latitude"],
                longitude=parsed["longitude"],
                season=parsed["season"],
            )
            db.session.add(destination)
            db.session.commit()
            flash(_ui_text("تمت إضافة الوجهة بنجاح.", "Destination added successfully.", lang), "success")
            return redirect(url_for("main.admin_destinations", lang=lang))

    destinations = Destination.query.order_by(Destination.created_at.desc()).all()
    return render_template(
        "admin_destinations.html",
        destinations=destinations,
        form_data=form_data,
        cities=cities,
        seasons=DESTINATION_SEASONS,
        dashboard_stats={
            "destinations": Destination.query.count(),
            "attractions": Attraction.query.count(),
            "users": User.query.count(),
            "reviews": Review.query.count(),
        },
    )


@main_bp.route("/admin", methods=["GET"])
@login_required
def admin_dashboard():
    _require_admin()
    lang = _get_ui_lang()
    return render_template(
        "admin_dashboard.html",
        dashboard_stats={
            "destinations": Destination.query.count(),
            "attractions": Attraction.query.count(),
            "users": User.query.count(),
            "reviews": Review.query.count(),
            "itineraries": Itinerary.query.count(),
        },
        latest_destinations=Destination.query.order_by(Destination.created_at.desc()).limit(5).all(),
        latest_attractions=Attraction.query.order_by(Attraction.id.desc()).limit(5).all(),
        latest_users=User.query.order_by(User.created_at.desc()).limit(5).all(),
    )


@main_bp.route("/admin/attractions", methods=["GET", "POST"])
@login_required
def admin_attractions():
    _require_admin()
    lang = _get_ui_lang()
    destinations = Destination.query.order_by(Destination.name.asc()).all()
    form_data = _build_attraction_form_data(request.form if request.method == "POST" else None)

    if request.method == "POST":
        parsed = _validate_attraction_form(form_data, destinations)
        for error in parsed["errors"]:
            flash(_ui_text(error[0], error[1], lang), "danger")
        if not parsed["errors"]:
            attraction = Attraction(
                destination_id=parsed["destination_id"],
                name=parsed["name"],
                category=parsed["category"],
                description=parsed["description"],
                entry_cost=parsed["entry_cost"],
                duration_hours=parsed["duration_hours"],
                latitude=parsed["latitude"],
                longitude=parsed["longitude"],
            )
            db.session.add(attraction)
            db.session.commit()
            flash(_ui_text("تمت إضافة النشاط بنجاح.", "Attraction added successfully.", lang), "success")
            return redirect(url_for("main.admin_attractions", lang=lang))

    attractions = Attraction.query.order_by(Attraction.id.desc()).all()
    return render_template(
        "admin_attractions.html",
        attractions=attractions,
        destinations=destinations,
        form_data=form_data,
    )


@main_bp.route("/admin/users", methods=["GET"])
@login_required
def admin_users():
    _require_admin()
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)


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
    cities = _available_cities()
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
    cities = _available_cities()
    category_interests = [
        row[0]
        for row in db.session.query(Destination.category)
        .filter(Destination.category.isnot(None))
        .distinct()
        .order_by(Destination.category.asc())
        .all()
    ]
    suggested_interests = list(dict.fromkeys([*PROFILE_TAG_OPTIONS, *category_interests]))
    form_data = _build_itinerary_form_data(request.form if request.method == "POST" else None)

    if request.method == "POST":
        parsed = _validate_itinerary_form(form_data, cities)
        for error in parsed["errors"]:
            flash(_ui_text(error[0], error[1], lang), "danger")
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
            profile_context=_user_profile_context(current_user),
        )
        if not matched:
            flash(_ui_text("لم نتمكن من العثور على وجهات تطابق تفضيلاتك الحالية. جرّب مدينة أو ميزانية أو اهتمامات مختلفة.", "No destinations matched your current preferences. Try a different city, budget, or interests.", lang), "warning")
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
            profile_context=_user_profile_context(current_user),
        )
        if not generated["items"]:
            flash(_ui_text("تعذر إنشاء خطة رحلة من التفضيلات المحددة.", "We could not generate an itinerary from the selected preferences.", lang), "warning")
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
    lang = _get_ui_lang()
    city = request.args.get("city", "").strip()
    cities = _available_cities()
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
            "name": tr_destination(destination.name, lang),
            "city": tr_city(destination.city, lang),
            "category": tr_category(destination.category, lang),
            "description": destination.description,
            "estimated_cost": destination.estimated_cost,
            "latitude": destination.latitude,
            "longitude": destination.longitude,
            "season": tr_season(destination.season, lang),
            "detail_url": url_for(
                "main.destination_detail",
                destination_id=destination.id,
                lang=lang,
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
