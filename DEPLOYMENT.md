# Step 20: IBM Cloud Deployment Guide
## Interview Trainer Agent — Complete Production Deployment

---

## What You Are Deploying

```
Single Docker Container (IBM Cloud Code Engine)
│
├── FastAPI backend (port 8000)
│   ├── All API routes (/auth, /resume, /interview, /report)
│   ├── ChromaDB (rebuilt from datasets/ on cold start)
│   └── Serves React frontend (static files at /)
│
└── React frontend (built into backend/static/)
    ├── All pages (Dashboard, Interview, Report, etc.)
    └── Calls /api/* → same container → no CORS
```

**Single container = 1 URL for everything.** Your frontend and backend share the same IBM Cloud domain.

---

## Part A: One-Time IBM Cloud Account Setup

### A1. Create IBM Cloud Account (Free Lite Plan)
1. Go to [cloud.ibm.com](https://cloud.ibm.com) → **Create a free account**
2. Verify your email
3. Choose **Lite plan** (free forever, no credit card needed for most services)

### A2. Install IBM Cloud CLI
```bash
# macOS/Linux:
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh

# Windows (PowerShell as Administrator):
iex(New-Object Net.WebClient).DownloadString('https://clis.cloud.ibm.com/install/powershell')
```

Verify:
```bash
ibmcloud --version
```

Install required plugins:
```bash
ibmcloud plugin install container-registry
ibmcloud plugin install code-engine
```

### A3. Login to IBM Cloud CLI
```bash
ibmcloud login --sso
# Follow the browser link to get a one-time passcode
# Select region: us-south
```

---

## Part B: Create IBM Cloud Services

### B1. IBM Container Registry (ICR) — Docker Image Storage

The Container Registry stores your Docker image. It's like Docker Hub but on IBM Cloud.

```bash
# Login to ICR
ibmcloud cr login

# Create a namespace (like a folder for your images)
ibmcloud cr namespace-add interview-trainer-ns

# Verify
ibmcloud cr namespace-list
```

### B2. IBM Code Engine — Serverless App Hosting

Code Engine runs your Docker container as a serverless app.
Free Lite plan includes: **50 vCPU-hours and 100 GB-hours per month** — enough for a hackathon.

```bash
# Create a Code Engine project
ibmcloud ce project create --name interview-trainer-project

# Select the project
ibmcloud ce project select --name interview-trainer-project
```

### B3. IBM Databases for PostgreSQL (Production Database)

> **Note for Lite Plan:** IBM Cloud Databases for PostgreSQL requires a paid plan.
> For a hackathon on Lite plan, use **ElephantSQL free tier** (external PostgreSQL):
>   - Go to [elephantsql.com](https://www.elephantsql.com/) → Sign up free
>   - Create instance → Select "Tiny Turtle" (free)
>   - Copy the connection URL (format: `postgresql://user:pass@host/db`)

Or use IBM Cloud Lite's built-in **Cloudant** (NoSQL) — but that requires code changes.

**Recommended for hackathon:** ElephantSQL free PostgreSQL.

### B4. IBM Cloud Object Storage (File Storage for Resumes)

```bash
# Already created during Step 9 setup.
# Verify your COS bucket exists:
# IBM Cloud Console → Cloud Object Storage → your-bucket → Overview
```

---

## Part C: Build and Push Docker Image

### C1. Build the Frontend First

The frontend must be built before the Docker image so it's included in the container.

```bash
# From the project root (interview-trainer/)
cd frontend
npm ci
npm run build
# Creates: frontend/dist/

# Copy built files into backend/static/
mkdir -p ../backend/static
cp -r dist/* ../backend/static/
cd ..
```

### C2. Build the Docker Image

```bash
cd backend

# Build the image
# Format: us.icr.io/<namespace>/<image-name>:<tag>
docker build -t us.icr.io/interview-trainer-ns/interview-trainer-api:latest .

# Verify the build
docker images | grep interview-trainer
```

**Expected output:**
```
us.icr.io/interview-trainer-ns/interview-trainer-api   latest   abc123   2 min ago   1.2GB
```

### C3. Test the Docker Image Locally

```bash
docker run -p 8000:8000 \
  -e ENV=production \
  -e SECRET_KEY=test-secret-key-32chars \
  -e DATABASE_URL=sqlite:///./test.db \
  us.icr.io/interview-trainer-ns/interview-trainer-api:latest

# Open in browser: http://localhost:8000/health
# Should return: {"status": "healthy", ...}
```

### C4. Push to IBM Container Registry

```bash
ibmcloud cr login
docker push us.icr.io/interview-trainer-ns/interview-trainer-api:latest

# Verify it's uploaded
ibmcloud cr image-list
```

---

## Part D: Configure Environment Variables

### D1. Generate a Secure Secret Key

```bash
# Run this once and save the output
python3 -c "import secrets; print(secrets.token_hex(32))"
# Example: a3f4c8e2b1d9... (64 char hex string)
```

### D2. Copy and Fill Production Env File

```bash
# From project root
cp env.production.example .env.production
# Edit .env.production with your real values:
notepad .env.production    # Windows
nano .env.production        # Mac/Linux
```

Required values:
| Variable | Where to Get It |
|---|---|
| `SECRET_KEY` | Generated in D1 above |
| `DATABASE_URL` | ElephantSQL → connection URL |
| `WATSONX_API_KEY` | IBM Cloud → IAM → API Keys |
| `WATSONX_PROJECT_ID` | watsonx.ai → Project → Manage → Details |
| `COS_API_KEY` | IBM COS → Service Credentials |
| `COS_INSTANCE_CRN` | IBM COS → Overview → CRN |

---

## Part E: Deploy to IBM Code Engine

### E1. Set Up Registry Access

Code Engine needs permission to pull your image from ICR.

```bash
# Create a registry secret
ibmcloud ce registry create \
  --name icr-secret \
  --server us.icr.io \
  --username iamapikey \
  --password $(ibmcloud iam api-key-create ce-key --output json | python3 -c "import sys,json; print(json.load(sys.stdin)['apikey'])")
```

### E2. Deploy the Application

```bash
ibmcloud ce project select --name interview-trainer-project

ibmcloud ce application create \
  --name interview-trainer-api \
  --image us.icr.io/interview-trainer-ns/interview-trainer-api:latest \
  --registry-secret icr-secret \
  --min-scale 1 \
  --max-scale 3 \
  --cpu 1 \
  --memory 4G \
  --port 8000 \
  --env ENV=production \
  --env SECRET_KEY="$(grep SECRET_KEY .env.production | cut -d= -f2)" \
  --env DATABASE_URL="$(grep DATABASE_URL .env.production | cut -d= -f2)" \
  --env WATSONX_API_KEY="$(grep WATSONX_API_KEY .env.production | cut -d= -f2)" \
  --env WATSONX_PROJECT_ID="$(grep WATSONX_PROJECT_ID .env.production | cut -d= -f2)" \
  --env COS_API_KEY="$(grep COS_API_KEY .env.production | cut -d= -f2)" \
  --env COS_INSTANCE_CRN="$(grep COS_INSTANCE_CRN .env.production | cut -d= -f2)"
```

### E3. Get Your Application URL

```bash
ibmcloud ce application get --name interview-trainer-api
# Look for "URL:" in the output
# Format: https://interview-trainer-api.<random>.us-south.codeengine.appdomain.cloud
```

### E4. Verify Deployment

```bash
# Replace <your-url> with the URL from E3
curl https://<your-url>/health
# Expected: {"status": "healthy", "app": "Interview Trainer Agent", ...}

curl https://<your-url>/docs
# Should show Swagger UI (open in browser)
```

---

## Part F: Run Database Migrations (PostgreSQL)

Once deployed, run Alembic migrations to create the tables:

```bash
# From backend/ directory
# With your production DATABASE_URL set:

export DATABASE_URL="postgresql://user:pass@host/db"
alembic upgrade head
# Output: Running upgrade  -> 001_initial, Initial schema — all tables
```

---

## Part G: GitHub Actions (Automatic CI/CD)

Every `git push` to `main` will automatically test, build, and deploy.

### G1. Add GitHub Secrets

Go to: **GitHub repo → Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

| Secret Name | Value |
|---|---|
| `IBM_CLOUD_API_KEY` | Your IBM Cloud API key |
| `IBM_CLOUD_REGION` | `us-south` |
| `IBM_ICR_NAMESPACE` | `interview-trainer-ns` |
| `IBM_CODE_ENGINE_PROJECT` | `interview-trainer-project` |
| `IBM_CODE_ENGINE_APP` | `interview-trainer-api` |
| `SECRET_KEY` | Your 64-char secret key |
| `DATABASE_URL` | Your PostgreSQL URL |
| `WATSONX_API_KEY` | Your IBM watsonx API key |
| `WATSONX_PROJECT_ID` | Your watsonx project ID |
| `COS_API_KEY` | Your IBM COS API key |
| `COS_INSTANCE_CRN` | Your COS instance CRN |

### G2. Test the Pipeline

```bash
git add .
git commit -m "deploy: Step 20 IBM Cloud deployment"
git push origin main
# Go to: GitHub repo → Actions → watch the pipeline run
```

---

## Part H: Update Frontend API URL

After deployment, update the frontend so it knows the production API URL (only if you host frontend separately):

```bash
# frontend/.env.production is already configured for single-container deployment
# No change needed — the React app is served by FastAPI at the same domain
```

---

## Troubleshooting

### "Container failed to start"
```bash
# Check container logs
ibmcloud ce application logs --name interview-trainer-api
# Common causes:
#   - Missing env variable (check all required vars are set)
#   - Database connection failed (check DATABASE_URL format)
#   - Port mismatch (make sure --port 8000 matches CMD in Dockerfile)
```

### "Health check failing"
```bash
# The app needs ~60s to cold start (ChromaDB population + model loading)
# Increase startup probe timeout:
ibmcloud ce application update \
  --name interview-trainer-api \
  --initial-delay-seconds 90
```

### "IBM Granite returning 401"
- Verify `WATSONX_API_KEY` is not expired (IBM API keys expire in 90 days by default)
- Verify `WATSONX_PROJECT_ID` is the correct project
- Verify WML service is associated with the watsonx.ai project

### "ChromaDB missing documents after restart"
- This is expected — ChromaDB is rebuilt from `datasets/` on every cold start
- The datasets are baked into the Docker image so they're always available
- Cold start takes ~30-60s; subsequent requests are fast

### "PDF reports not generating"
```bash
# Check reports/ directory permissions inside container
# The Dockerfile creates /app/reports — it should be writable
# Check logs for reportlab errors:
ibmcloud ce application logs --name interview-trainer-api | grep -i pdf
```

---

## Architecture Diagram (Production)

```
Internet
   │
   ▼
IBM Cloud Code Engine
┌─────────────────────────────────────────────┐
│  Docker Container (1 vCPU, 4GB RAM)         │
│                                             │
│  Uvicorn (ASGI server, port 8000)           │
│  └── FastAPI Application                   │
│       ├── /auth/*        → JWT auth        │
│       ├── /resume/*      → Resume upload   │
│       ├── /interview/*   → Mock interview  │
│       ├── /report/*      → PDF reports     │
│       ├── /static/*      → React frontend  │
│       └── /*             → React SPA       │
│                                             │
│  ChromaDB (in-memory + /app/chroma_db/)    │
│  SQLite (dev) / PostgreSQL (prod)           │
│  IBM Granite (via watsonx.ai API)           │
│  IBM COS (resume file storage)              │
└─────────────────────────────────────────────┘
   │                    │
   ▼                    ▼
ElephantSQL         IBM watsonx.ai
(PostgreSQL)        (Granite LLM)
```

---

## Cost Estimate (IBM Cloud Lite Plan)

| Service | Plan | Cost |
|---|---|---|
| IBM Code Engine | Lite | Free (50 vCPU-h/month) |
| IBM Container Registry | Lite | Free (500MB storage) |
| IBM Cloud Object Storage | Lite | Free (25GB) |
| IBM watsonx.ai | Lite | Free (limited tokens) |
| ElephantSQL PostgreSQL | Tiny Turtle | Free (20MB) |
| **Total** | | **$0/month** |

> For a hackathon or demo, this is completely free.
> For production scale (>100 users), upgrade to Pay-As-You-Go.
