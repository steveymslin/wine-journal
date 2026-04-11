# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Wine Journal (Cave à Vin) — a full-stack wine tracking PWA with a Python Flask backend and vanilla JavaScript frontend. Uses Claude AI for wine label analysis, pronunciation guides, and price checking. Data is stored client-side in IndexedDB with offline support via Service Worker.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (requires ANTHROPIC_API_KEY env var)
python app.py  # serves on http://localhost:5000

# Production
gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT
```

No test suite or linter is configured.

## Architecture

**Backend (`app.py`)** — Flask app with API endpoints:
- `POST /api/analyze` — Wine label image analysis via Claude vision (claude-opus-4-5)
- `POST /api/pronounce` — Phonetic pronunciation guide (claude-sonnet-4-5)
- `POST /api/price-check` — Price lookup using Claude with web search tool
- `GET /api/health` — Health check

**Frontend (`static/index.html`)** — Single monolithic HTML file (~4200 lines) containing all CSS, JavaScript, and HTML. Key subsystems:
- **IndexedDB layer** (`dbGetAll`, `dbPut`, `dbDelete`, `dbSearch`) — all wine data stored client-side
- **Wine CRUD** (`openAdd`, `openEdit`, `saveWine`, `deleteWine`, `loadWines`, `render`)
- **AI features** (`analyzeLabel`, `generateWsetNote`, `checkPrice`, `showPronun`)
- **Regional data** — large hardcoded `REGIONS` object with wine regions for 40+ countries, used for cascading country→region→sub-region dropdowns
- **CSV import/export** (`importCSV`, `exportCSV`)

**PWA assets** — `static/sw.js` (Service Worker), `static/manifest.json`, app icons

## Key Patterns

- The frontend is entirely in one file — CSS at top, HTML in middle, JS at bottom. There are no build steps or bundling.
- AI model selection: `claude-opus-4-5` for vision/label analysis, `claude-sonnet-4-5` for text tasks.
- Wine region matching uses fuzzy logic to handle variations in AI-returned region names.
- Deployed to Heroku (see `Procfile`).

## Environment Variables

- `ANTHROPIC_API_KEY` — required for all AI features
- `PORT` — server port (defaults to 5000)
