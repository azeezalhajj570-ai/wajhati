# Wajhati Saudiya Final Report

## 1. Introduction

Wajhati Saudiya is a web-based tourism planning system developed to support domestic travel in Saudi Arabia. The system helps users discover destinations, review travel options, and generate trip itineraries based on personal preferences such as city, budget, duration, and interests.

The project was built as a full-stack software engineering exercise using Flask, SQLite, server-rendered templates, and a rule-based recommendation service. Its main value as a university project is that it demonstrates complete application flow from user interface to persistence and business logic.

## 2. Problem Statement

Planning domestic travel can be inconvenient when information about destinations is fragmented and not presented in a structured way. Travelers may also struggle to build a schedule that fits their time, budget, and interests. This project addresses that problem by collecting destination data into one system and generating itinerary suggestions through a guided planning workflow.

## 3. Objectives

- Build a usable tourism planning platform focused on Saudi destinations.
- Allow users to create accounts and manage personalized travel activity.
- Provide destination discovery through browsing and filtering.
- Generate itinerary suggestions that reflect user preferences.
- Offer both a browser-based experience and JSON API endpoints.
- Apply software engineering concepts such as modular design, validation, persistence, and testing.

## 4. Project Scope

The current scope includes local deployment, destination browsing, account management, itinerary generation, favorites, and reviews. The system is intended for demonstration and academic evaluation rather than production release.

The following items are outside the current scope:

- live booking integration
- external maps or route optimization services
- advanced recommendation models
- production-grade deployment hardening
- schema migration tooling

## 5. System Overview

The application is a monolithic Flask system with separated modules for presentation, routing, services, and persistence.

### Core Features

- user registration and login
- destination listing and filtering
- destination detail pages
- favorite destinations
- destination reviews
- itinerary generation
- saved itinerary management
- API access for selected features

## 6. System Architecture

### Architectural Style

The system follows a layered monolithic architecture:

- presentation layer: Jinja templates and static assets
- application layer: Flask blueprints and route handlers
- service layer: itinerary recommendation logic
- data layer: SQLAlchemy models and SQLite database

### Main Components

- `app.py`: local development entry point
- `wajhati/__init__.py`: app factory and extension setup
- `wajhati/routes/auth.py`: authentication routes
- `wajhati/routes/main.py`: main web routes
- `wajhati/routes/api.py`: API routes
- `wajhati/services/recommender.py`: matching and itinerary generation logic
- `wajhati/models.py`: relational data model
- `seed_data.py`: sample data loader

## 7. Database Design

The database supports the main user journeys of searching, saving, and evaluating destinations.

### Main Entities

- `User`: stores account identity and password hash
- `Destination`: stores destination metadata such as city, category, cost, and location
- `Attraction`: stores attraction records linked to destinations
- `Favorite`: links users to saved destinations
- `Review`: stores user ratings and comments
- `Itinerary`: stores generated trip metadata
- `ItineraryItem`: stores day-by-day itinerary entries

### Relationship Summary

- one user can create many itineraries
- one user can create many favorites and reviews
- one destination can have many attractions and reviews
- one itinerary can contain many itinerary items

## 8. Functional Design

### Authentication Module

Users can register, log in, and log out. Authenticated sessions are required for saving favorites, submitting reviews, and creating itineraries.

### Destination Module

Users can browse destinations and filter them by city or category. Destination detail pages display descriptive information and associated user reviews.

### Review And Favorite Module

Authenticated users can submit reviews and toggle destinations as favorites. These actions personalize the overall user experience and create reusable travel history.

### Itinerary Module

Users choose a city, duration, budget, trip type, and interests. The system validates the request, matches suitable destinations, generates day-by-day items, and optionally saves the final itinerary.

### API Module

The API exposes health checks, destination listing, itinerary generation, and destination reviews. This allows the backend logic to be reused by future clients if needed.

## 9. Recommendation Approach

The project uses a rule-based recommendation method rather than machine learning. Destinations are ranked based on:

- selected city
- budget compatibility
- category match
- keyword overlap between interests and destination descriptions

The system then distributes the selected destinations across trip days and estimates the total trip cost. This approach is simple and understandable, which makes it suitable for an academic prototype, but it is less sophisticated than a real recommendation engine.

## 10. User Flow Summary

### Main User Journey

1. A visitor creates an account or logs in.
2. The user browses destinations and reviews details.
3. The user selects trip preferences in the itinerary form.
4. The system validates the request and generates a trip plan.
5. The user saves the itinerary and later reviews or deletes it.

### Supporting Journeys

- mark a destination as favorite
- submit a review for a destination
- retrieve destination and itinerary information through the API

## 11. Validation And Testing

The project includes server-side validation for itinerary inputs in both the web and API layers. Required fields and numeric ranges are checked before itinerary generation.

The automated test suite currently focuses on the most critical itinerary behavior:

- city-constrained destination matching in the recommendation service
- itinerary generation API responses
- no-match API behavior when a requested city has no valid destinations

This is a useful starting point, but it does not yet provide full quality assurance coverage.

## 12. Limitations

- the recommendation engine is heuristic and does not learn from user behavior
- the dataset is small and intended for demonstration
- the map page is not integrated with live routing
- database schema evolution is not managed with migrations
- deployment security settings are still development-oriented
- localization is partial rather than fully centralized

## 13. Future Work

- add a wider automated test suite for authentication, authorization, and error handling
- introduce migration support with Flask-Migrate or Alembic
- improve configuration safety for deployment environments
- expand destination and attraction data
- connect the map interface to itinerary items and coordinates
- introduce a stronger bilingual localization workflow
- explore more advanced recommendation strategies

## 14. Conclusion

Wajhati Saudiya is a successful software engineering project that delivers a complete tourism planning workflow with practical functionality and a clear modular structure. Its strongest qualities are scope completeness, separation of concerns, and end-to-end usability. The main areas for improvement are testing depth, deployment readiness, and documentation maturity. Even with those limitations, the project demonstrates solid engineering practice and provides a strong foundation for future enhancement.
