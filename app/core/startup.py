from datetime import datetime, timezone
from app.core.config import settings
from app.core.security import hash_password
from app.database import get_db as supabase, SessionLocal
from sqlalchemy import select
from app.models.auth import User

def ensure_admin_user():
    db = SessionLocal()
    try:
        existing = db.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        ).scalar_one_or_none()

        if existing:
            return

        admin = User(
            username="admin",
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            role="admin",
            is_verified=True,
            otp_code=None,
            otp_expires_at=None,  
            otp_attempts=0,
        )

        db.add(admin)
        db.commit()
    finally:
        db.close()