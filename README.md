# LegalLens — AI-Driven Legal Document Analyzer

An enterprise-grade legal document risk analysis platform with AI-powered clause scoring, LLM-enhanced reasoning, persistent storage, user authentication, real-time chat, document comparison, and multi-format export.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          React Frontend (Vite)                           │
│  ┌──────────┐  ┌──────────────┐  ┌───────────┐  ┌───────┐  ┌────────┐ │
│  │  Upload   │  │    Risk      │  │    Chat    │  │History│  │Compare │ │
│  │  Panel    │  │  Dashboard   │  │   Panel    │  │       │  │Panel   │ │
│  └─────┬────┘  └──────┬───────┘  └─────┬─────┘  └───┬───┘  └───┬────┘ │
│        └──────────────┴────────────────┴────────────┴──────────┘       │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │         api.js (Auth, REST, WebSocket, Polling)                 │   │
│  └─────────────────────────────┬────────────────────────────────────┘   │
│                                │ HTTP/WS                                │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────────────┐
│                     FastAPI Backend (Python)                             │
│                                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────┐  │
│  │  Auth     │ │ Document │ │   Chat   │ │ Compare │ │   Export     │  │
│  │  /auth/*  │ │  /docs/* │ │ /chat/*  │ │/compare │ │  /export/*   │  │
│  └─────┬────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ └──────┬───────┘  │
│        └───────────┴────────────┴────────────┴──────────────┘          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              agent.py (Background Analysis Worker)                │   │
│  │         Split → Score → LLM Enhance → Match → Aggregate         │   │
│  └──┬──────────┬──────────────────┬──────────────────────┬─────────┘   │
│     │          │                  │                      │             │
│  ┌──┴───┐  ┌───┴──────┐  ┌───────┴────────┐  ┌─────────┴─────────┐  │
│  │score │  │ vector   │  │  llm_service   │  │  database.py +    │  │
│  │.py   │  │ _store   │  │  (OpenAI GPT)  │  │  models.py        │  │
│  │(60/40│  │ .py      │  │  Chat/Enhance/ │  │  (SQLite/SQLAlch.)│  │
│  │ math)│  │(ChromaDB)│  │  Compare       │  │  + In-Memory      │  │
│  └──────┘  └──────────┘  └───────────────┘  └────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Analysis Engine
- **Custom Risk Scoring**: 60/40 weighted formula — `(0.6 × Cosine Similarity to high-risk corpus) + (0.4 × Keyword Penalties)` using sentence-transformers (`all-MiniLM-L6-v2`)
- **Clause Categorization**: Auto-detects 10 legal categories (termination, liability, data privacy, IP, warranty, etc.)
- **Quality Assessment**: Clarity, balance, and enforceability scores per clause
- **Compliance Matching**: Vector search against 40+ regulatory guidelines (GDPR, CCPA, HIPAA, SOX, ISO 27001, LGPD, PIPEDA, VCDPA, UCC, and more)
- **Suggested Improvements**: AI-generated safer alternative text for high-risk clauses

### LLM Integration (OpenAI)
- **Enhanced Clause Analysis**: GPT-powered legal reasoning, negotiation tips, jurisdiction notes, and risk details
- **Executive Summaries**: AI-generated document-level summaries with key risks and recommendations
- **Document Q&A Chat**: Ask natural language questions about any analyzed document
- **Document Comparison**: LLM-powered clause-by-clause comparison between two documents

### User System & Persistence
- **JWT Authentication**: Register/login with secure token-based auth
- **Persistent Database**: SQLite/SQLAlchemy stores all analyses, users, chat history
- **Document History**: Browse, search, and reload past analyses
- **Job Cleanup**: Automatic cleanup of expired documents

### Collaboration & Export
- **Document Comparison**: Side-by-side risk comparison of any two analyzed documents
- **Batch Analysis**: Upload and analyze up to 10 documents at once
- **CSV Export**: Download clause-level analysis as CSV
- **TXT Report**: Download formatted text report with full analysis

### Real-Time & UX
- **WebSocket Progress**: Real-time analysis progress with polling fallback
- **Interactive Dashboard**: Health score ring, risk distribution, critical issues
- **Side-by-Side Diff Viewer**: Original vs suggested clause comparison with quality bars
- **3D Background**: Three.js interactive particle network visualization
- **Dark Theme**: Glass morphism UI with Tailwind CSS

### Security & Operations
- **Rate Limiting**: Per-client rate limiting on upload endpoints
- **File Size Enforcement**: Configurable max upload size (default 50MB)
- **Graceful Error Handling**: Comprehensive error states and user feedback
- **Dockerized**: Ready for Railway/Render deployment with Docker
- **CI/CD**: GitHub Actions for testing and build verification

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Three.js, Tailwind CSS, Vite |
| Backend | Python 3.11, FastAPI, Uvicorn |
| AI/ML | sentence-transformers, OpenAI API, numpy |
| Vector DB | ChromaDB (40+ compliance guidelines) |
| Database | SQLAlchemy + SQLite |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Real-Time | WebSocket (native FastAPI) |
| PDF Parsing | pdfplumber |
| Testing | pytest, pytest-asyncio, httpx |
| CI/CD | GitHub Actions |
| Deployment | Docker, Railway, Render |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key (optional, for LLM features)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Configure your settings
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register a new user |
| `POST` | `/api/auth/login` | Login and receive JWT |
| `GET` | `/api/auth/me` | Get current user profile |
| `PUT` | `/api/auth/me` | Update user profile |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/session/upload` | Submit document text for analysis |
| `POST` | `/api/session/upload-file` | Upload PDF/TXT file for analysis |
| `POST` | `/api/session/batch-upload` | Batch analyze up to 10 documents |
| `GET` | `/api/session/status/{job_id}` | Get analysis status |
| `GET` | `/api/documents` | List user's documents |
| `GET` | `/api/documents/{id}` | Get full document analysis |
| `DELETE` | `/api/documents/{id}` | Delete a document |

### Chat & AI
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents/{id}/chat` | Ask a question about a document |
| `GET` | `/api/documents/{id}/chat/history` | Get chat history |

### Comparison & Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/documents/compare` | Compare two documents |
| `GET` | `/api/documents/{id}/export/csv` | Download CSV report |
| `GET` | `/api/documents/{id}/export/txt` | Download TXT report |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/admin/cleanup` | Clean up expired documents |
| `WS` | `/ws/analysis/{job_id}` | Real-time analysis progress |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite:///./legal_analyzer.db` | Database connection string |
| `SECRET_KEY` | **Yes** | — | JWT signing key (change in production) |
| `OPENAI_API_KEY` | No | — | OpenAI API key (enables LLM features) |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model to use |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | Max upload requests per minute |
| `MAX_UPLOAD_SIZE_MB` | No | `50` | Max file upload size in MB |
| `JOB_CLEANUP_HOURS` | No | `24` | Auto-delete documents older than N hours |
| `BACKEND_HOST` | No | `127.0.0.1` | Backend bind address |
| `BACKEND_PORT` | No | `8000` | Backend bind port |

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

---

## Deployment

### Railway / Render

1. Push to GitHub:
   ```bash
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. Deploy the **backend** service using `backend/Dockerfile`
3. Deploy the **frontend** service using `frontend/Dockerfile`
4. Set `VITE_API_URL` on the frontend service to your backend URL
5. Set `SECRET_KEY` and optionally `OPENAI_API_KEY` on the backend service

### Docker Compose

```yaml
version: "3.8"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=your-secret-key
      - OPENAI_API_KEY=your-openai-key
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://localhost:8000
```

---

## License

MIT
