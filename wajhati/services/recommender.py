from collections import defaultdict


def match_destinations(destinations, city, budget, interests):
    normalized_interests = {item.strip().lower() for item in interests if item.strip()}
    matched = []

    for destination in destinations:
        score = 0
        if destination.city.lower() == city.lower():
            score += 3
        if destination.estimated_cost <= budget:
            score += 2
        if destination.category.lower() in normalized_interests:
            score += 2
        if normalized_interests and any(
            interest in destination.description.lower() for interest in normalized_interests
        ):
            score += 1
        matched.append((score, destination))

    matched.sort(key=lambda item: (item[0], -item[1].estimated_cost), reverse=True)
    return [destination for score, destination in matched if score > 0]


def generate_itinerary(destinations, duration_days, budget, trip_type, interests):
    """
    Simple rule-based itinerary generator.
    """
    if not destinations:
        return {"items": [], "estimated_total_cost": 0.0}

    selected = destinations[: max(duration_days * 2, 1)]
    day_items = defaultdict(list)

    for index, destination in enumerate(selected):
        day = (index % duration_days) + 1
        note = (
            f"{trip_type.title()} experience focused on {destination.category.lower()}."
            f" Explore {destination.name} in {destination.city}."
        )
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
