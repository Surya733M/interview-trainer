"""
run.py — Development Server Launcher
=====================================
Run this file to start the FastAPI development server.

Usage:
    python run.py

What this does:
  - Starts Uvicorn (the ASGI server) pointing at app/main.py
  - Enables --reload so the server restarts automatically on any code change
  - Listens on http://localhost:8000
  - Opens Swagger UI at http://localhost:8000/docs

Why Uvicorn?
  FastAPI is an ASGI (Async Server Gateway Interface) framework.
  It needs an ASGI-compatible server. Uvicorn is the standard choice —
  it's fast, supports async/await, and handles WebSockets (for future live
  interview streaming features).
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",   # module path : FastAPI instance name
        host="0.0.0.0",   # listen on all interfaces (required for Docker / IBM Cloud)
        port=8000,         # default FastAPI port
        reload=True,       # auto-restart on file changes (dev only)
        log_level="info",  # show INFO logs in console
    )
