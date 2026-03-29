# Wajhati Saudiya Project Documentation

This document provides comprehensive guidance on the Wajhati Saudiya project, covering chapters 1-5 as specified in the applied project report. It includes all required diagrams, tables, and structural information.

## Chapter 1: Introduction

### 1.1 Introduction
This system “Wajhati Saudiya: Smart Domestic Tourism Planning System” provides a unified platform for domestic tourism planning within the Kingdom of Saudi Arabia. The system is characterized by organized destination content, user account support, favorite management, destination reviews, interactive browsing, map-based exploration, and smart itinerary generation through both rule-based and optional AI-assisted recommendation logic.

### 1.2 Previous Work
- **Tourism destination platforms**: Provide destination information but lack personalized itinerary generation and integrated administration features.
- **Route and planning systems**: Allow travel suggestions based on preferences but are often general-purpose or part of larger commercial ecosystems.
- **Map-based travel platforms**: Enable geographic visualization but lack the comprehensive feature set of Wajhati.

### 1.3 Problem Statement
Domestic tourism planning is fragmented, making it difficult for users to discover destinations, compare options, and create personalized itineraries. Information is often scattered across multiple platforms, requiring significant manual effort to plan trips.

### 1.4 Scope
The current project scope includes:
- Web-based Flask application for local development
- Destination browsing with filtering
- User authentication and account management
- Favorites and reviews
- Saved itineraries
- Interactive map browsing
- Administration panels
- AI recommendation configuration
- API endpoints

Exclusions: online booking, payment processing, commercial travel inventory, live routing optimization, and production deployment hardening.

### 1.5 Objectives
- Enable browsing and searching of Saudi tourism destinations
- Allow user account creation and management
- Generate itinerary suggestions based on preferences
- Allow review and confirmation of suggestions
- Store and display saved itineraries
- Provide administration capabilities
- Offer API access for core functionality

### 1.6 Advantages
- User-friendly graphical interface
- Integrated features (browsing, favorites, reviews, map, itinerary generation, administration)
- Bilingual interface (Arabic and English)
- Smart planning with user confirmation capability
- Modular and maintainable architecture

### 1.7 Disadvantages
- Dependence on current dataset quality
- AI service dependency on external configuration and internet
- SQLite database suitable only for development
- Prototype nature, not a commercial platform

### 1.8 Software Requirements

**Table 1-1: Software Requirements**

| Software Tool | Description |
|---------------|-------------|
| Python 3.12 | Main programming language |
| Flask | Web framework |
| Flask-SQLAlchemy | ORM and database interaction |
| Flask-Login | Authentication and session management |
| SQLite | Relational database |
| Jinja2 | HTML template rendering |
| Tailwind CSS | UI styling |
| Leaflet | Map visualization |
| Pytest / unittest | Testing framework |
| Gemini REST API | Optional AI service integration |

### 1.9 Hardware Requirements

**Table 1-2: Hardware Requirements**

| Hardware | Specifications |
|----------|----------------|
| Processor | Intel Core i3 or equivalent |
| RAM | 4 GB or more |
| Disk | 1 GB free space |
| Display | Standard monitor with modern browser |
| Network | Internet connection |

### 1.11 Project Plan
The project follows an Agile methodology with these phases:
1. Requirements and problem identification
2. Interface and database design
3. Authentication and destination module development
4. Itinerary generation and recommendation logic
5. Administration and API module development
6. Testing and validation
7. Documentation and final report preparation

---

## Chapter 2: Literature Review

### 2.1 Introduction
This chapter reviews tourism platforms and itinerary planning systems similar to Wajhati, examining digital systems related to the proposed work.

### 2.2 Related Work
- **Travel destination websites**: Provide basic destination information but lack personalized itineraries and user preference preservation.
- **Trip planning applications**: Offer travel suggestions based on criteria but are often general-purpose or commercial.
- **Map-based travel platforms**: Visualize places geographically but lack integrated features like reviews and administration.

---

## Chapter 3: System Analysis

### 3.1 Introduction
System analysis identifies functions, users, and data requirements. The codebase supports three user contexts: visitor, registered user, and administrator, with both browser pages and API endpoints.

