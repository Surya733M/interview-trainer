# Interview Trainer Agent 🤖

> AI-powered mock interview trainer using **IBM Granite** + **Retrieval-Augmented Generation (RAG)**

[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-green)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev)
[![IBM watsonx](https://img.shields.io/badge/IBM-watsonx.ai-red)](https://www.ibm.com/watsonx)

---

## What Is This?

Upload your resume. Enter your target job role. The agent:

1. **Parses** your resume and extracts skills, experience, and projects
2. **Searches** a curated vector knowledge base of 1000+ interview Q&As (RAG)
3. **Generates** personalised technical, behavioral, and HR questions via IBM Granite
4. **Conducts** a real mock interview — one question at a time
5. **Evaluates** every answer for correctness, grammar, STAR method, and confidence
6. **Reports** your scores across 5 dimensions with a recommended learning path

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | Python, FastAPI, Uvicorn |
| AI Model | IBM Granite 13B (watsonx.ai) |
| Embeddings | IBM Slate / sentence-transformers |
| Vector DB | ChromaDB → IBM watsonx.data |
| Resume Parsing | PyMuPDF |
| Database | SQLite (dev) → PostgreSQL (prod) |
| Storage | IBM Cloud Object Storage |
| Deployment | IBM Cloud Code Engine |

---

## Project Structure

```
interview-trainer/
├── backend/          # FastAPI Python API
│   ├── app/
│   │   ├── routes/   # HTTP endpoints
│   │   ├── services/ # Business logic
│   │   ├── models/   # Database ORM models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── rag/      # RAG pipeline
│   │   ├── prompts/  # Granite prompt templates
│   │   └── utils/    # Shared helpers
│   └── datasets/     # Interview knowledge base
└── frontend/         # React + Vite app
    └── src/
        ├── pages/    # Full page views
        ├── components/ # Reusable UI
        └── services/ # API call wrappers
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- IBM Cloud account (free Lite tier)
- watsonx.ai project

### Backend Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Copy and fill in your credentials
cp env.example .env

python run.py
# API running at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
# App running at http://localhost:5173
```

---

## Environment Variables

Copy `backend/env.example` to `backend/.env` and fill in:

| Variable | Description |
|---|---|
| `WATSONX_API_KEY` | IBM Cloud API Key |
| `WATSONX_PROJECT_ID` | watsonx.ai Project ID |
| `SECRET_KEY` | JWT signing secret (random 64-char string) |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| POST | `/resume/upload` | Upload PDF resume |
| GET  | `/resume/analyze` | Extract skills |
| POST | `/interview/start` | Start mock interview |
| POST | `/interview/answer` | Submit answer + get feedback |
| GET  | `/report/{id}` | Get final report |
| GET  | `/report/{id}/pdf` | Download PDF report |

---

## License

MIT — built for IBM Hackathon 2024
