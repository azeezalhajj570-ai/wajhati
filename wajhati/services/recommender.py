from collections import defaultdict
import json
from urllib import error, request

from flask import current_app

from wajhati.models import AppSetting


AI_PROVIDER_GEMINI = "gemini"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_AI_SYSTEM_PROMPT = (
    "You are a travel planner for Saudi Arabia. "
    "Return only valid JSON with this shape: "
    "{\"items\":[{\"day_number\":1,\"title\":\"...\",\"notes\":\"...\",\"estimated_cost\":120.0}],"
    "\"estimated_total_cost\":120.0}. "
    "Use only the provided destinations, keep day_number between 1 and the requested duration, "
    "and make the total cost realistic for the provided budget."
)


def _normalize_text_list(items):
    return {str(item).strip().lower() for item in items if str(item).strip()}


def _normalize_profile_context(profile_context=None):
    profile_context = profile_context or {}
    return {
        "age_range": str(profile_context.get("age_range", "")).strip(),
        "gender": str(profile_context.get("gender", "")).strip(),
        "favorite_tags": [str(item).strip() for item in profile_context.get("favorite_tags", []) if str(item).strip()],
    }


def get_ai_settings():
    return {
        "enabled": AppSetting.get_value("ai_recommendations_enabled", "0") == "1",
        "provider": AppSetting.get_value("ai_recommendations_provider", AI_PROVIDER_GEMINI) or AI_PROVIDER_GEMINI,
        "model": AppSetting.get_value("ai_recommendations_model", DEFAULT_GEMINI_MODEL) or DEFAULT_GEMINI_MODEL,
        "api_key": AppSetting.get_value("ai_recommendations_api_key", "").strip(),
        "system_prompt": AppSetting.get_value("ai_recommendations_system_prompt", DEFAULT_AI_SYSTEM_PROMPT)
        or DEFAULT_AI_SYSTEM_PROMPT,
    }


def ai_recommendations_available(settings=None):
    settings = settings or get_ai_settings()
    return bool(settings["enabled"] and settings["provider"] == AI_PROVIDER_GEMINI and settings["api_key"])


def _coerce_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _extract_text_from_gemini_response(payload):
    candidates = payload.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            text = part.get("text")
            if text:
                return text
    return ""


def _normalize_generated_items(items, duration_days):
    normalized_items = []
    for item in items or []:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        day_number = item.get("day_number", 1)
        try:
            day_number = int(day_number)
        except (TypeError, ValueError):
            day_number = 1
        day_number = min(max(day_number, 1), duration_days)
        normalized_items.append(
            {
                "day_number": day_number,
                "title": title,
                "notes": str(item.get("notes", "")).strip(),
                "estimated_cost": round(max(_coerce_float(item.get("estimated_cost", 0.0)), 0.0), 2),
            }
        )
    normalized_items.sort(key=lambda item: (item["day_number"], item["title"].lower()))
    return normalized_items


def _build_gemini_system_instruction(ai_settings, duration_days, budget, trip_type, interests, profile_context):
    user_context = {
        "age_range": profile_context.get("age_range", ""),
        "gender": profile_context.get("gender", ""),
        "favorite_tags": list(profile_context.get("favorite_tags", [])),
    }
    form_context = {
        "duration_days": duration_days,
        "budget": budget,
        "trip_type": trip_type,
        "interests": list(interests),
    }
    context_block = {
        "admin_prompt": ai_settings["system_prompt"],
        "user_context": user_context,
        "form_context": form_context,
        "output_rules": {
            "format": "json",
            "required_keys": ["items", "estimated_total_cost"],
            "item_keys": ["day_number", "title", "notes", "estimated_cost"],
        },
    }
    return (
        "Use the following database-configured instruction and runtime context to generate the itinerary. "
        "The admin prompt is authoritative, and the user/form context must directly influence the plan. "
        "Return valid JSON only.\n"
        f"{json.dumps(context_block, ensure_ascii=True)}"
    )


def _generate_itinerary_with_gemini(destinations, duration_days, budget, trip_type, interests, profile_context, ai_settings):
    destination_payload = [
        {
            "name": destination.name,
            "city": destination.city,
            "category": destination.category,
            "description": destination.description,
            "estimated_cost": destination.estimated_cost,
        }
        for destination in destinations[: max(duration_days * 3, 3)]
    ]
    prompt = {
        "trip_request": {
            "duration_days": duration_days,
            "budget": budget,
            "trip_type": trip_type,
            "interests": list(interests),
            "profile_context": profile_context,
        },
        "candidate_destinations": destination_payload,
    }
    body = {
        "system_instruction": {
            "parts": [
                {
                    "text": _build_gemini_system_instruction(
                        ai_settings,
                        duration_days=duration_days,
                        budget=budget,
                        trip_type=trip_type,
                        interests=interests,
                        profile_context=profile_context,
                    )
                }
            ]
        },
        "contents": [{"parts": [{"text": json.dumps(prompt, ensure_ascii=True)}]}],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{ai_settings['model']}:generateContent"
    )
    req = request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": ai_settings["api_key"],
        },
        method="POST",
    )
    with request.urlopen(req, timeout=20) as response:
        raw_payload = json.loads(response.read().decode("utf-8"))
    raw_text = _extract_text_from_gemini_response(raw_payload)
    if not raw_text:
        raise ValueError("Gemini response did not include any text content.")
    generated_payload = json.loads(raw_text)
    items = _normalize_generated_items(generated_payload.get("items"), duration_days)
    estimated_total_cost = round(
        max(_coerce_float(generated_payload.get("estimated_total_cost"), 0.0), 0.0), 2
    )
    if not items:
        raise ValueError("Gemini response did not include itinerary items.")
    if estimated_total_cost <= 0:
        estimated_total_cost = round(sum(item["estimated_cost"] for item in items), 2)
    return {"items": items, "estimated_total_cost": estimated_total_cost}


