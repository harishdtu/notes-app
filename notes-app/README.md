# Notes API

A multi-user notes backend service built with **FastAPI + SQLite + JWT auth**.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | FastAPI |
| Database | SQLite (local) / PostgreSQL (production) |
| Auth | JWT via python-jose |
| Password hashing | bcrypt via passlib |
| ORM | SQLAlchemy |
| Deployment | Render.com |

---

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/register` | — | Register new user |
| POST | `/login` | — | Login, returns JWT |
| GET | `/notes` | ✅ | Get all accessible notes (paginated) |
| GET | `/notes/{id}` | ✅ | Get a specific note |
| POST | `/notes` | ✅ | Create a note |
| PUT | `/notes/{id}` | ✅ | Update a note |
| DELETE | `/notes/{id}` | ✅ | Delete a note |
| POST | `/notes/{id}/share` | ✅ | Share note with another user |
| PATCH | `/notes/{id}/pin` | ✅ | Toggle pin on a note |
| GET | `/search?q=keyword` | ✅ | Full-text search (title + content) |
| GET | `/openapi.json` | — | OpenAPI spec |
| GET | `/about` | — | About this API |
| GET | `/docs` | — | Interactive Swagger UI |

---

## My Extra Features

### 1. Pin / Unpin Notes (`PATCH /notes/{id}/pin`)
Toggles a note's `is_pinned` field. Pinned notes always sort to the top of `GET /notes`. Only the note owner can pin. This mirrors the most-used UX pattern in Google Keep and Apple Notes.

### 2. Full-text Search (`GET /search?q=keyword`)
Case-insensitive search across title AND content of all notes accessible to the current user (owned + shared). Fast SQLite LIKE query.

### 3. Pagination (`GET /notes?page=1&per_page=20`)
Prevents returning unbounded data. Defaults: page=1, per_page=20, max per_page=100.

---

## Run Locally

```bash
# Clone & enter project
git clone <your-repo-url>
cd notes-app

# Install dependencies
pip install -r requirements.txt

# Start server
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs.

---

## Deploy to Render.com (Free Tier)

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `SECRET_KEY` → any long random string (e.g. from `openssl rand -hex 32`)
6. Click **Deploy**

Your base URL will be something like `https://notes-api-xxxx.onrender.com`.

> ⚠️ **Update `/about`** with your real name and email before deploying!

---

## Deploy with Docker

```bash
docker build -t notes-api .
docker run -p 8000:8000 -e SECRET_KEY=your-secret notes-api
```

---

## Edge Cases Handled

- Duplicate email registration → 409
- Wrong password → 401
- Access note you don't own/share → 404
- Share note with yourself → 400
- Share note already shared → idempotent 200
- Empty/whitespace title → 422
- Invalid JWT → 401
- Non-existent note ID → 404
- Invalid pagination params → 422