### 3.2 Data Collection
Data is collected through:
- Direct system input forms
- Administrative data entry
- Registration, profile, review, and itinerary preference forms
- Startup seed logic for demonstration data

### 3.3 Functional Requirements

**Visitor**
- Browse destinations with city/category filtering
- View destination details and interactive map
- Register and log in

**User**
- Update preference profile
- Manage favorites and submit reviews
- Generate and review itineraries
- Save itineraries
- Delete itineraries

**Administrator**
- Manage destinations, attractions, users, and AI settings
- Access admin dashboard

**API**
- Health, destinations, itinerary generation, and review endpoints

### 3.4 Non-Functional Requirements
- Bilingual interface (Arabic/English)
- Input validation
- Relational database persistence
- Admin-only access to admin pages
- Modular design
- Automated testing
- AI fallback to rule-based generation

---

## Chapter 4: System Design

### 4.1 Introduction
The system uses a layered Flask architecture with presentation, application, service, and persistence layers.

### 4.2 Static Models
**Figure 4.1 Class Diagram**
```text
User -> Itinerary
User -> Favorite
User -> Review
Destination -> Attraction
Destination -> Review
Itinerary -> ItineraryItem
Favorite -> User + Destination
Review -> User + Destination
AppSetting -> configurable system values
```

Key classes:
- `User`: account and personalization data
- `Destination`: tourism destination data
- `Attraction`: related activities
- `Itinerary` and `ItineraryItem`: trip and daily suggestions
- `AppSetting`: configurable values including AI settings

### 4.3 Dynamic Models

#### 4.3.1 Sequence Diagram (Figure 4.2)
![Itinerary Generation Sequence](docs/diagrams/04-sequence-itinerary-generation.drawio)

#### 4.3.2 Activity Diagram (Figure 4.3)
![Itinerary Flow Activity Diagram](docs/diagrams/04b-sequence-preferences-and-attractions.drawio)

---

## Chapter 5: Database

### 5.1 Data Modeling
The project uses SQLAlchemy with relational modeling supporting users, destinations, attractions, reviews, favorites, itineraries, and configurable settings.

### 5.2 Database Schema

| Entity | Key Attributes |
|--------|----------------|
| User | id, name, email, password_hash, is_admin, preferred_language, age_range, gender, favorite_tags, created_at |
| Destination | id, name, city, category, description, estimated_cost, latitude, longitude, season, created_at |
| Attraction | id, destination_id, name, category, description, entry_cost, duration_hours, latitude, longitude |
| Favorite | id, user_id, destination_id, created_at |
| Review | id, user_id, destination_id, rating, comment, created_at |
| Itinerary | id, user_id, destination_city, trip_type, duration_days, budget, interests, estimated_total_cost, created_at |

### 5.3 Relationships
The schema establishes relationships between users and destinations (favorites, reviews), destinations and attractions, and itineraries with their items.

---

## Appendices

### List of Project Diagrams
1. `digrams/01-system-context.drawio` - System context diagram
2. `digrams/02-use-case.drawio` - Use case diagram
3. `digrams/03a-activity-input-validation.drawio` - Input validation activity
4. `digrams/03b-activity-attraction-ranking.drawio` - Attraction ranking activity
5. `digrams/03c-activity-routing-and-build.drawio` - Routing and build activity
6. `digrams/03d-activity-save-and-display.drawio` - Save and display activity
7. `digrams/04-sequence-itinerary-generation.drawio` - Itinerary generation sequence
8. `digrams/04a-sequence-authentication.drawio` - Authentication sequence
9. `digrams/04b-sequence-preferences-and-attractions.drawio` - Preferences and attractions sequence
10. `digrams/04c-sequence-routing-and-ai.drawio` - Routing and AI sequence
11. `digrams/04d-sequence-save-and-display.drawio` - Save and display sequence
12. `digrams/05-class-domain-model.drawio` - Class domain model
13. `digrams/06-er-database.drawio` - Entity-relationship diagram
14. `digrams/07-system-architecture-3tier.drawio` - 3-tier architecture
15. `digrams/08-deployment.drawio` - Deployment architecture

### Sample Tables and Diagrams
All tables and diagrams referenced in Chapters 1-5 are included in the project documentation and stored in the `digrams/` directory for reference.