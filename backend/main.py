import asyncio
import io
import json
import os
import time
import csv
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, UploadFile, File, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import state_store as memory_store
from services.agent import analyze_document
from config import settings
from models import init_db, get_db, User, Document, Clause, ChatMessage
from auth import hash_password, verify_password, create_access_token, get_current_user, get_optional_user

app = FastAPI(
    title="AI-Driven Legal Document Analyzer",
    description="Enterprise-grade legal document risk analysis with AI-powered clause scoring, LLM integration, authentication, and export",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    return response

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)

    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.active_connections:
            self.active_connections[job_id] = [ws for ws in self.active_connections[job_id] if ws != websocket]
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    async def broadcast(self, job_id: str, message: dict):
        if job_id not in self.active_connections:
            return
        dead = []
        for ws in self.active_connections[job_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(job_id, ws)

manager = ConnectionManager()

# --- Request/Response Models ---
class UploadRequest(BaseModel):
    text: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    display_name: str

class ChatRequest(BaseModel):
    question: str
    document_id: int

class CompareRequest(BaseModel):
    document_id_a: int
    document_id_b: int

class BatchUploadRequest(BaseModel):
    documents: List[str]

class UserUpdateRequest(BaseModel):
    display_name: Optional[str] = None

# --- Input Sanitization ---
_MAX_TEXT_LENGTH = settings.MAX_TEXT_LENGTH

def sanitize_text(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if len(text) > _MAX_TEXT_LENGTH:
        text = text[:_MAX_TEXT_LENGTH]
    text = text.replace("\x00", "")
    return text

# --- Rate Limiting ---
_rate_limit_store: dict = {}
_last_rate_cleanup: float = time.time()

def _check_rate_limit(client_id: str, max_requests: int = settings.RATE_LIMIT_PER_MINUTE, window: int = 60) -> bool:
    global _last_rate_cleanup
    now = time.time()
    if now - _last_rate_cleanup > 300:
        cutoff = now - 120
        expired = [k for k, v in _rate_limit_store.items() if v and max(v) < cutoff]
        for k in expired:
            del _rate_limit_store[k]
        _last_rate_cleanup = now
    if client_id not in _rate_limit_store:
        _rate_limit_store[client_id] = []
    _rate_limit_store[client_id] = [t for t in _rate_limit_store[client_id] if now - t < window]
    if len(_rate_limit_store[client_id]) >= max_requests:
        return False
    _rate_limit_store[client_id].append(now)
    return True

# --- Startup ---
@app.on_event("startup")
async def startup_event():
    init_db()
    from services.agent import _get_scoring_engine, _get_vector_store
    try:
        _get_scoring_engine()
        print("Scoring engine initialized.")
    except Exception as e:
        print(f"Scoring engine init warning (fallback will activate at runtime): {e}")
    try:
        _get_vector_store()
        print("Vector store initialized.")
    except Exception as e:
        print(f"Vector store init warning: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    from models import engine
    engine.dispose()

# --- Health ---
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "legallens", "version": "2.0.0"}

# ==================== AUTH ROUTES ====================

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=req.email, hashed_password=hash_password(req.password), display_name=req.display_name or req.email.split("@")[0])
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id, email=user.email, display_name=user.display_name)

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    token = create_access_token({"sub": str(user.id)})
    return TokenResponse(access_token=token, user_id=user.id, email=user.email, display_name=user.display_name)

@app.get("/api/auth/me")
async def get_profile(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "created_at": user.created_at.isoformat()}

