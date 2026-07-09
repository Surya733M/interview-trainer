# =============================================================================
# Interview Trainer Agent — Backend Dockerfile
# =============================================================================
#
# HOW IT WORKS:
#   This is a multi-stage Docker build:
#   Stage 1 (builder): Install Python dependencies into a virtual environment.
#   Stage 2 (runtime): Copy only the venv + app code — keeps the image small.
#
# WHY MULTI-STAGE?
#   - Build tools (gcc, libffi-dev, etc.) are needed to compile some Python
#     packages (like chromadb, sentence-transformers) but NOT needed at runtime.
#   - Multi-stage builds leave those tools behind in Stage 1.
#   - Final image is ~40% smaller and has a smaller attack surface.
#
# BASE IMAGE: python:3.11-slim
#   - Slim variant = no extra apt packages pre-installed.
#   - Python 3.11 is the most stable for our dependencies.
#   - We avoid 3.14 in Docker because some C-extension wheels don't ship for it.
# =============================================================================

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

# Set working directory inside the container
WORKDIR /app

# Install OS-level build tools needed to compile Python packages
# gcc        → needed by chromadb, sentence-transformers
# libffi-dev → needed by cffi/cryptography
# curl       → needed to download spaCy model
# We clean up apt cache at the end to reduce layer size
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (Docker layer cache optimisation)
# If requirements.txt hasn't changed, Docker reuses this cached layer.
COPY requirements.txt .

# Create a virtual environment inside the builder stage
# Isolates our packages from the system Python
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip first (avoids legacy resolver issues with complex deps)
RUN pip install --upgrade pip

# Install all Python dependencies
# --no-cache-dir: don't cache the wheel files (saves image space)
RUN pip install --no-cache-dir -r requirements.txt

# Download the spaCy language model used for resume NLP parsing
RUN python -m spacy download en_core_web_sm

# ── Stage 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Add a non-root user for security best practice
# Running as root inside a container is a security risk
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install only the minimal OS libraries needed at runtime
# (not build tools — those stay in Stage 1)
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy spaCy model from builder (installed into the venv)
# spaCy stores its model inside the venv packages directory

# Set working directory
WORKDIR /app

# Copy application code
COPY app/ ./app/
COPY datasets/ ./datasets/
COPY run.py ./

# Create required directories (will be overridden by volume mounts in prod)
RUN mkdir -p uploads reports logs chroma_db \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Activate the virtual environment by setting PATH
ENV PATH="/opt/venv/bin:$PATH"

# Environment variables with safe defaults
# These will be OVERRIDDEN by IBM Cloud Code Engine environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PORT=8000 \
    DEBUG=false

# Expose port 8000 (FastAPI default)
# IBM Cloud Code Engine routes external HTTPS traffic to this port
EXPOSE 8000

# Health check: Docker / Code Engine pings /health every 30s
# If it fails 3 times → container is restarted automatically
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start the application with uvicorn
# --host 0.0.0.0: listen on all interfaces (required inside container)
# --port: from environment variable (Code Engine sets PORT dynamically)
# --workers 2: 2 processes for better concurrency on IBM Cloud Lite (1 vCPU)
# --no-access-log: reduce noise (Cloud logging captures these separately)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2"]
