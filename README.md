# Clover — Adaptive & Scrutable AI Job Application Assistant

Clover is an end-to-end AI platform that:

- Continuously ingests live jobs (Apify pipelines)
- Matches jobs against a user profile with adaptive ranking
- Explains each score with scrutable breakdowns
- Generates ATS-optimized CV output + cover letters with Gemini agents

## Architecture

- Data layer: Apify scrapers -> PostgreSQL -> Gemini embeddings -> ChromaDB
- API layer: FastAPI
- Auth layer: JWT access + refresh sessions
- Intelligence layer: CV parser + adaptive matching engine
- Agent layer: LangGraph orchestration (with sequential fallback)
- Frontend: Next.js (modern glassy Clover theme)

## Core Flows

1. User signs up/logs in (`/api/auth/*`)
2. User completes onboarding (`/api/onboarding`)
3. User uploads CV (`/api/upload-cv`)
4. Clover returns personalized, explainable matches (`/api/match-jobs`)
5. For scores >= 80, user triggers generation (`/api/generate-outputs`)
6. Clover tracks signals and applications (`/api/signals`, `/api/applications`)

## Backend Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables

Create `.env` with at least:

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=jobfit_ai
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-1.5-flash
GEMINI_EMBEDDING_MODEL=models/embedding-001

JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES_MINUTES=45
JWT_REFRESH_TOKEN_EXPIRES_DAYS=14

GENERATION_THRESHOLD=80
CHROMA_DB_PATH=./chroma_db
APIFY_TOKEN=your_apify_token
```

### Run API

```bash
python3 -m uvicorn api.main:app --reload
```

### Run Scraper Once

```bash
python3 scraper/run_scraper.py
```

### Run Continuous Scraper (every 6h)

```bash
CLOVER_SCRAPER_MODE=daemon python3 scraper/run_scraper.py
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Set API URL:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Tests

```bash
pytest
```

Smoke tests cover:

- API import/startup path
- Config validation
- Match engine scoring
- CV parser extraction

## Notes

- Gemini is used when `GEMINI_API_KEY` is configured; deterministic local fallbacks keep flows functional in dev.
- LangGraph orchestration is enabled automatically when available.
- Existing datasets and partial legacy scripts are left intact for compatibility and manual testing.
