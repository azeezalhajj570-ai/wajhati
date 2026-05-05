import json
import os
import uuid
from urllib.parse import parse_qs, urlparse

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from wajhati import db
from wajhati.models import AppSetting, Attraction, Destination, Favorite, Itinerary, ItineraryItem, Review, User
from wajhati.services.recommender import (
    AI_PROVIDER_GEMINI,
    DEFAULT_AI_SYSTEM_PROMPT,
    DEFAULT_GEMINI_MODEL,
    ai_recommendations_available,
    generate_itinerary,
    get_ai_settings,
    match_destinations,
)
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
DESTINATION_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}


def _get_ui_lang():
    lang = request.args.get("lang") or request.form.get("lang")
    if not lang and request.referrer:
        lang = parse_qs(urlparse(request.referrer).query).get("lang", [None])[0]
    if not lang and current_user.is_authenticated:
        lang = getattr(current_user, "preferred_language", None)
    lang = lang or "ar"
    lang = lang if lang in ("ar", "en") else "ar"

    if (
        current_user.is_authenticated
        and request.args.get("lang") in ("ar", "en")
        and current_user.preferred_language != lang
    ):
        current_user.preferred_language = lang
        db.session.commit()

    return lang


def _save_destination_image(upload):
    filename = secure_filename(upload.filename or "")
    if not filename:
        return None, ("يرجى اختيار ملف صورة صالح.", "Please choose a valid image file.")

    extension = os.path.splitext(filename)[1].lower()
    if extension not in DESTINATION_IMAGE_EXTENSIONS:
        return None, (
            "امتداد الصورة غير مدعوم. استخدم JPG أو PNG أو WEBP أو GIF أو SVG.",
            "Unsupported image format. Use JPG, PNG, WEBP, GIF, or SVG.",
        )

    upload_dir = os.path.join(current_app.root_path, "static", "uploads", "destinations")
    os.makedirs(upload_dir, exist_ok=True)

    saved_name = f"{uuid.uuid4().hex}{extension}"
    upload.save(os.path.join(upload_dir, saved_name))
    return f"/static/uploads/destinations/{saved_name}", None


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


def _serialize_generated_itinerary(generated):
    return json.dumps(
        {
            "items": generated.get("items", []),
            "estimated_total_cost": generated.get("estimated_total_cost", 0.0),
        },
        ensure_ascii=False,
    )


