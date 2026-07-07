"""
logger.py — Application-wide Logging Setup
===========================================
Uses loguru for structured, colorised, levelled logging.

Why loguru over Python's built-in logging?
  - Zero-config colourised console output
  - Automatic log rotation (max file size, retention days)
  - Thread-safe and async-safe
  - Single import: `from app.utils.logger import logger`

Log levels (in order of severity):
  TRACE < DEBUG < INFO < SUCCESS < WARNING < ERROR < CRITICAL
"""

import sys
from loguru import logger

# ── Remove the default loguru handler ─────────────────────────────────────────
# loguru adds one by default; we replace it with our configured version
logger.remove()

# ── Console Handler ───────────────────────────────────────────────────────────
# Format explanation:
#   {time:YYYY-MM-DD HH:mm:ss} → human-readable timestamp
#   {level: <8}                → log level, left-aligned in 8 chars
#   {name}:{function}:{line}   → exactly where the log was called
#   {message}                  → the actual log message
logger.add(
    sys.stdout,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "{message}"
    ),
    level="DEBUG",          # Show DEBUG and above in development
    colorize=True,          # Enable ANSI colours in terminal
    backtrace=True,         # Show full stack trace on errors
    diagnose=True,          # Show variable values in stack traces (dev only)
)

# ── File Handler ──────────────────────────────────────────────────────────────
# Writes WARNING and above to a rotating log file
# rotation="10 MB"    → start a new file when current reaches 10 MB
# retention="7 days"  → delete log files older than 7 days
# compression="zip"   → compress old log files to save disk space
logger.add(
    "logs/app.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="WARNING",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
)

# Re-export logger so other modules just do:
# from app.utils.logger import logger
__all__ = ["logger"]
