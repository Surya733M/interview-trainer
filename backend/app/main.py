"""
main.py — FastAPI Application Entry Point
==========================================
This is the first file executed when the backend starts.

Responsibilities:
  1. Create the FastAPI application instance
  2. Configure CORS (Cross-Origin Resource Sharing) — required for React frontend
  3. Register all route modules (auth, resume, interview, report, dashboard)
  4. Add startup/shutdown lifecycle events (DB init, ChromaDB init)
  5. Provide a health-check endpoint for deployment monitoring

Architecture note:
  main.py is intentionally thin — it only wires things together.
  All business logic lives in services/, all HTTP logic in routes/.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.utils.logger import logger

# ── Import routers (will be created in later steps) ───────────────────────────
# We import them inside the lifespan function to avoid circular imports at boot
# For now we register placeholders; real routers added in Step 4 onwards


# ── Lifespan: startup + shutdown logic ────────────────────────────────────────
# asynccontextmanager lets us run setup code before yield and cleanup after yield
# FastAPI runs the code before yield on startup and after yield on shutdown

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Code before `yield` → runs on startup.
    Code after  `yield` → runs on shutdown.
    """
    # ── STARTUP ───────────────────────────────────────────────────────────────
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"  Debug mode : {settings.debug}")
    logger.info(f"  Database   : {settings.database_url}")
    logger.info(f"  Frontend   : {settings.frontend_url}")

    # Create upload and reports directories if they don't exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs("./reports", exist_ok=True)
    os.makedirs("./logs", exist_ok=True)
    logger.info("Storage directories verified.")

    # Initialise database tables
    from app.database import init_db
    init_db()
    logger.info("Database initialised.")

    logger.success("Application startup complete.")

    yield  # ← Application is running while paused here

    # ── SHUTDOWN ──────────────────────────────────────────────────────────────
    logger.info("Application shutting down...")


# ── Create FastAPI instance ────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered Interview Trainer using IBM Granite + RAG. "
        "Upload your resume and get personalised mock interviews."
    ),
    # Swagger UI available at /docs
    docs_url="/docs" if settings.debug else None,
    # ReDoc UI available at /redoc
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)


# ── CORS Middleware ────────────────────────────────────────────────────────────
# CORS (Cross-Origin Resource Sharing) must be enabled because:
#   - React frontend runs on http://localhost:5173
#   - FastAPI backend runs on http://localhost:8000
#   - Browsers block cross-origin requests by default
#   - This middleware adds the required "Access-Control-Allow-Origin" headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,          # React dev server
        "http://localhost:5173",        # Vite default
        "http://localhost:3000",        # Create React App fallback
    ],
    allow_credentials=True,            # Allow cookies / auth headers
    allow_methods=["*"],               # Allow GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],               # Allow all headers including Authorization
)


# ── Static Files ──────────────────────────────────────────────────────────────
# Serve generated PDF reports at /static/reports/<filename>
# This lets the frontend download reports without a separate file endpoint
if os.path.exists("./reports"):
    app.mount("/static/reports", StaticFiles(directory="./reports"), name="reports")


# ── Health Check Endpoint ─────────────────────────────────────────────────────
# Used by IBM Cloud / load balancers to verify the service is alive
# Always returns 200 OK with basic status info
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns application name, version, and status.
    IBM Cloud Code Engine pings this to verify the container is healthy.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
    }


# ── Root Endpoint ─────────────────────────────────────────────────────────────
@app.get("/", tags=["System"])
async def root():
    """Root endpoint — confirms API is running."""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "docs": "/docs",
        "health": "/health",
    }


# ── Register Routers ──────────────────────────────────────────────────────────
# Routers are added here with a URL prefix and tag for grouping in Swagger UI
# Uncomment each as we build the corresponding step:

from app.routes import auth, resume, interview, report
app.include_router(auth.router)
app.include_router(resume.router)
app.include_router(interview.router)
app.include_router(report.router)
app.include_router(report.dashboard_router)

logger.info("All routers registered.")
