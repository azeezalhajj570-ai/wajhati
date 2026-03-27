from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_REPORT = ROOT / "Docs" / "applied_project_report_sample_aligned.md"
OUTPUT_REPORT = ROOT / "Docs" / "applied_project_report_100plus.md"

FILE_GROUPS = [
    (
        "Core Backend Source Code Listings",
        [
            "app.py",
            "config.py",
            "wajhati/__init__.py",
            "wajhati/models.py",
            "wajhati/seed.py",
            "wajhati/translations.py",
            "wajhati/routes/auth.py",
            "wajhati/routes/main.py",
            "wajhati/routes/api.py",
            "wajhati/services/recommender.py",
        ],
    ),
    (
        "Template Source Code Listings",
        [
            "wajhati/templates/base.html",
            "wajhati/templates/index.html",
            "wajhati/templates/register.html",
            "wajhati/templates/login.html",
            "wajhati/templates/profile.html",
            "wajhati/templates/destinations.html",
            "wajhati/templates/destination_detail.html",
            "wajhati/templates/create_itinerary.html",
            "wajhati/templates/itinerary_detail.html",
            "wajhati/templates/my_itineraries.html",
            "wajhati/templates/map.html",
            "wajhati/templates/admin_dashboard.html",
            "wajhati/templates/admin_destinations.html",
            "wajhati/templates/admin_attractions.html",
            "wajhati/templates/admin_users.html",
            "wajhati/templates/admin_ai_settings.html",
            "wajhati/templates/components/_topbar.html",
            "wajhati/templates/components/_footer.html",
            "wajhati/templates/components/_flashes.html",
            "wajhati/templates/components/_i18n.html",
            "wajhati/templates/components/_media.html",
        ],
    ),
    (
        "Automated Test Listings",
        [
            "tests/test_api.py",
            "tests/test_auth.py",
            "tests/test_features.py",
            "tests/test_recommender.py",
            "tests/conftest.py",
        ],
    ),
]

ANALYTICAL_EXTENSION = """
# Extended Technical Documentation

## Chapter 7 Supplement: Detailed Screen-by-Screen Description

The home page acts as the landing environment of the system and combines branding, featured destinations, recent itinerary information, and quick access to major functions. When the user is authenticated, the page also summarizes itinerary count, favorites count, and reviews count. This means that the home page is not only an introduction page but also a lightweight personalized dashboard.

The registration and login pages are designed as entry points to account-based interaction. They are implemented as server-rendered forms with bilingual labels and simple validation behavior. The login route accepts either email or username as identifier, which improves usability in comparison with systems that force only one identifier type.

The profile screen is technically important because it extends the user model beyond authentication. The data collected in the profile page, including age range, gender, and favorite tags, are stored in the database and later reused by the itinerary recommendation logic. This creates a connection between user preference modeling and trip generation.

The destinations listing page provides the discovery function of the project. It filters data by city and category and presents destination cards. The destination detail page extends this by showing full descriptive data, review history, and favorite status. These pages together form the information browsing layer of the system.

The create itinerary screen is one of the most important user interface components in the project. It accepts destination city, duration, budget, trip type, and interest tags. The latest implementation allows the city field to remain optional so that the system can still produce a recommendation even when no city is selected. This is an example of resilient design because it reduces user dead ends. The preview-confirm-regenerate workflow further improves the interface because it gives the user control over the generated result before persistence.

The itinerary detail screen provides the final representation of a confirmed plan. It groups items by day, shows estimated costs, and keeps the user aware of the overall travel structure. The my itineraries screen complements this by acting as a personal archive of previously confirmed plans.

The map interface introduces a spatial dimension to the platform. It uses Leaflet and stored coordinates to present destination markers. The map does not perform route optimization, but it strengthens the exploratory value of the system and demonstrates integration between stored geolocation data and browser visualization.

The administration screens are important from a system engineering perspective because they separate operational data entry from end-user browsing. The admin dashboard aggregates counts and recent records, while the destination and attraction forms support content creation. The user administration screen enforces role management rules such as preventing the removal of the last administrator. The AI settings screen exposes provider configuration and system prompts through the database, which demonstrates a configurable integration approach rather than a hard-coded one.

## Additional Analysis of Recommendation Logic

The recommendation service combines deterministic ranking and optional AI assistance. First, candidate destinations are filtered and scored according to user-selected city, budget, category match, destination description overlap, and favorite tags. This provides explainable heuristic logic. Second, if the administrator has enabled Gemini and supplied the required credentials, the system builds a structured prompt containing an administrative system prompt, user profile context, form input context, and a list of candidate destinations. This prompt is sent to the Gemini REST endpoint to produce a JSON itinerary. If Gemini is unavailable or fails, the system logs the error and returns to the internal rule-based generator.

This design is useful for academic evaluation because it shows two distinct engineering ideas. The first is a transparent ranking-based recommendation baseline. The second is a configurable AI integration that remains bounded by system data and still has a local fallback path. This demonstrates defensive design because external service failure does not prevent the system from functioning.

## Additional Analysis of Security and Validation

The implemented system includes several important security and validation patterns. Passwords are not stored as plain text; instead, hashing is performed through Werkzeug utilities. Login redirection is guarded by a safe redirect checker that prevents unsafe redirect targets. Administrative pages call a dedicated authorization helper that aborts access for non-admin users. Form data is validated before model creation, and itinerary constraints such as budget and duration are checked in both web and API paths. These patterns do not make the system production-complete, but they reflect correct software engineering awareness in a diploma-level project.

## Additional Analysis of Testing

The repository contains both service-level and interaction-level tests. Recommendation tests verify destination matching and itinerary generation behavior. API tests verify JSON endpoint correctness. Authentication and feature tests written with Playwright verify realistic user journeys such as sign up, login, favorites, reviews, and itinerary flows. The presence of these tests strengthens the academic value of the project because it demonstrates that implementation is supported by executable verification rather than documentation alone.

## Appendix Expansion Strategy

To satisfy the requirement for a long submission document, the following appendices include full or near-full listings of the real source files used by the current application. This approach keeps the report grounded in the actual codebase and avoids invented material.
"""


def fenced_code_for(path: Path) -> str:
    suffix = path.suffix.lstrip(".") or "text"
    content = path.read_text(encoding="utf-8")
    return f"```{suffix}\n{content}\n```\n"


def file_section(rel_path: str) -> str:
    path = ROOT / rel_path
    content = path.read_text(encoding="utf-8")
    line_count = len(content.splitlines())
    return (
        f"### Source Listing: `{rel_path}`\n\n"
        f"This listing is included exactly because it is part of the implemented system. "
        f"It contains {line_count} lines of source code and contributes directly to the documented functionality.\n\n"
        f"{fenced_code_for(path)}"
    )


def main():
    base = BASE_REPORT.read_text(encoding="utf-8").rstrip() + "\n\n---\n\n"
    parts = [base, ANALYTICAL_EXTENSION.strip(), "\n\n"]
    for group_title, files in FILE_GROUPS:
        parts.append(f"## {group_title}\n\n")
        for rel_path in files:
            parts.append(file_section(rel_path))
            parts.append("\n")
    OUTPUT_REPORT.write_text("".join(parts), encoding="utf-8")
    print(OUTPUT_REPORT)


if __name__ == "__main__":
    main()
