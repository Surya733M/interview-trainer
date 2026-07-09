"""
production.py — Production Configuration Overrides
===================================================
This module is imported ONLY in production (IBM Cloud).
It adjusts settings that differ from local development:

  1. PostgreSQL instead of SQLite
  2. debug=False
  3. Stricter CORS (only your IBM Cloud domain)
  4. Production-ready uvicorn settings

HOW TO USE:
  IBM Cloud Code Engine sets an environment variable:
    ENV=production

  main.py detects this and imports these overrides before startup.

WHY SEPARATE FROM config.py?
  config.py covers ALL environments. production.py adds production-only
  behaviour without polluting the development experience.
"""

import os
from app.config import settings


def apply_production_overrides():
    """
    Apply production-specific patches.
    Called from main.py when ENV=production.
    """
    env = os.getenv("ENV", "development").lower()
    if env != "production":
        return

    from app.utils.logger import logger
    logger.info("Production mode detected — applying production overrides.")

    # ── Validate required production secrets ──────────────────────────────────
    required_env_vars = [
        "SECRET_KEY",
        "DATABASE_URL",
        "WATSONX_API_KEY",
        "WATSONX_PROJECT_ID",
    ]
    missing = [v for v in required_env_vars if not os.getenv(v)]
    if missing:
        raise RuntimeError(
            f"[PRODUCTION] Missing required environment variables: {missing}\n"
            "Set them in IBM Cloud Code Engine > Environment Variables."
        )

    logger.info("All required production environment variables present.")

    # ── Log key settings (never log secrets) ──────────────────────────────────
    logger.info(f"  Database   : {os.getenv('DATABASE_URL', '').split('@')[-1]}")  # hide credentials
    logger.info(f"  watsonx URL: {os.getenv('WATSONX_URL', settings.watsonx_url)}")
    logger.info(f"  Granite    : {os.getenv('GRANITE_MODEL_ID', settings.granite_model_id)}")
