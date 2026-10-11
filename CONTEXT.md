# Job Vacancy Image Parser — Project Context

## 1. Overview
A web app where a user uploads an image of a job vacancy posting (poster, screenshot,
flyer, etc.). The system extracts structured job data from the image using a vision
LLM. If the user is signed in, the result is saved to their history in the database;
if not signed in, the result is only shown once and discarded.

## 2. Tech Stack
| Layer | Choice | Notes |
|---|---|---|
| Frontend | **SvelteKit**, run/built with **Bun** | File upload UI, result display, auth forms |
| Backend | **FastAPI** (Python 3.12+) | Chosen over Go for first-class LLM SDK support & async I/O |
| Database | **PostgreSQL 17-bookworm** (Docker) | Stores users, sessions, saved extractions |
| ORM / Migrations | SQLAlchemy 2.0 (async) + Alembic | |
| Image → Data | **Google Gemini** (free tier, primary) → **Groq** (free tier, fallback) | Called server-side only, never from frontend. No billing risk — both stay on free quotas for personal-use volume. Fallback triggers on primary error/timeout/rate-limit |
| Image storage | **Cloudflare R2** | Signed-in users only; image optimized (resized/re-encoded) before upload |
| Auth | Email/password + JWT (access + refresh) | Structured so OAuth (Google, GitHub) can be added later without reshaping schema |
| Rate limiting | Anonymous: by IP, 3/day. Signed-in: by user_id, 5/day | Backed by Postgres or Redis counter (see §9) |
| Containerization | Docker Compose | postgres, backend, (optionally frontend) services |

## 3. Core Behavior / Requirements
1. **Image upload**
   - Accepts common image formats: JPEG, PNG, WebP.
   - **Size limit**: reject files over a configurable max (suggested default: 5 MB).
   - Reject non-image MIME types even if the extension is spoofed (check actual content type / magic bytes server-side).
