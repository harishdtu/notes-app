from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import uuid
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=new_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    shared_accesses = relationship("NoteShare", back_populates="shared_with_user", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=new_uuid)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False, default="")
    is_pinned = Column(Boolean, default=False, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="notes")
    shares = relationship("NoteShare", back_populates="note", cascade="all, delete-orphan")


class NoteShare(Base):
    __tablename__ = "note_shares"

    id = Column(String, primary_key=True, default=new_uuid)
    note_id = Column(String, ForeignKey("notes.id"), nullable=False)
    shared_with_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    shared_at = Column(DateTime(timezone=True), default=utcnow)

    note = relationship("Note", back_populates="shares")
    shared_with_user = relationship("User", back_populates="shared_accesses")
