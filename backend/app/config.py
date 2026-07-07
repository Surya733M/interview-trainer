"""
config.py — Central Application Settings
=========================================
Uses pydantic-settings to automatically read values from the .env file.
Every service imports `settings` from this module.

How it works:
  1. pydantic-settings reads your .env file on startup.
  2. Each field is type-validated (e.g., int, bool, str).
  3. If a required field is missing, the app crashes early with a clear error
     instead of failing silently later at runtime.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application-wide settings loaded from environment variables / .env file.
    Field names must EXACTLY match the keys in your .env file (case-insensitive).
    """

    # ── Application ───────────────────────────────────────────────────────────
    app_name: str = "Interview Trainer Agent"
    app_version: str = "1.0.0"
    debug: bool = True

    # JWT secret — used to sign and verify access tokens
    secret_key: str = "fallback-insecure-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # ── Database ──────────────────────────────────────────────────────────────
    # SQLite path for dev; replace with PostgreSQL URL for production
    database_url: str = "sqlite:///./interview_trainer.db"

    # ── IBM watsonx.ai ────────────────────────────────────────────────────────
    watsonx_api_key: str = ""
    watsonx_project_id: str = ""
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"

    # IBM Granite model identifiers
    granite_model_id: str = "ibm/granite-13b-chat-v2"
    granite_embed_model_id: str = "ibm/slate-125m-english-rtrvr"

    # ── IBM Cloud Object Storage ──────────────────────────────────────────────
    cos_api_key: str = ""
    cos_instance_crn: str = ""
    cos_endpoint: str = "https://s3.us-south.cloud-object-storage.appdomain.cloud"
    cos_bucket_name: str = "interview-trainer-resumes"

    # ── ChromaDB Vector Store ─────────────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "interview_knowledge_base"

    # ── File Upload ───────────────────────────────────────────────────────────
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 10
    allowed_extensions: str = "pdf"

    # ── CORS ──────────────────────────────────────────────────────────────────
    frontend_url: str = "http://localhost:5173"

    # ── Pydantic-settings config ──────────────────────────────────────────────
    # env_file: tells pydantic-settings where to find the .env file
    # extra="ignore": silently ignore any extra keys in .env that we haven't declared
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# @lru_cache ensures Settings() is only instantiated once per process.
# This is important because reading files on every request would be slow.
@lru_cache()
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()


# Module-level singleton — import this directly in other modules
# Usage: from app.config import settings
settings = get_settings()
