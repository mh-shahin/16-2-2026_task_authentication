from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from supabase import Client, create_client

from app.core.config import settings
from app.models.base import Base

supabase: Client = create_client(settings.PROJECT_URL, settings.SUPABASE_ANON_KEY)

db_engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG if hasattr(settings, "DEBUG") else False,
)

SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import os
    import app.models

    if os.getenv("ENV", "dev") == "dev":
        Base.metadata.create_all(bind=db_engine)
        print("✅ DEV: Tables ensured with create_all()")
    else:
        print("✅ PROD: Use Alembic migrations, not create_all()")

