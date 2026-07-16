# AI-Driven Legal Document Analyzer

An enterprise-grade portfolio project demonstrating an AI agent architecture that ingests text-based contracts, processes them asynchronously, flags high-risk clauses using a custom mathematical evaluation engine, matches them against indexed compliance guidelines, and displays results in an interactive side-by-side dashboard.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Upload   │  │  Risk        │  │  Diff Viewer     │  │
│  │  Panel    │  │  Dashboard   │  │  (Side-by-Side)  │  │
│  └─────┬────┘  └──────┬───────┘  └────────┬─────────┘  │
│        │              │                    │             │
│  ┌─────┴──────────────┴────────────────────┴──────────┐  │
│  │              api.js (Fetch + Polling)              │  │
│  └─────────────────────┬──────────────────────────────┘  │
│                        │                                 │
│  ┌─────────────────────┴──────────────────────────────┐  │
│  │        VectorBackground3D (Three.js Canvas)        │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────┘
                               │ HTTP (Port 3000 -> 8000)
┌──────────────────────────────┴──────────────────────────┐
│                    FastAPI Backend                        │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │   POST       │  │   GET        │  │   WebSocket    │  │
│  │   /upload    │  │   /status    │  │   /ws/analysis │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘  │
│         │                │                   │           │
│  ┌──────┴────────────────┴───────────────────┴────────┐  │
│  │           agent.py (Background Worker)             │  │
│  │    Split → Score → Match → Aggregate → Store       │  │
│  └──┬──────────┬──────────────────┬───────────────────┘  │
│     │          │                  │                      │
│  ┌──┴───┐  ┌───┴──────┐  ┌───────┴────────────────┐    │
│  │score │  │ vector   │  │     database.py        │    │
│  │.py   │  │ _store   │  │  (In-Memory State)     │    │
│  │(60/40│  │ .py      │  │                        │    │
│  │ math)│  │(ChromaDB)│  │  Job status, progress, │    │
│  └──────┘  └──────────┘  │  clauses, aggregates   │    │
│                           └────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Core Features

- **Custom Risk Scoring Engine**: Deterministic 60/40 weighted formula — `Risk Score = (0.6 * Cosine Similarity) + (0.4 * Keyword Penalties)` — using sentence-transformers (`all-MiniLM-L6-v2`) and numpy dot products
- **Asynchronous Processing**: FastAPI `BackgroundTasks` with real-time WebSocket progress updates and HTTP polling fallback
- **Compliance Matching**: ChromaDB vector store pre-seeded with GDPR, CCPA, HIPAA, SOX, and ISO 27001 regulatory guidelines
- **Interactive 3D Visualization**: Three.js particle network background representing vector-space connections
- **Side-by-Side Diff Viewer**: Dynamic red-lining of original clauses against AI-generated suggestions with quality assessments
- **Risk Dashboard**: Aggregate metrics, health score, risk distribution, key findings, and missing protections

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm 9+

### Backend Setup

```bash
cd legal-analyzer-app/backend

# Create virtual environment (if not already created)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies (first run downloads ~800MB for torch + sentence-transformers)
pip install -r requirements.txt

# Start the server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The backend will be available at `http://localhost:8000`.

### Frontend Setup

```bash
cd legal-analyzer-app/frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/session/upload` | Submit a legal document for analysis |
| `GET` | `/api/session/status/{job_id}` | Get analysis status and results |
| `WS` | `/ws/analysis/{job_id}` | WebSocket for real-time progress |

### Upload Request

```json
{
  "text": "Section 1. Automatic Renewal. This Agreement shall automatically renew..."
}
```

### Status Response

```json
{
  "job_id": "uuid",
  "status": "completed",
  "progress": 100,
  "clauses": [...],
  "risk_summary": { "high_risk_count": 1, "medium_risk_count": 2, "low_risk_count": 1 },
  "document_summary": { "health_score": 65.0, "overall_health": "moderate", "verdict": "..." }
}
```

---

## Data Synchronization Mechanics

1. **Upload**: Client POSTs document text → backend creates a job ID, stores it in `database.py` (thread-safe in-memory dict), and spawns a `BackgroundTask`
2. **Background Processing**: The agent splits text into clauses, scores each clause sequentially, queries ChromaDB for compliance matches, and broadcasts progress via WebSocket
3. **Real-Time Updates**: WebSocket pushes `{ type: "progress", ... }` messages to connected clients on each clause completion
4. **Polling Fallback**: Frontend falls back to 1-second HTTP polling if WebSocket is unavailable
5. **Completion**: Final state includes all analyzed clauses, aggregate risk summary, document health score, and key findings

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Three.js, Tailwind CSS, Vite |
| Backend | Python 3.11, FastAPI, Uvicorn |
| ML/AI | sentence-transformers, scikit-learn, numpy |
| Vector DB | ChromaDB |
| Real-Time | WebSocket (native FastAPI) |
| PDF Parsing | pdfplumber |

---

## Deployment (Railway)

### Prerequisites
- A [Railway](https://railway.app) account
- This GitHub repository

### Steps

1. **Push to GitHub** (if not already done):
   ```bash
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Create a Railway project**:
   - Go to [railway.app](https://railway.app) → New Project → **Deploy from GitHub Repo**
   - Select this repository

3. **Add Backend Service**:
   - Railway will auto-detect the `backend/Dockerfile`
   - Set the root directory to `backend` in the service settings
   - The backend will build with all ML dependencies (may take 5-10 min on first deploy)

4. **Add Frontend Service**:
   - Add a second service → **Deploy from GitHub Repo** (same repo)
   - Set the root directory to `frontend`
   - Railway will build using `frontend/Dockerfile`

5. **Set Environment Variable**:
   - On the **frontend** service, add environment variable:
     ```
     VITE_API_URL=<your-backend-railway-url>
     ```
   - The backend URL looks like: `https://backend-xxxx.up.railway.app`

6. **Done!** Your frontend will be live at `https://frontend-xxxx.up.railway.app`

### Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`

---

## License

MIT
