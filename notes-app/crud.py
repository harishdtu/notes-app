from sqlalchemy.orm import Session
from sqlalchemy import or_
import models, schemas, auth
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


# ─── Users ───────────────────────────────────────────────────────────────────

def get_user_by_email(db: Session, email: str) -> models.User | None:
    return db.query(models.User).filter(models.User.email == email.lower().strip()).first()


def create_user(db: Session, user: schemas.UserCreate) -> models.User:
    hashed = auth.hash_password(user.password)
    db_user = models.User(email=user.email.lower().strip(), hashed_password=hashed)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


# ─── Notes ───────────────────────────────────────────────────────────────────

def get_notes_for_user(db: Session, user_id: str, page: int = 1, per_page: int = 20):
    """Return notes owned by user + notes shared with user, pinned first."""
    shared_note_ids = (
        db.query(models.NoteShare.note_id)
        .filter(models.NoteShare.shared_with_user_id == user_id)
        .scalar_subquery()
    )
    return (
        db.query(models.Note)
        .filter(
            or_(
                models.Note.owner_id == user_id,
                models.Note.id.in_(shared_note_ids),
            )
        )
        .order_by(models.Note.is_pinned.desc(), models.Note.updated_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )


def get_note_owned_by_user(db: Session, note_id: str, user_id: str) -> models.Note | None:
    return (
        db.query(models.Note)
        .filter(models.Note.id == note_id, models.Note.owner_id == user_id)
        .first()
    )


def get_note_accessible_by_user(db: Session, note_id: str, user_id: str) -> models.Note | None:
    """Returns the note if the user owns it or has been granted share access."""
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        return None
    if note.owner_id == user_id:
        return note
    share = (
        db.query(models.NoteShare)
        .filter(
            models.NoteShare.note_id == note_id,
            models.NoteShare.shared_with_user_id == user_id,
        )
        .first()
    )
    return note if share else None


def create_note(db: Session, payload: schemas.NoteCreate, owner_id: str) -> models.Note:
    note = models.Note(
        title=payload.title.strip(),
        content=payload.content or "",
        owner_id=owner_id,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def update_note(db: Session, note: models.Note, payload: schemas.NoteUpdate) -> models.Note:
    if payload.title is not None:
        note.title = payload.title.strip()
    if payload.content is not None:
        note.content = payload.content
    note.updated_at = utcnow()
    db.commit()
    db.refresh(note)
    return note


def delete_note(db: Session, note: models.Note) -> None:
    db.delete(note)
    db.commit()


# ─── Sharing ─────────────────────────────────────────────────────────────────

def is_note_shared_with_user(db: Session, note_id: str, user_id: str) -> bool:
    return (
        db.query(models.NoteShare)
        .filter(
            models.NoteShare.note_id == note_id,
            models.NoteShare.shared_with_user_id == user_id,
        )
        .first()
        is not None
    )


def share_note(db: Session, note_id: str, user_id: str) -> models.NoteShare:
    share = models.NoteShare(note_id=note_id, shared_with_user_id=user_id)
    db.add(share)
    db.commit()
    return share


# ─── Search ──────────────────────────────────────────────────────────────────

def search_notes(db: Session, user_id: str, query: str):
    """Case-insensitive full-text search across title + content for accessible notes."""
    shared_note_ids = (
        db.query(models.NoteShare.note_id)
        .filter(models.NoteShare.shared_with_user_id == user_id)
        .scalar_subquery()
    )
    like = f"%{query}%"
    return (
        db.query(models.Note)
        .filter(
            or_(
                models.Note.owner_id == user_id,
                models.Note.id.in_(shared_note_ids),
            )
        )
        .filter(
            or_(
                models.Note.title.ilike(like),
                models.Note.content.ilike(like),
            )
        )
        .order_by(models.Note.is_pinned.desc(), models.Note.updated_at.desc())
        .all()
    )


# ─── Pin ─────────────────────────────────────────────────────────────────────

def toggle_pin(db: Session, note: models.Note) -> models.Note:
    note.is_pinned = not note.is_pinned
    note.updated_at = utcnow()
    db.commit()
    db.refresh(note)
    return note
