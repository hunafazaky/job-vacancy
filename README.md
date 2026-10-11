# Job Vacancy Image Parser

Upload an image of a job posting; get back structured job data (title, company,
skills, etc.) via a vision LLM. Signed-in users get their results saved
(image → Cloudflare R2, data → Postgres); anonymous users get a one-off result
that's discarded.

See `CONTEXT.md` (if present) for the full design rationale. This README covers
running the scaffold.

## Stack
- **Frontend**: SvelteKit, run with Bun
- **Backend**: FastAPI (Python 3.12), async SQLAlchemy
- **Database**: PostgreSQL 17-bookworm (Docker)
- **Vision LLM**: Claude Haiku (primary) → GPT-4o mini (fallback)
- **Image storage**: Cloudflare R2 (signed-in users only)

## Quick start (Docker)

1. Copy env files and fill in secrets:
   ```bash
   cp .env.example .env
   cp frontend/.env.example frontend/.env
   ```
   You'll need at minimum: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, and R2
   credentials (`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
   `R2_PUBLIC_BASE_URL`) to save extractions for signed-in users. The app
   still runs without R2 configured — signed-in saving will just fail on
   upload until it's set. `CORS_ORIGINS` defaults to `http://localhost:5173`;
   update it (comma-separated for multiple origins) if your frontend runs
   elsewhere.

2. Start everything:
   ```bash
   docker compose up --build
   ```

3. Run the initial DB migration (first time only, in a second terminal):
   ```bash
   docker compose exec backend alembic revision --autogenerate -m "init"
   docker compose exec backend alembic upgrade head
   ```

4. Open the app:
   - Frontend: http://localhost:5173
   - Backend docs (Swagger UI): http://localhost:8000/docs

## Running without Docker

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# point DATABASE_URL at a local/remote Postgres instance in .env
alembic revision --autogenerate -m "init"
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
bun install
bun run dev
```

## Project layout
```
backend/    FastAPI app (see backend/app for routes, services, models)
frontend/   SvelteKit app (see frontend/src/routes for pages)
docker-compose.yml
.env.example
```

## What's implemented in this scaffold
- Email/password signup, login, JWT refresh (`/auth/*`)
- `POST /extract` — optional-auth endpoint: works for everyone, saves only if signed in
- Rate limiting: 3/day anonymous (by IP), 5/day signed-in (by user), enforced before any LLM call
- Vision extraction with automatic fallback: Claude Haiku → GPT-4o mini
- Image validation (real content-type sniffing, not just extension) and a 5MB size cap
- Image optimization (resize + re-encode) before upload to Cloudflare R2, signed-in only
- `GET/DELETE /history` for a signed-in user's saved extractions
- `GET /rate-limit-status` so the frontend can show remaining quota
- SvelteKit pages: upload/result, login, signup, history
- CORS origins configurable via `CORS_ORIGINS` in `.env` (comma-separated)
- Global exception handler so unhandled backend errors still return proper CORS headers instead of showing up as a misleading "CORS policy" error in the browser
- Frontend auto-refreshes the access token on a 401 and retries the request once before giving up

## What's intentionally left as TODO
- Google/GitHub OAuth — `auth_providers` table exists but no OAuth flow is wired up yet
- Rate-limit UI (showing "2 of 3 left today" using `/rate-limit-status`)
- Tests
- Production-grade CORS config (currently just reads `CORS_ORIGINS` from env, still defaults to localhost dev)
