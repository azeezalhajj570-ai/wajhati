# Wajhati Saudiya

Wajhati Saudiya is a Flask-based tourism planning system for domestic travel in Saudi Arabia. The project combines destination discovery, user authentication, favorites, reviews, saved itineraries, and a rule-based recommendation service through both web pages and JSON API endpoints.

This repository is suitable for a 4th-year software engineering project because it demonstrates a complete web application stack: presentation, business logic, persistence, validation, and basic service integration in one coherent system.

## Project Summary

### Problem Statement

Domestic travelers often need a simple way to discover destinations, compare travel options, and build a trip plan that fits their budget and interests. Wajhati Saudiya addresses that need with a guided itinerary workflow centered on Saudi destinations.

### Objectives

- Provide a searchable catalog of destinations and attractions.
- Allow users to create accounts and manage personal travel activity.
- Generate itinerary suggestions based on city, budget, trip duration, trip type, and interests.
- Let users save itineraries, mark favorites, and leave destination reviews.
- Expose core planning features through both a browser interface and a lightweight API.

### Scope

The current implementation supports local development and demonstration use. It does not yet include production deployment hardening, database migrations, live mapping, or external travel data sources.

## Implemented Features

- User registration, login, and logout with session-based authentication
- Destination browsing with city and category filtering
- Destination detail pages with reviews and favorite toggling
- Itinerary generation based on city, duration, budget, trip type, and interests
- Saved itinerary listing, detail view, and deletion
- Basic user dashboard information on the home page
- API endpoints for health checks, destinations, reviews, and itinerary generation

## Architecture

Wajhati Saudiya follows a monolithic Flask architecture with clear internal separation of concerns.

- Presentation layer: Jinja templates and static assets in `wajhati/templates` and `wajhati/static`
- Application layer: Flask blueprints in `wajhati/routes`
- Domain and persistence layer: SQLAlchemy models in `wajhati/models.py`
- Service layer: itinerary recommendation logic in `wajhati/services/recommender.py`

### Main Modules

- `app.py`: application entry point for local development
- `wajhati/__init__.py`: app factory, extension initialization, and blueprint registration
- `wajhati/routes/auth.py`: authentication workflows
- `wajhati/routes/main.py`: browser-based destination and itinerary flows
- `wajhati/routes/api.py`: JSON API endpoints
- `wajhati/models.py`: database schema and relationships
- `wajhati/services/recommender.py`: rule-based destination matching and itinerary creation
- `seed_data.py`: sample destination seeding

## Technology Stack

- Backend: Flask
- Database access: Flask-SQLAlchemy
- Authentication: Flask-Login
- Database engine: SQLite
- Frontend rendering: Jinja templates
- Styling: custom CSS and Tailwind CSS via CDN
- Testing: Python `unittest`

## Database Design

The data model includes the following entities:

- `User`
- `Destination`
- `Attraction`
- `Favorite`
- `Review`
- `Itinerary`
- `ItineraryItem`

These models support the main user flows of browsing, reviewing, saving favorites, and generating multi-day trip plans.

## Recommendation Logic

The itinerary engine is rule-based, not machine-learning based. Destination matching prioritizes:

- exact city match
- budget fit
- category match against user interests
- keyword overlap between interests and destination descriptions

After matching, the generator distributes selected destinations across the requested number of days and scales estimated costs to fit within the stated budget when necessary.

## Setup And Run

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Seed sample data:

```bash
python seed_data.py
```

4. Start the application:

```bash
python app.py
```

5. Open:

```text
http://127.0.0.1:5000
```

## Testing

The repository now includes a small automated test suite for the most critical itinerary behavior.

Run the tests with:

```bash
python -m unittest discover -s tests
```

Current automated coverage focuses on:

- destination matching behavior in the recommender service
- itinerary generation API behavior for city-constrained results
- no-match API responses for unsupported cities

## API Overview

### `GET /api/health`

Returns a small status payload confirming the service is available.

### `GET /api/destinations`

Supports optional `city` and `category` query parameters.

### `POST /api/itineraries/generate`

Example request body:

```json
{
  "destination_city": "Riyadh",
  "duration_days": 3,
  "budget": 1200,
  "trip_type": "family",
  "interests": ["cultural", "leisure"],
  "save": false
}
```

Validation rules:

- `destination_city` is required
- `duration_days` must be between `1` and `7`
- `budget` must be greater than `0`
- `trip_type` must be one of `family`, `adventure`, `cultural`, or `leisure`

### `GET /api/destinations/<id>/reviews`

Returns review records for the selected destination.

## Limitations

- The recommendation engine is heuristic and uses a small demo dataset.
- The map page is currently presentation-only and is not connected to live routing.
- The app still uses automatic table creation and does not yet include a migration workflow.
- Configuration is currently optimized for local development rather than deployment.

## Documentation

- Academic project status: [Docs/project-status.md](/c:/Users/pc/Desktop/UNI-PROJECTS/wajhati/Docs/project-status.md)
- Full university-style report: [Docs/final-report.md](/c:/Users/pc/Desktop/UNI-PROJECTS/wajhati/Docs/final-report.md)
- Supporting reference document: [Docs/wejhati.docx](/c:/Users/pc/Desktop/UNI-PROJECTS/wajhati/Docs/wejhati.docx)