def match_destinations(destinations, city, budget, interests, profile_context=None):
    normalized_city = city.strip().lower()
    normalized_interests = _normalize_text_list(interests)
    normalized_profile = _normalize_profile_context(profile_context)
    normalized_favorite_tags = _normalize_text_list(normalized_profile["favorite_tags"])
    matched = []
    city_candidates = []

    for destination in destinations:
        if normalized_city and destination.city.lower() != normalized_city:
            continue
        city_candidates.append(destination)

        score = 0
        score += 3
        if destination.estimated_cost <= budget:
            score += 2
        if destination.category.lower() in normalized_interests:
            score += 2
        if destination.category.lower() in normalized_favorite_tags:
            score += 2
        if normalized_interests and any(
            interest in destination.description.lower() for interest in normalized_interests
        ):
            score += 1
        if normalized_favorite_tags and any(
            tag in destination.description.lower() for tag in normalized_favorite_tags
        ):
            score += 1
        matched.append((score, destination))

    matched.sort(key=lambda item: (item[0], -item[1].estimated_cost), reverse=True)
    ranked_matches = [destination for score, destination in matched if score > 0]
    if ranked_matches:
        return ranked_matches

    city_candidates.sort(key=lambda destination: (destination.estimated_cost > budget, destination.estimated_cost))
    return city_candidates


def _generate_rule_based_itinerary(destinations, duration_days, budget, trip_type, interests, profile_context=None):
    if not destinations:
        return {"items": [], "estimated_total_cost": 0.0}

    profile_context = _normalize_profile_context(profile_context)
    selected = destinations[: max(duration_days * 2, 1)]
    day_items = defaultdict(list)
    favorite_tags = ", ".join(profile_context["favorite_tags"])
    profile_note = []
    if profile_context["age_range"]:
        profile_note.append(f"age range {profile_context['age_range']}")
    if profile_context["gender"]:
        profile_note.append(f"gender {profile_context['gender']}")
    if favorite_tags:
        profile_note.append(f"favorite tags {favorite_tags}")
    profile_suffix = f" Tailored using profile metadata: {', '.join(profile_note)}." if profile_note else ""

    for index, destination in enumerate(selected):
        day = (index % duration_days) + 1
        note = (
            f"{trip_type.title()} experience focused on {destination.category.lower()}."
            f" Explore {destination.name} in {destination.city}."
        )
        note += profile_suffix
        day_items[day].append(
            {
                "day_number": day,
                "title": destination.name,
                "notes": note,
                "estimated_cost": destination.estimated_cost,
            }
        )

    items = []
    for day in range(1, duration_days + 1):
        items.extend(day_items.get(day, []))

    estimated_total_cost = sum(item["estimated_cost"] for item in items)
    if estimated_total_cost > budget and estimated_total_cost > 0:
        ratio = budget / estimated_total_cost
        for item in items:
            item["estimated_cost"] = round(item["estimated_cost"] * ratio, 2)
        estimated_total_cost = sum(item["estimated_cost"] for item in items)

    return {"items": items, "estimated_total_cost": round(estimated_total_cost, 2)}


def generate_itinerary(destinations, duration_days, budget, trip_type, interests, profile_context=None, ai_settings=None):
    if not destinations:
        return {"items": [], "estimated_total_cost": 0.0}

    profile_context = _normalize_profile_context(profile_context)
    settings = ai_settings or get_ai_settings()
    if ai_recommendations_available(settings):
        try:
            return _generate_itinerary_with_gemini(
                destinations,
                duration_days=duration_days,
                budget=budget,
                trip_type=trip_type,
                interests=interests,
                profile_context=profile_context,
                ai_settings=settings,
            )
        except (error.URLError, error.HTTPError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            current_app.logger.warning("Gemini itinerary generation failed; falling back to rules: %s", exc)

    return _generate_rule_based_itinerary(
        destinations,
        duration_days=duration_days,
        budget=budget,
        trip_type=trip_type,
        interests=interests,
        profile_context=profile_context,
    )
