from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from app.config import get_settings
from app.models import Session, User
from app.services.security import generate_token


def create_session(
    db: DBSession,
    user: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Session:
    """Creates a new server-side session for a user."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.session_ttl_seconds)

    session = Session(
        id=generate_token(32),
        user_id=user.id,
        csrf_token=generate_token(32),
        expires_at=expires_at,
        created_at=now,
        last_seen_at=now,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def rotate_session(
    db: DBSession,
    old_session_id: Optional[str],
    user: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Session:
    """Invalidates the previous session if present and creates a fresh session."""
    if old_session_id:
        existing = db.get(Session, old_session_id)
        if existing and existing.user_id == user.id:
            db.delete(existing)
            db.commit()
    return create_session(db, user, ip_address=ip_address, user_agent=user_agent)


def get_active_session(db: DBSession, session_id: str) -> Optional[Session]:
    """Retrieves an active, unexpired session and updates its last_seen_at timestamp."""
    if not session_id:
        return None

    session = db.get(Session, session_id)
    if not session:
        return None

    now = datetime.now(timezone.utc)
    # Ensure expires_at is timezone-aware
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at <= now:
        db.delete(session)
        db.commit()
        return None

    if not session.user.is_active:
        db.delete(session)
        db.commit()
        return None

    session.last_seen_at = now
    db.commit()
    return session


def invalidate_session(db: DBSession, session_id: str) -> bool:
    """Explicitly deletes a session from the database (logout/revocation)."""
    if not session_id:
        return False
    session = db.get(Session, session_id)
    if session:
        db.delete(session)
        db.commit()
        return True
    return False
