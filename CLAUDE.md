# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands
- **Development**: `python wajhati/app.py` (starts the application server)
- **Test Suite**: `pytest -v` (runs all tests in /tests/)
- **Run Specific Tests**:
  - `pytest tests/test_auth.py` (runs authentication tests)
  - `pytest tests/test_api.py` (runs API tests)
- **Seed Data**: `python wajhati/seed.py` (initial data population)
- **Clear Cache**: `rm -rf wajhati/static/cache/*` (clears caching data)
- **Linting**: `flake8 wajhati` (lint Python code)

## High-Level Architecture
The project follows a 3-tier architecture as illustrated in `digrams/07-system-architecture-3tier.drawio`:

1. **Presentation Layer**
   - Static assets: `/wajhati/static/` (CSS, images)
   - Templates: `/wajhati/templates/` (HTML templates)
   - Frontend logic: Embedded in Python templates

2. **Business Logic Layer**
   - Core services: `/wajhati/services/` (recommender.py, auth logic)
   - Route handlers: `/wajhati/routes/` (api.py, auth.py, main.py)
   - Data interaction: `/wajhati/models.py` (database models)

3. **Data Layer**
   - Database schema: Defined in `/digrams/06-er-database.drawio`
   - Seed data: `/wajhati/seed.py` and `/seed_data.py`

Key components:
- AI itinerary generation (AI-related logic in `/design/ai_itinerary_standardized/`)
- Trip planning workflow: `/design/04b-sequence-preferences-and-attractions.drawio`
- Authentication flow: `/design/04a-sequence-authentication.drawio`
- Admin dashboard: `/wajhati/templates/admin_dashboard.html`

## Notes
- The project uses Python 3 with Flask (implied by app.py structure)
- Routes are organized in `/wajhati/routes/` with API and authentication endpoints
- Project reports are generated via `/Docs/generate_report_docx.py`
- Draw.io diagrams should be consulted for detailed workflows and ER models