from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn

from database import get_db, engine, Base
import models, schemas, auth, crud

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Notes API",
    description="A multi-user notes service API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse("frontend/favicon.ico")


# ─── Auth ────────────────────────────────────────────────────────────────────

@app.post("/register", status_code=201)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if not user.email or "@" not in user.email:
        raise HTTPException(status_code=422, detail="Invalid email format")
    if not user.password or len(user.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    crud.create_user(db, user)
    return {"message": "User registered successfully"}


@app.post("/login", status_code=200)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, credentials.email)
    if not user or not auth.verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth.create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


# ─── Notes CRUD ──────────────────────────────────────────────────────────────

@app.get("/notes", response_model=List[schemas.NoteOut], status_code=200)
def get_notes(
    page: int = 1,
    per_page: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if page < 1 or per_page < 1 or per_page > 100:
        raise HTTPException(status_code=422, detail="Invalid pagination parameters")
    return crud.get_notes_for_user(db, current_user.id, page=page, per_page=per_page)


@app.get("/notes/{id}", response_model=schemas.NoteOut, status_code=200)
def get_note(
    id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    note = crud.get_note_accessible_by_user(db, id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@app.post("/notes", response_model=schemas.NoteOut, status_code=201)
def create_note(
    payload: schemas.NoteCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=422, detail="Title cannot be empty")
    return crud.create_note(db, payload, current_user.id)


@app.put("/notes/{id}", response_model=schemas.NoteOut, status_code=200)
def update_note(
    id: str,
    payload: schemas.NoteUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    note = crud.get_note_owned_by_user(db, id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or not owned by you")
    if payload.title is not None and not payload.title.strip():
        raise HTTPException(status_code=422, detail="Title cannot be empty")
    return crud.update_note(db, note, payload)


@app.delete("/notes/{id}", status_code=204)
def delete_note(
    id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    note = crud.get_note_owned_by_user(db, id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or not owned by you")
    crud.delete_note(db, note)


@app.post("/notes/{id}/share", status_code=200)
def share_note(
    id: str,
    payload: schemas.ShareNote,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    note = crud.get_note_owned_by_user(db, id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or not owned by you")
    target_user = crud.get_user_by_email(db, payload.share_with_email)
    if not target_user:
        raise HTTPException(status_code=404, detail="User with that email not found")
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot share a note with yourself")
    already_shared = crud.is_note_shared_with_user(db, note.id, target_user.id)
    if already_shared:
        return {"message": f"Note already shared with {payload.share_with_email}"}
    crud.share_note(db, note.id, target_user.id)
    return {"message": f"Note shared successfully with {payload.share_with_email}"}


# ─── Stretch: Full-text search ────────────────────────────────────────────────

@app.get("/search", response_model=List[schemas.NoteOut], status_code=200)
def search_notes(
    q: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if not q or not q.strip():
        raise HTTPException(status_code=422, detail="Search query cannot be empty")
    return crud.search_notes(db, current_user.id, q.strip())


# ─── Feature: Pin / Unpin note ───────────────────────────────────────────────

@app.patch("/notes/{id}/pin", response_model=schemas.NoteOut, status_code=200)
def toggle_pin(
    id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Toggle the pinned state of a note. Pinned notes float to the top of GET /notes.
    Only the note owner can pin/unpin.
    """
    note = crud.get_note_owned_by_user(db, id, current_user.id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found or not owned by you")
    return crud.toggle_pin(db, note)


# ─── About ───────────────────────────────────────────────────────────────────

@app.get("/about")
def about():
    return {
        "name": "Harish",
        "email": "satyaharish12345@gmail.com",
        "my_features": {
            "Pin / Unpin Notes": (
                "PATCH /notes/{id}/pin toggles a note's pinned state. "
                "Pinned notes always appear first in GET /notes, mirroring the "
                "UX of Google Keep. Only the note owner can pin. I chose this "
                "because it is one of the most-used features in real note apps "
                "and adds genuine value with minimal complexity."
            ),
            "Full-text Search": (
                "GET /search?q=keyword searches across title and content of all "
                "notes accessible to the user (owned + shared). Case-insensitive "
                "LIKE query — simple and fast for the SQLite backend."
            ),
            "Pagination": (
                "GET /notes supports ?page=&per_page= query params (default 1 / 20). "
                "Prevents returning unbounded data sets and makes the API "
                "production-ready from day one."
            ),
        },
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
