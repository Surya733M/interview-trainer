"""
database.py — Database Engine and Session Management
=====================================================
Supports both SQLite (development) and PostgreSQL (production).

WHY TWO DATABASES?
  - SQLite is a file-based database — zero setup, runs anywhere, perfect for
    local development and testing.
  - PostgreSQL is a full enterprise database — supports concurrent connections,
    proper transactions, and scales to millions of rows. Required for production.

HOW THE SWITCH WORKS:
  Both are configured via the DATABASE_URL environment variable:
    SQLite (dev):       sqlite:///./interview_trainer.db
    PostgreSQL (prod):  postgresql://user:pass@host:5432/dbname?sslmode=require

  SQLAlchemy reads DATABASE_URL and automatically adapts to the right driver.

SQLALCHEMY CONCEPTS:
  - Engine:       The "connection factory" — knows HOW to connect.
  - SessionLocal: A "session factory" — creates DB sessions for each request.
  - Base:         The declarative base class all ORM models inherit from.
  - get_db():     A FastAPI dependency that yields one session per HTTP request
                  and closes it automatically, even if an error occurs.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

from app.config import settings
from app.utils.logger import logger


# ── Detect database type from URL ─────────────────────────────────────────────
IS_SQLITE     = settings.database_url.startswith("sqlite")
IS_POSTGRESQL = settings.database_url.startswith("postgresql")


# ── Engine configuration ──────────────────────────────────────────────────────
if IS_SQLITE:
    # SQLite special config:
    # check_same_thread=False → allows multiple threads to use the same connection
    # (required for FastAPI async requests)
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
        # echo=True in debug mode → prints every SQL query to the log
        echo=settings.debug,
    )
    logger.info("Database engine: SQLite (development mode)")

elif IS_POSTGRESQL:
    # PostgreSQL production config:
    # pool_size      → how many persistent connections to maintain
    # max_overflow   → extra connections allowed under heavy load
    # pool_pre_ping  → test connection before using (handles dropped connections)
    # pool_timeout   → max seconds to wait for a connection from the pool
    engine = create_engine(
        settings.database_url,
        pool_size=5,           # 5 persistent connections (Lite plan limit)
        max_overflow=10,       # 10 extra connections during spikes
        pool_pre_ping=True,    # Ping DB before query to catch stale connections
        pool_timeout=30,       # Wait up to 30s for a free connection
        echo=False,            # Never log SQL in production (security)
    )
    logger.info("Database engine: PostgreSQL (production mode)")

else:
    # Fallback for any other database type (e.g., MySQL)
    engine = create_engine(settings.database_url, echo=settings.debug)
    logger.warning(f"Using unknown database type: {settings.database_url.split(':')[0]}")


# ── SQLite WAL mode (for better concurrent read performance) ──────────────────
# WAL = Write-Ahead Logging. Allows reads while a write is happening.
# Only relevant for SQLite; PostgreSQL handles this natively.
if IS_SQLITE:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")    # Enable WAL mode
        cursor.execute("PRAGMA foreign_keys=ON")     # Enforce foreign key constraints
        cursor.close()


# ── Session factory ───────────────────────────────────────────────────────────
# autocommit=False → you must explicitly call db.commit() to save changes.
#                    This ensures operations are atomic (all-or-nothing).
# autoflush=False  → don't automatically sync in-memory objects to DB before
#                    queries. We control this manually.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ── Declarative base ──────────────────────────────────────────────────────────
# All ORM model classes inherit from Base.
# Base keeps a registry of all models so init_db() can create their tables.
Base = declarative_base()


# ── Database initialisation ───────────────────────────────────────────────────
def init_db():
    """
    Create all tables that don't yet exist.

    In DEVELOPMENT (SQLite):
      - Runs on every startup (no migrations needed for schema changes during dev)
      - Tables created automatically from model definitions

    In PRODUCTION (PostgreSQL):
      - Tables created on first deploy
      - Schema changes use Alembic migrations (see alembic/)
      - This function is still called but mostly a no-op once tables exist
    """
    # Import all models here so Base knows about them before creating tables
    # This is the "import side effect" pattern — models register themselves with Base
    from app.models import user, interview, report  # noqa: F401

    logger.info("Creating database tables (if not exist)...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")


# ── Request-scoped session (FastAPI dependency) ───────────────────────────────
def get_db():
    """
    FastAPI dependency that provides a database session for each HTTP request.

    HOW IT WORKS:
      1. yield creates the session and passes it to the route handler
      2. The route handler uses it (e.g., db.query(...))
      3. After the response is sent, finally: db.close() runs automatically
      4. Even if an exception occurs, the session is still closed

    USAGE IN ROUTES:
      @router.get("/items")
      def get_items(db: Session = Depends(get_db)):
          return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
