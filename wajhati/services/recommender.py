from collections import defaultdict


def _normalize_text_list(items):
    return {str(item).strip().lower() for item in items if str(item).strip()}


def _normalize_profile_context(profile_context=None):
    profile_context = profile_context or {}
    return {
        "age_range": str(profile_context.get("age_range", "")).strip(),
        "gender": str(profile_context.get("gender", "")).strip(),
        "favorite_tags": [str(item).strip() for item in profile_context.get("favorite_tags", []) if str(item).strip()],
    }


def match_destinations(destinations, city, budget, interests, profile_context=None):
    normalized_city = city.strip().lower()
    normalized_interests = _normalize_text_list(interests)
    normalized_profile = _normalize_profile_context(profile_context)
    normalized_favorite_tags = _normalize_text_list(normalized_profile["favorite_tags"])
    matched = []

    for destination in destinations:
        if destination.city.lower() != normalized_city:
            continue

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
    return [destination for score, destination in matched if score > 0]


def generate_itinerary(destinations, duration_days, budget, trip_type, interests, profile_context=None):
    """
    Simple rule-based itinerary generator.
    """
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