def _parse_generated_itinerary(raw_value):
    try:
        payload = json.loads(raw_value or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return {"items": [], "estimated_total_cost": 0.0}

    items = []
    for item in payload.get("items", []):
        try:
            day_number = int(item.get("day_number", 1))
        except (TypeError, ValueError):
            day_number = 1
        try:
            estimated_cost = float(item.get("estimated_cost", 0.0))
        except (TypeError, ValueError):
            estimated_cost = 0.0
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        items.append(
            {
                "day_number": day_number,
                "title": title,
                "notes": str(item.get("notes", "")).strip(),
                "estimated_cost": round(max(estimated_cost, 0.0), 2),
            }
        )

    try:
        estimated_total_cost = float(payload.get("estimated_total_cost", 0.0))
    except (TypeError, ValueError):
        estimated_total_cost = sum(item["estimated_cost"] for item in items)

    return {
        "items": items,
        "estimated_total_cost": round(max(estimated_total_cost, 0.0), 2),
    }


def _build_destination_form_data(form=None):
    form = form or {}
    return {
        "name": str(form.get("name", "")).strip(),
        "city": str(form.get("city", "")).strip(),
        "category": str(form.get("category", "")).strip().lower(),
        "description": str(form.get("description", "")).strip(),
        "image_url": str(form.get("image_url", "")).strip(),
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


def _build_ai_settings_form_data(form=None):
    settings = get_ai_settings()
    form = form or {}
    if form:
        enabled_value = str(form.get("enabled", "")).strip().lower()
        return {
            "enabled": enabled_value in {"1", "true", "on", "yes"},
            "provider": AI_PROVIDER_GEMINI,
            "model": str(form.get("model", settings["model"])).strip() or DEFAULT_GEMINI_MODEL,
            "api_key": str(form.get("api_key", settings["api_key"])).strip(),
            "system_prompt": str(form.get("system_prompt", settings["system_prompt"])).strip() or DEFAULT_AI_SYSTEM_PROMPT,
        }
    return settings


def _validate_ai_settings_form(form_data):
    errors = []
    if not form_data["model"]:
        errors.append(("يرجى إدخال اسم نموذج Gemini.", "Please enter a Gemini model name."))
    if form_data["enabled"] and not form_data["api_key"]:
        errors.append(("أدخل مفتاح Gemini API قبل تفعيل الميزة.", "Enter a Gemini API key before enabling the feature."))
    if not form_data["system_prompt"]:
        errors.append(("يرجى إدخال تعليمات النظام.", "Please enter a system prompt."))
    return errors


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
        "image_url": form_data["image_url"],
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
    if city and city not in available_cities:
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
    edit_destination = None
    if request.method == "GET":
        try:
            edit_id = int(request.args.get("edit", "0"))
        except ValueError:
            edit_id = 0
        if edit_id:
            edit_destination = Destination.query.get_or_404(edit_id)
            form_data = {
                "name": edit_destination.name,
                "city": edit_destination.city,
                "category": edit_destination.category,
                "description": edit_destination.description,
                "image_url": edit_destination.image_url or "",
                "estimated_cost": str(edit_destination.estimated_cost),
                "latitude": "" if edit_destination.latitude is None else str(edit_destination.latitude),
                "longitude": "" if edit_destination.longitude is None else str(edit_destination.longitude),
                "season": edit_destination.season or "all",
            }
        else:
            form_data = _build_destination_form_data()
    else:
        form_data = _build_destination_form_data(request.form)

    if request.method == "POST":
        action = str(request.form.get("action", "create")).strip().lower()
        try:
            destination_id = int(request.form.get("destination_id", "0"))
        except ValueError:
            destination_id = 0
        if action == "update":
            edit_destination = Destination.query.get(destination_id)
            if not edit_destination:
                flash(_ui_text("تعذر العثور على الوجهة المطلوبة.", "The requested destination could not be found.", lang), "danger")
                return redirect(url_for("main.admin_destinations", lang=lang))

        parsed = _validate_destination_form(form_data, cities)
        uploaded_image = request.files.get("image_file")
        resolved_image_url = parsed["image_url"] or None
        if uploaded_image and uploaded_image.filename:
            resolved_image_url, image_error = _save_destination_image(uploaded_image)
            if image_error:
                parsed["errors"].append(image_error)
        for error in parsed["errors"]:
            flash(_ui_text(error[0], error[1], lang), "danger")
        if parsed["errors"]:
            destinations = Destination.query.order_by(Destination.created_at.desc()).all()
            return render_template(
                "admin_destinations.html",
                destinations=destinations,
                form_data=form_data,
                cities=cities,
                seasons=DESTINATION_SEASONS,
                edit_destination=edit_destination,
                dashboard_stats={
                    "destinations": Destination.query.count(),
                    "attractions": Attraction.query.count(),
                    "users": User.query.count(),
                    "reviews": Review.query.count(),
                },
            )

        if action == "update" and edit_destination:
            edit_destination.name = parsed["name"]
            edit_destination.city = parsed["city"]
            edit_destination.category = parsed["category"]
            edit_destination.description = parsed["description"]
            edit_destination.image_url = resolved_image_url if resolved_image_url is not None else edit_destination.image_url
            edit_destination.estimated_cost = parsed["estimated_cost"]
            edit_destination.latitude = parsed["latitude"]
            edit_destination.longitude = parsed["longitude"]
            edit_destination.season = parsed["season"]
            db.session.commit()
            flash(_ui_text("تم تحديث الوجهة بنجاح.", "Destination updated successfully.", lang), "success")
            return redirect(url_for("main.admin_destinations", lang=lang))

        destination = Destination(
            name=parsed["name"],
            city=parsed["city"],
            category=parsed["category"],
            description=parsed["description"],
            image_url=resolved_image_url,
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
        edit_destination=edit_destination,
        dashboard_stats={
            "destinations": Destination.query.count(),
            "attractions": Attraction.query.count(),
            "users": User.query.count(),
            "reviews": Review.query.count(),
        },
    )


@main_bp.route("/admin/destinations/<int:destination_id>/delete", methods=["POST"])
@login_required
def delete_admin_destination(destination_id):
    _require_admin()
    lang = _get_ui_lang()
    destination = Destination.query.get_or_404(destination_id)
    db.session.delete(destination)
    db.session.commit()
    flash(_ui_text("تم حذف الوجهة بنجاح.", "Destination deleted successfully.", lang), "info")
    return redirect(url_for("main.admin_destinations", lang=lang))


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


@main_bp.route("/admin/users", methods=["GET", "POST"])
@login_required
def admin_users():
    _require_admin()
    lang = _get_ui_lang()

    if request.method == "POST":
        action = str(request.form.get("action", "")).strip().lower()
        try:
            user_id = int(request.form.get("user_id", "0"))
        except ValueError:
            user_id = 0

        managed_user = User.query.get(user_id) if user_id else None
        if not managed_user:
            flash(_ui_text("تعذر العثور على المستخدم المطلوب.", "The requested user could not be found.", lang), "danger")
            return redirect(url_for("main.admin_users", lang=lang))

        if action == "make_admin":
            if managed_user.is_admin:
                flash(_ui_text("المستخدم مشرف بالفعل.", "This user is already an admin.", lang), "warning")
            else:
                managed_user.is_admin = True
                db.session.commit()
                flash(_ui_text("تمت ترقية المستخدم إلى مشرف.", "User promoted to admin successfully.", lang), "success")
        elif action == "remove_admin":
            admin_count = User.query.filter_by(is_admin=True).count()
            if managed_user.id == current_user.id:
                flash(_ui_text("لا يمكنك إزالة صلاحية الإدارة من حسابك الحالي.", "You cannot remove admin access from your current account.", lang), "danger")
            elif not managed_user.is_admin:
                flash(_ui_text("هذا المستخدم ليس مشرفًا.", "This user is not an admin.", lang), "warning")
            elif admin_count <= 1:
                flash(_ui_text("يجب أن يبقى هناك مشرف واحد على الأقل.", "At least one admin must remain.", lang), "danger")
            else:
                managed_user.is_admin = False
                db.session.commit()
                flash(_ui_text("تمت إزالة صلاحية الإدارة من المستخدم.", "Admin access removed from the user.", lang), "success")
        else:
            flash(_ui_text("إجراء غير صالح.", "Invalid action.", lang), "danger")

        return redirect(url_for("main.admin_users", lang=lang))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)


@main_bp.route("/admin/ai-settings", methods=["GET", "POST"])
@login_required
def admin_ai_settings():
    _require_admin()
    lang = _get_ui_lang()
    form_data = _build_ai_settings_form_data(request.form if request.method == "POST" else None)

    if request.method == "POST":
        errors = _validate_ai_settings_form(form_data)
        for error in errors:
            flash(_ui_text(error[0], error[1], lang), "danger")
        if not errors:
            AppSetting.set_value("ai_recommendations_enabled", "1" if form_data["enabled"] else "0")
            AppSetting.set_value("ai_recommendations_provider", form_data["provider"])
            AppSetting.set_value("ai_recommendations_model", form_data["model"])
            AppSetting.set_value("ai_recommendations_api_key", form_data["api_key"])
            AppSetting.set_value("ai_recommendations_system_prompt", form_data["system_prompt"])
            db.session.commit()
            flash(_ui_text("تم حفظ إعدادات الذكاء الاصطناعي.", "AI settings saved successfully.", lang), "success")
            return redirect(url_for("main.admin_ai_settings", lang=lang))

    saved_settings = get_ai_settings()
    return render_template(
        "admin_ai_settings.html",
        form_data=form_data,
        saved_settings=saved_settings,
        ai_status_ready=ai_recommendations_available(saved_settings),
    )


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
    preview_itinerary = None

    if request.method == "POST":
        action = str(request.form.get("action", "generate")).strip().lower()
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
                ai_settings=get_ai_settings(),
            )

        if action == "confirm":
            generated = _parse_generated_itinerary(request.form.get("generated_itinerary"))
            if not generated["items"]:
                flash(_ui_text("انتهت صلاحية الاقتراح الحالي. أعد التوليد أولاً.", "The current suggestion is no longer valid. Please regenerate it first.", lang), "warning")
                return render_template(
                    "create_itinerary.html",
                    cities=cities,
                    suggested_interests=suggested_interests,
                    form_data=form_data,
                    trip_types=TRIP_TYPES,
                    ai_settings=get_ai_settings(),
                )
        else:
            destinations = Destination.query.all()
            matched = match_destinations(
                destinations,
                city=parsed["city"],
                budget=parsed["budget"],
                interests=parsed["interests"],
                profile_context=_user_profile_context(current_user),
            )
            if not matched:
                flash(_ui_text("لا توجد وجهات متاحة حاليًا لإنشاء اقتراح.", "There are no destinations available right now to build a suggestion.", lang), "warning")
                return render_template(
                    "create_itinerary.html",
                    cities=cities,
                    suggested_interests=suggested_interests,
                    form_data=form_data,
                    trip_types=TRIP_TYPES,
                    ai_settings=get_ai_settings(),
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
                    ai_settings=get_ai_settings(),
                )

            if action != "confirm":
                preview_itinerary = generated
                flash(_ui_text("تم إنشاء اقتراح جديد. راجعه ثم أكد الحفظ أو أعد التوليد.", "A new suggestion was generated. Review it, then confirm save or regenerate.", lang), "success")
                return render_template(
                    "create_itinerary.html",
                    cities=cities,
                    suggested_interests=suggested_interests,
                    form_data=form_data,
                    trip_types=TRIP_TYPES,
                    ai_settings=get_ai_settings(),
                    preview_itinerary=preview_itinerary,
                    generated_itinerary_json=_serialize_generated_itinerary(preview_itinerary),
                )

        itinerary = Itinerary(
            user_id=current_user.id,
            destination_city=parsed["city"] or _ui_text("مرن", "Flexible", lang),
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
        ai_settings=get_ai_settings(),
        preview_itinerary=preview_itinerary,
        generated_itinerary_json="",
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

