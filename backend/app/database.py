"""
database.py — Database Connection & Session Management
=======================================================
Sets up SQLAlchemy to connect to SQLite (dev) or PostgreSQL (prod).

Key concepts:
  - engine       : the actual database connection (one per app)
  - SessionLocal : a factory that creates individual DB sessions
  - Base         : all ORM models inherit from this — it tracks all tables
  - get_db()     : a FastAPI dependency — gives each request its own session,
                   then closes it automatically when the request ends

SQLite vs PostgreSQL:
  In .env:  DATABASE_URL="sqlite:///./interview_trainer.db"   ← dev
  In .env:  DATABASE_URL="postgresql://user:pass@host/dbname" ← prod
  The rest of the code never changes.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import settings
from app.utils.logger import logger

# ── Engine ────────────────────────────────────────────────────────────────────
# connect_args={"check_same_thread": False} is REQUIRED for SQLite only.
# SQLite does not allow multiple threads to share a connection by default.
# FastAPI is async and uses multiple threads, so we must disable this check.
# PostgreSQL does not need this flag.

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    # echo=True prints every SQL query to console — useful for debugging
    echo=settings.debug,
)

# ── Session Factory ───────────────────────────────────────────────────────────
# autocommit=False → we manually commit transactions (safer — errors = rollback)
# autoflush=False  → we manually flush (prevents premature DB writes)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ── Declarative Base ──────────────────────────────────────────────────────────
# All ORM model classes will inherit from Base.
# SQLAlchemy uses Base's metadata to know which tables to create.
Base = declarative_base()


# ── Database Initialiser ──────────────────────────────────────────────────────
def init_db() -> None:
    """
    Create all tables defined in ORM models.
    Called once at application startup (in main.py lifespan).

    Important: all model files must be imported BEFORE this is called,
    otherwise SQLAlchemy doesn't know those tables exist.
    """
    # Import all models here so SQLAlchemy registers them before create_all()
    from app.models import user, interview, report  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.success("Database tables created/verified.")


# ── Request-scoped Session Dependency ─────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.

    Usage in a route:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            result = db.query(User).all()
            return result

    How it works:
      1. A new Session is created for this request
      2. The route function runs (using the session)
      3. After the route finishes, the finally block closes the session
      4. If an exception occurred, any uncommitted changes are rolled back
    """
    db = SessionLocal()
    try:
        yield db          # ← route function runs here
    finally:
        db.close()        # ← always runs, even if an exception occurred