2. **Extraction**
   - Backend sends the image to **Gemini** (vision) with a structured-output prompt.
   - If the primary call fails (error, timeout, or provider-side rate limit) → automatically retry once against **Groq** as fallback. Log which provider actually served the request (useful for tracking free-tier quota usage).
   - Extracted fields (minimum):
     - `job_title`
     - `company`
     - `description` (free text / summary)
     - `skills_required` (array of strings)
     - `location` (if present)
     - `employment_type` (e.g. full-time, internship — if present)
     - `salary_range` (if present)
     - `source_language` (optional, if OCR text isn't English/Indonesian)
   - If the LLM can't confidently extract a field, return `null` for it rather than guessing — surface this to the user instead of fabricating data.
3. **Auth-gated persistence**
   - If the request includes a valid JWT (user is signed in) → optimize the image (resize/re-encode to a reasonable max dimension/quality), upload it to **Cloudflare R2**, then save the extraction + R2 URL to the DB, tied to `user_id`.
   - If not signed in → run extraction, return result in the response, **discard the image** — nothing is uploaded or persisted server-side.
   - Anonymous users should be able to use the core feature; sign-in only unlocks history/saving and image retention.

4. **Rate limiting**
   - Anonymous: **3 extractions/day**, keyed by client IP.
   - Signed-in: **5 extractions/day**, keyed by `user_id`.
   - Enforce server-side before the LLM call (reject over-limit requests with 429), so quota can't be bypassed by not sending a token.
   - A simple approach: a Postgres table keyed by `(ip_or_user_id, date)` with a count column, checked/incremented atomically. Redis is an option if load grows, but isn't required to start.
5. **Auth**
   - Email/password signup & login now.
   - Design the `users` table and auth service layer so **Google and GitHub OAuth** can be bolted on later (via a separate `auth_providers` table linked to `users`, rather than baking password-only assumptions into `users`). Not implemented yet, but schema is ready for it.

## 4. Suggested Repository Structure
```
project-root/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── extract.py        # image upload + extraction endpoint
│   │   │   │   └── history.py        # list/get saved extractions (auth required)
│   │   ├── core/
│   │   │   ├── config.py             # env vars, settings
│   │   │   ├── security.py           # JWT, password hashing
│   │   │   └── deps.py               # FastAPI dependencies (get_current_user, optional_user)
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── models/
│   │   │       ├── user.py
│   │   │       └── extraction.py
│   │   ├── services/
│   │   │   ├── vision_llm.py         # calls Claude Haiku, falls back to GPT-4o mini
│   │   │   ├── image_validation.py   # size/type checks
│   │   │   ├── image_optimize.py     # resize/re-encode before R2 upload
│   │   │   ├── storage_r2.py         # Cloudflare R2 upload/URL generation
│   │   │   └── rate_limit.py         # check-and-increment against rate_limits table
│   │   └── schemas/
│   │       ├── auth.py
│   │       └── extraction.py
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte          # upload + result view
│   │   │   ├── login/+page.svelte
│   │   │   ├── signup/+page.svelte
│   │   │   └── history/+page.svelte  # signed-in only
│   │   ├── lib/
│   │   │   ├── api.ts                # fetch wrapper
│   │   │   └── stores/auth.ts
│   ├── package.json
│   └── Dockerfile
└── README.md
```

## 5. Database Schema (initial)

**users**
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| email | text, unique, not null | |
| password_hash | text, nullable | nullable so OAuth-only users are possible later |
| created_at | timestamptz | |

**auth_providers** (future-proofing for OAuth)
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| user_id | uuid, FK → users.id | |
| provider | text | e.g. 'google', 'github' |
| provider_user_id | text | |
| created_at | timestamptz | |

**extractions**
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| user_id | uuid, FK → users.id, not null | only rows for signed-in users exist |
| job_title | text | |
| company | text | |
| description | text | |
| skills_required | text[] or jsonb | |
| location | text, nullable | |
| employment_type | text, nullable | |
| salary_range | text, nullable | |
| llm_provider | text | 'gemini' or 'groq', whichever actually served the request |
| raw_llm_response | jsonb | for debugging/audit |
| image_url | text, not null | Cloudflare R2 URL of the optimized image |
| created_at | timestamptz | |

> Note: only persist rows for authenticated requests — anonymous extractions never touch this table, and never get an R2 upload.

**rate_limits**
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| key | text, not null | client IP (anonymous) or `user_id` (signed-in) |
| key_type | text | 'ip' or 'user' |
| request_date | date, not null | UTC date bucket |
| count | integer, not null, default 0 | |

Unique constraint on `(key, key_type, request_date)`; increment atomically (`INSERT ... ON CONFLICT DO UPDATE SET count = count + 1`) and check against the daily cap (3 for IP, 5 for user) before allowing the LLM call.

## 6. Key API Endpoints (draft)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | none | email/password signup |
| POST | `/auth/login` | none | returns access + refresh JWT |
| POST | `/auth/refresh` | refresh token | rotate access token |
| POST | `/extract` | optional | upload image → returns extracted job data; saves to DB + R2 only if authenticated; 429 if daily quota exceeded |
| GET | `/history` | required | list current user's saved extractions |
| GET | `/history/{id}` | required | get one saved extraction |
| DELETE | `/history/{id}` | required | delete a saved extraction |
| GET | `/rate-limit-status` | optional | returns remaining quota for the day (useful for frontend to show "2 of 3 left today") |

`/extract` should use an **optional-auth dependency** (resolves `user` if a valid token is present, otherwise `None`) rather than two separate endpoints.

## 7. Environment Variables (.env.example)
```
# Postgres
POSTGRES_USER=app
POSTGRES_PASSWORD=changeme
POSTGRES_DB=job_vacancy_db
DATABASE_URL=postgresql+asyncpg://app:changeme@db:5432/job_vacancy_db

# Auth
JWT_SECRET=changeme
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Vision LLM (free tier — primary + fallback)
GEMINI_API_KEY=changeme
GEMINI_VISION_MODEL=gemini-2.0-flash   # verify current free-tier model name at request time
GROQ_API_KEY=changeme
GROQ_VISION_MODEL=llama-3.2-90b-vision-preview   # verify current free-tier model name at request time

# Upload limits
MAX_IMAGE_SIZE_MB=5
ALLOWED_IMAGE_TYPES=image/jpeg,image/png,image/webp

# Rate limits
ANON_DAILY_LIMIT=3
USER_DAILY_LIMIT=5

# Cloudflare R2
R2_ACCOUNT_ID=changeme
R2_ACCESS_KEY_ID=changeme
R2_SECRET_ACCESS_KEY=changeme
R2_BUCKET_NAME=job-vacancy-images
R2_PUBLIC_BASE_URL=https://pub-xxxx.r2.dev   # or custom domain fronting the bucket
```

## 8. Docker Compose Sketch
```yaml
services:
  db:
    image: postgres:17-bookworm
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    env_file: .env
    depends_on:
      - db
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend   # Dockerfile uses `oven/bun` base image, `bun install` / `bun run dev`
    env_file: .env
    depends_on:
      - backend
    ports:
      - "5173:5173"

volumes:
  pgdata:
```

## 9. Security / Validation Notes
- Validate image size and MIME type **server-side** before sending anything to the LLM (don't trust the client).
- Enforce the daily rate limit (§4 item 4 / `rate_limits` table) **before** calling any LLM — check-and-increment atomically to avoid race conditions from concurrent requests.
- Store password hashes with a strong algorithm (e.g. bcrypt/argon2), never plaintext.
- Sanitize/validate LLM output before persisting — treat it as untrusted structured data, not code.
- Image optimization before R2 upload (signed-in only): re-encode to a capped max dimension (e.g. 1600px longest side) and reasonable JPEG/WebP quality to keep storage costs down.
- R2 bucket should not be public-write; backend uploads via signed credentials, and either serves a public-read URL or signed GET URLs depending on how private you want saved images to be.
- Never log full API keys or full JWTs, even in debug mode.

## 10. Open Decisions / TODO
- [ ] Exact system prompt / output schema for the vision LLM call (JSON schema enforcement, retries on malformed output).
- [ ] Whether `/rate-limit-status` is needed at launch or can be added later (nice-to-have for UX, not required for core behavior).
- [ ] R2 bucket access model: public-read URLs vs. signed URLs with expiry.
- [ ] Google/GitHub OAuth: not implemented now — `auth_providers` table and login UI should just avoid assumptions that'd make adding them later painful (e.g. don't require `password_hash` to be non-null).
- [ ] Verify current Gemini and Groq free-tier vision model names/limits at implementation time — these change periodically and the ones in this doc are placeholders.
- [ ] Confirm Gemini/Groq free-tier daily/rate limits comfortably cover personal use volume (3/day anon + 5/day signed-in is small, so should be fine, but worth a sanity check against current published limits).
- [ ] Cloudflare Tunnel for exposing the app publicly (portfolio demo) — separate from the LLM choice, not yet scoped.
