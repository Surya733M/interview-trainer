#!/usr/bin/env bash
# =============================================================================
# deploy-ibmcloud.sh — Manual IBM Cloud Deployment Script
# =============================================================================
#
# USE THIS WHEN:
#   - You want to deploy manually (without waiting for GitHub Actions)
#   - You are testing the deployment for the first time
#   - You need to deploy from your local machine
#
# PREREQUISITES:
#   1. IBM Cloud CLI installed: https://cloud.ibm.com/docs/cli
#   2. IBM Cloud Container Registry plugin: ibmcloud plugin install container-registry
#   3. IBM Cloud Code Engine plugin: ibmcloud plugin install code-engine
#   4. Docker Desktop running
#   5. Node.js installed (for building frontend)
#   6. Copy .env.production and fill in all values before running
#
# HOW TO RUN:
#   chmod +x deploy-ibmcloud.sh
#   ./deploy-ibmcloud.sh
#
# =============================================================================

set -e  # Exit immediately on any error
set -u  # Treat unset variables as errors

# ── Configuration — edit these before running ─────────────────────────────────
IBM_CLOUD_API_KEY="${IBM_CLOUD_API_KEY:-}"
IBM_CLOUD_REGION="${IBM_CLOUD_REGION:-us-south}"
ICR_NAMESPACE="${ICR_NAMESPACE:-interview-trainer-ns}"
CE_PROJECT_NAME="${CE_PROJECT_NAME:-interview-trainer-project}"
CE_APP_NAME="${CE_APP_NAME:-interview-trainer-api}"
IMAGE_NAME="interview-trainer-api"
REGISTRY="us.icr.io"
FULL_IMAGE="${REGISTRY}/${ICR_NAMESPACE}/${IMAGE_NAME}:latest"

# ── Colour helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()    { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
info "Starting deployment of Interview Trainer Agent to IBM Cloud..."

[[ -z "$IBM_CLOUD_API_KEY" ]] && \
  error "IBM_CLOUD_API_KEY is not set. Export it before running: export IBM_CLOUD_API_KEY=your_key"

command -v ibmcloud  >/dev/null 2>&1 || error "ibmcloud CLI not found. Install from https://cloud.ibm.com/docs/cli"
command -v docker    >/dev/null 2>&1 || error "Docker not found. Install Docker Desktop."
command -v node      >/dev/null 2>&1 || error "Node.js not found."
command -v npm       >/dev/null 2>&1 || error "npm not found."

info "All prerequisites found."

# ── Step 1: Build frontend ────────────────────────────────────────────────────
info "Building React frontend for production..."
cd frontend
npm ci
npm run build
cd ..
# Copy frontend build into backend/static so it's served by FastAPI
mkdir -p backend/static
cp -r frontend/dist/* backend/static/
info "Frontend build complete. Files copied to backend/static/"

# ── Step 2: Login to IBM Cloud ────────────────────────────────────────────────
info "Logging in to IBM Cloud..."
ibmcloud login --apikey "$IBM_CLOUD_API_KEY" -r "$IBM_CLOUD_REGION" --quiet

# ── Step 3: Setup IBM Container Registry ──────────────────────────────────────
info "Setting up IBM Container Registry..."
ibmcloud plugin install container-registry -f --quiet 2>/dev/null || true
ibmcloud cr login
ibmcloud cr namespace-add "$ICR_NAMESPACE" 2>/dev/null || \
  warn "Namespace $ICR_NAMESPACE already exists (OK)."

# ── Step 4: Build Docker image ────────────────────────────────────────────────
info "Building Docker image: $FULL_IMAGE"
cd backend
docker build \
  --tag "$FULL_IMAGE" \
  --label "git-commit=$(git rev-parse --short HEAD 2>/dev/null || echo 'manual')" \
  --label "build-date=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  .
cd ..
info "Docker image built successfully."

# ── Step 5: Push image to ICR ─────────────────────────────────────────────────
info "Pushing image to IBM Container Registry..."
docker push "$FULL_IMAGE"
info "Image pushed: $FULL_IMAGE"

# ── Step 6: Deploy to Code Engine ─────────────────────────────────────────────
info "Setting up IBM Cloud Code Engine..."
ibmcloud plugin install code-engine -f --quiet 2>/dev/null || true

# Create project if it doesn't exist
ibmcloud ce project create --name "$CE_PROJECT_NAME" 2>/dev/null || \
  warn "Project $CE_PROJECT_NAME already exists (OK)."

ibmcloud ce project select --name "$CE_PROJECT_NAME"

# Load production environment variables from .env.production
info "Loading production environment variables..."
[[ ! -f ".env.production" ]] && \
  error ".env.production not found. Copy env.production.example and fill in your values."

# Source the production env file
set -a
source .env.production
set +a

info "Deploying application to Code Engine..."

# Update or create the Code Engine application
ibmcloud ce application update \
  --name "$CE_APP_NAME" \
  --image "$FULL_IMAGE" \
  --min-scale 1 \
  --max-scale 3 \
  --cpu 1 \
  --memory 4G \
  --port 8000 \
  --env ENV=production \
  --env SECRET_KEY="${SECRET_KEY}" \
  --env DATABASE_URL="${DATABASE_URL}" \
  --env WATSONX_API_KEY="${WATSONX_API_KEY}" \
  --env WATSONX_PROJECT_ID="${WATSONX_PROJECT_ID}" \
  --env WATSONX_URL="${WATSONX_URL:-https://us-south.ml.cloud.ibm.com}" \
  --env GRANITE_MODEL_ID="${GRANITE_MODEL_ID:-ibm/granite-13b-chat-v2}" \
  --env COS_API_KEY="${COS_API_KEY}" \
  --env COS_INSTANCE_CRN="${COS_INSTANCE_CRN}" \
  --env FRONTEND_URL="${FRONTEND_URL}" \
  2>/dev/null || \
ibmcloud ce application create \
  --name "$CE_APP_NAME" \
  --image "$FULL_IMAGE" \
  --min-scale 1 \
  --max-scale 3 \
  --cpu 1 \
  --memory 4G \
  --port 8000 \
  --env ENV=production \
  --env SECRET_KEY="${SECRET_KEY}" \
  --env DATABASE_URL="${DATABASE_URL}" \
  --env WATSONX_API_KEY="${WATSONX_API_KEY}" \
  --env WATSONX_PROJECT_ID="${WATSONX_PROJECT_ID}" \
  --env WATSONX_URL="${WATSONX_URL:-https://us-south.ml.cloud.ibm.com}" \
  --env GRANITE_MODEL_ID="${GRANITE_MODEL_ID:-ibm/granite-13b-chat-v2}" \
  --env COS_API_KEY="${COS_API_KEY}" \
  --env COS_INSTANCE_CRN="${COS_INSTANCE_CRN}" \
  --env FRONTEND_URL="${FRONTEND_URL}"

# ── Step 7: Get the application URL ───────────────────────────────────────────
info "Waiting for deployment to stabilise (30s)..."
sleep 30

APP_URL=$(ibmcloud ce application get --name "$CE_APP_NAME" --output json 2>/dev/null | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',{}).get('url','NOT FOUND'))" \
)

info "==================================================================="
info "Deployment complete!"
info "Application URL : $APP_URL"
info "Health check    : $APP_URL/health"
info "API Docs        : $APP_URL/docs"
info "==================================================================="

# Verify health check
info "Running health check..."
if curl -sf "$APP_URL/health" > /dev/null 2>&1; then
  info "Health check PASSED."
else
  warn "Health check pending — the app may need 1-2 minutes to warm up."
  warn "Run manually: curl $APP_URL/health"
fi