@app.put("/api/auth/me")
async def update_profile(req: UserUpdateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.display_name is not None:
        user.display_name = req.display_name
    db.commit()
    return {"id": user.id, "email": user.email, "display_name": user.display_name}

# ==================== DOCUMENT ROUTES ====================

@app.post("/api/session/upload")
async def upload_document(
    request: UploadRequest,
    background_tasks: BackgroundTasks,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty")
    if len(request.text) > _MAX_TEXT_LENGTH:
        raise HTTPException(status_code=413, detail=f"Document text exceeds {_MAX_TEXT_LENGTH} character limit")
    text = sanitize_text(request.text)
    client_ip = "anonymous"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    job_id = memory_store.create_job()
    doc = Document(job_id=job_id, user_id=user.id if user else None, original_text=text, title="Pasted Document")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    memory_store.update_job(job_id, user_id=user.id if user else None)
    background_tasks.add_task(analyze_document, job_id, text, doc.id)
    return {"job_id": job_id, "document_id": doc.id, "message": "Analysis started."}

@app.post("/api/session/upload-file")
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    filename_lower = file.filename.lower()
    is_pdf = filename_lower.endswith(".pdf")
    is_txt = filename_lower.endswith(".txt") or filename_lower.endswith(".md")
    if not is_pdf and not is_txt:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload .pdf, .txt, or .md")
    contents = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")
    if not contents:
        raise HTTPException(status_code=400, detail="File is empty")
    text = ""
    if is_pdf:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(contents)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
                text = "\n\n".join([p for p in pages if p.strip()])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    else:
        try:
            text = contents.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = contents.decode("latin-1")
            except Exception:
                raise HTTPException(status_code=400, detail="Could not decode file")
    if not text.strip():
        raise HTTPException(status_code=400, detail="No extractable text found")
    if len(text) > _MAX_TEXT_LENGTH:
        raise HTTPException(status_code=413, detail=f"Document text exceeds {_MAX_TEXT_LENGTH} character limit")
    text = sanitize_text(text)
    job_id = memory_store.create_job()
    doc = Document(job_id=job_id, user_id=user.id if user else None, original_text=text, title=file.filename)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    memory_store.update_job(job_id, user_id=user.id if user else None)
    background_tasks.add_task(analyze_document, job_id, text, doc.id)
    return {"job_id": job_id, "document_id": doc.id, "message": f"Analysis started for {file.filename}."}

@app.get("/api/session/status/{job_id}")
async def get_job_status(job_id: str, user: Optional[User] = Depends(get_optional_user)):
    job = memory_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job_owner = job.get("user_id")
    if job_owner is not None:
        if not user or user.id != job_owner:
            raise HTTPException(status_code=403, detail="Access denied")
    return job

@app.get("/api/documents")
async def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.user_id == user.id).order_by(Document.created_at.desc()).limit(50).all()
    return [{
        "id": d.id,
        "job_id": d.job_id,
        "title": d.title,
        "status": d.status,
        "progress": d.progress,
        "total_clauses": d.total_clauses,
        "health_score": d.document_summary.get("health_score") if d.document_summary else None,
        "overall_health": d.document_summary.get("overall_health") if d.document_summary else None,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    } for d in docs]

@app.get("/api/documents/{document_id}")
async def get_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    clauses = db.query(Clause).filter(Clause.document_id == doc.id).order_by(Clause.clause_index).all()
    return {
        "id": doc.id,
        "job_id": doc.job_id,
        "title": doc.title,
        "status": doc.status,
        "progress": doc.progress,
        "total_clauses": doc.total_clauses,
        "processed_clauses": doc.processed_clauses,
        "risk_summary": doc.risk_summary,
        "document_summary": doc.document_summary,
        "clauses": [{
            "id": c.id,
            "clause_index": c.clause_index,
            "original_text": c.original_text,
            "suggested_text": c.suggested_text,
            "risk_score": c.risk_score,
            "risk_level": c.risk_level,
            "category": c.category,
            "flags": c.flags,
            "suggestions": c.suggestions,
            "pros": c.pros,
            "cons": c.cons,
            "quality": c.quality,
            "compliance_matches": c.compliance_matches,
            "llm_analysis": c.llm_analysis,
        } for c in clauses],
        "created_at": doc.created_at.isoformat(),
        "updated_at": doc.updated_at.isoformat(),
    }

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
    return {"message": "Document deleted"}

# ==================== EXPORT ROUTES ====================

@app.get("/api/documents/{document_id}/export/csv")
async def export_document_csv(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from export_service import generate_csv_report
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    clauses = db.query(Clause).filter(Clause.document_id == doc.id).order_by(Clause.clause_index).all()
    clause_dicts = [{
        "original_text": c.original_text, "suggested_text": c.suggested_text or "",
        "risk_score": c.risk_score, "risk_level": c.risk_level, "category": c.category,
        "flags": c.flags, "suggestions": c.suggestions, "pros": c.pros, "cons": c.cons,
        "quality": c.quality, "compliance_matches": c.compliance_matches,
    } for c in clauses]
    csv_content = generate_csv_report(clause_dicts, doc.risk_summary or {}, doc.document_summary or {})
    from fastapi.responses import StreamingResponse
    return StreamingResponse(io.StringIO(csv_content), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=legallens_report_{doc.id}.csv"})

@app.get("/api/documents/{document_id}/export/txt")
async def export_document_txt(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from export_service import generate_txt_report
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    clauses = db.query(Clause).filter(Clause.document_id == doc.id).order_by(Clause.clause_index).all()
    clause_dicts = [{
        "original_text": c.original_text, "suggested_text": c.suggested_text or "",
        "risk_score": c.risk_score, "risk_level": c.risk_level, "category": c.category,
        "flags": c.flags, "suggestions": c.suggestions,
    } for c in clauses]
    txt_content = generate_txt_report(clause_dicts, doc.risk_summary or {}, doc.document_summary or {})
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=txt_content, headers={"Content-Disposition": f"attachment; filename=legallens_report_{doc.id}.txt"})

# ==================== CHAT ROUTES ====================

@app.post("/api/documents/{document_id}/chat")
async def chat_with_document(document_id: int, req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from llm_service import llm_service
    from local_chat import answer_question_locally
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    clauses = db.query(Clause).filter(Clause.document_id == doc.id).order_by(Clause.clause_index).all()
    clause_dicts = [{
        "original_text": c.original_text,
        "risk_score": c.risk_score,
        "risk_level": c.risk_level,
        "category": c.category,
        "flags": c.flags or [],
        "suggestions": c.suggestions or [],
        "pros": c.pros or [],
        "cons": c.cons or [],
        "compliance_matches": c.compliance_matches or [],
    } for c in clauses]
    answer = None
    if llm_service.available:
        clauses_text = "\n\n".join([f"Clause {c.clause_index} [{c.risk_level.upper()}]: {c.original_text[:500]}" for c in clauses])
        answer = llm_service.answer_question(doc.original_text[:8000], clauses_text[:4000], req.question)
    if not answer:
        answer = answer_question_locally(
            doc.original_text or "",
            clause_dicts,
            doc.document_summary or {},
            req.question
        )
    user_msg = ChatMessage(document_id=doc.id, role="user", content=req.question)
    assistant_msg = ChatMessage(document_id=doc.id, role="assistant", content=answer)
    db.add_all([user_msg, assistant_msg])
    db.commit()
    return {"question": req.question, "answer": answer, "message_id": assistant_msg.id}

@app.get("/api/documents/{document_id}/chat/history")
async def get_chat_history(document_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    messages = db.query(ChatMessage).filter(ChatMessage.document_id == doc.id).order_by(ChatMessage.created_at).all()
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages]

# ==================== COMPARISON ROUTES ====================

@app.post("/api/documents/compare")
async def compare_documents(req: CompareRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from llm_service import llm_service
    doc_a = db.query(Document).filter(Document.id == req.document_id_a, Document.user_id == user.id).first()
    doc_b = db.query(Document).filter(Document.id == req.document_id_b, Document.user_id == user.id).first()
    if not doc_a or not doc_b:
        raise HTTPException(status_code=404, detail="One or both documents not found")
    clauses_a = db.query(Clause).filter(Clause.document_id == doc_a.id).order_by(Clause.clause_index).all()
    clauses_b = db.query(Clause).filter(Clause.document_id == doc_b.id).order_by(Clause.clause_index).all()
    comparison = []
    max_len = max(len(clauses_a), len(clauses_b))
    for i in range(max_len):
        ca = clauses_a[i] if i < len(clauses_a) else None
        cb = clauses_b[i] if i < len(clauses_b) else None
        llm_diff = None
        if ca and cb and llm_service.available:
            llm_diff = llm_service.compare_clauses(ca.original_text[:1000], cb.original_text[:1000])
        comparison.append({
            "index": i + 1,
            "doc_a": {"text": ca.original_text if ca else None, "risk_level": ca.risk_level if ca else None, "risk_score": ca.risk_score if ca else None, "category": ca.category if ca else None},
            "doc_b": {"text": cb.original_text if cb else None, "risk_level": cb.risk_level if cb else None, "risk_score": cb.risk_score if cb else None, "category": cb.category if cb else None},
            "risk_delta": (cb.risk_score - ca.risk_score) if ca and cb else None,
            "llm_comparison": llm_diff,
        })
    from export_service import generate_clause_comparison_csv
    return {
        "doc_a": {"id": doc_a.id, "title": doc_a.title, "health_score": doc_a.document_summary.get("health_score") if doc_a.document_summary else None},
        "doc_b": {"id": doc_b.id, "title": doc_b.title, "health_score": doc_b.document_summary.get("health_score") if doc_b.document_summary else None},
        "comparison": comparison,
    }

# ==================== BATCH ANALYSIS ====================

@app.post("/api/session/batch-upload")
async def batch_upload(req: BatchUploadRequest, background_tasks: BackgroundTasks, user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    if len(req.documents) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 documents per batch")
    results = []
    for i, text in enumerate(req.documents):
        if not text.strip():
            continue
        job_id = memory_store.create_job()
        doc = Document(job_id=job_id, user_id=user.id if user else None, original_text=text.strip(), title=f"Batch Document {i + 1}")
        db.add(doc)
        db.flush()
        background_tasks.add_task(analyze_document, job_id, text.strip(), doc.id)
        results.append({"job_id": job_id, "document_id": doc.id, "title": f"Batch Document {i + 1}"})
    db.commit()
    return {"message": f"Started analysis for {len(results)} documents", "documents": results}

# ==================== WEBSOCKET ====================

@app.websocket("/ws/analysis/{job_id}")
async def websocket_analysis(websocket: WebSocket, job_id: str):
    await manager.connect(job_id, websocket)
    try:
        last_progress = -1
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if msg == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass
            job = memory_store.get_job(job_id)
            if job is None:
                await websocket.send_json({"type": "error", "message": "Job not found"})
                break
            current_progress = job["progress"]
            if current_progress != last_progress:
                await websocket.send_json({
                    "type": "progress",
                    "progress": current_progress,
                    "status": job["status"],
                    "processed_clauses": job["processed_clauses"],
                    "total_clauses": job["total_clauses"],
                })
                last_progress = current_progress
            if job["status"] in ("completed", "error"):
                await websocket.send_json({"type": "complete", "status": job["status"], "data": job})
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
    except Exception:
        manager.disconnect(job_id, websocket)

# ==================== JOB CLEANUP ====================

@app.post("/api/admin/cleanup")
async def cleanup_old_jobs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(hours=settings.JOB_CLEANUP_HOURS)
    old_docs = db.query(Document).filter(Document.user_id == user.id, Document.created_at < cutoff).all()
    count = len(old_docs)
    for doc in old_docs:
        db.delete(doc)
    db.commit()
    return {"message": f"Cleaned up {count} expired documents"}

# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    import uvicorn
    import socket
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    port_env = os.environ.get("BACKEND_PORT")
    ports_to_try = [int(port_env)] if port_env else [8000, 8001, 8002, 8003, 8004]

    def _port_is_available(h, p):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind((h, p))
            s.close()
            return True
        except Exception:
            try:
                s.close()
            except Exception:
                pass
            return False

    chosen_port = None
    for p in ports_to_try:
        if _port_is_available(host, p):
            chosen_port = p
            break
        else:
            print(f"Port {p} not available on {host}, trying next...")

    if chosen_port is None:
        print(f"Could not bind to any of the ports: {ports_to_try}.")
        raise SystemExit(1)

    print(f"Starting server on http://{host}:{chosen_port}")
    uvicorn.run(app, host=host, port=chosen_port)
