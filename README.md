# Flask Smart Tourism App - Wajhati Saudiya

A Flask-based smart tourism application for domestic trip planning in Saudi Arabia.

## Features
- User authentication (register/login/logout)
- Destinations catalog with filtering
- Rule-based personalized itinerary generation
- Favorites and reviews
- REST API endpoints for destinations and itinerary generation
- SQLite persistence via SQLAlchemy

## Stack
- Flask
- Flask-SQLAlchemy
- Flask-Login
- SQLite

## Quick Start
1. Create and activate a virtual environment.
2. Install dependencies:
   pip install -r requirements.txt
3. Seed sample data:
   python seed_data.py
4. Run the app:
   python app.py
5. Open:
   http://127.0.0.1:5000

## API Endpoints
- GET /api/health
- GET /api/destinations?city=Riyadh&category=cultural
- POST /api/itineraries/generate
  Example JSON:
  {
    "destination_city": "Riyadh",
    "duration_days": 3,
    "budget": 1200,
    "trip_type": "family",
    "interests": ["cultural", "leisure"],
    "save": false
  }
- GET /api/destinations/<id>/reviews

## Notes
- Database file is created automatically (`wajhati.db`) on first run.
- The recommendation engine is rule-based and can later be replaced with ML logic.
