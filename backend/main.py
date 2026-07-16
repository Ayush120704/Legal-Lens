import asyncio
import io
import json
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import state_store
from services.agent import analyze_document

app = FastAPI(
    title="AI-Driven Legal Document Analyzer",
    description="Enterprise-grade legal document risk analysis with AI-powered clause scoring",
    version="1.0.0",
)

# CORS configuration for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- WebSocket Connection Manager ---
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
            self.active_connections[job_id] = [
                ws for ws in self.active_connections[job_id] if ws != websocket
            ]
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


# --- Request Models ---
class UploadRequest(BaseModel):
    text: str


# --- Startup Event: Preload ML models ---
@app.on_event("startup")
async def startup_event():
    """Preload the sentence-transformers model and ChromaDB on startup."""
    from services.agent import _get_scoring_engine, _get_vector_store
    _get_scoring_engine()
    _get_vector_store()
    print("Models and vector store loaded successfully.")


# --- Health Check ---
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "legallens", "version": "1.0.0"}


# --- Upload Endpoint ---
@app.post("/api/session/upload")
async def upload_document(request: UploadRequest, background_tasks: BackgroundTasks):
    """Submit a legal document for asynchronous analysis."""
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Document text cannot be empty")

    job_id = state_store.create_job()
    background_tasks.add_task(analyze_document, job_id, request.text.strip())
    return {"job_id": job_id, "message": "Analysis started."}


# --- File Upload Endpoint (PDF / TXT) ---
@app.post("/api/session/upload-file")
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """Upload a PDF or TXT file for analysis. Text is extracted server-side."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    filename_lower = file.filename.lower()
    is_pdf = filename_lower.endswith(".pdf")
    is_txt = filename_lower.endswith(".txt") or filename_lower.endswith(".md")

    if not is_pdf and not is_txt:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a .pdf, .txt, or .md file.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="File is empty")

    text = ""

    if is_pdf:
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(contents)) as pdf:
                pages = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages.append(page_text)
                text = "\n\n".join(pages)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    else:
        try:
            text = contents.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = contents.decode("latin-1")
            except Exception:
                raise HTTPException(status_code=400, detail="Could not decode file. Ensure it is UTF-8 or Latin-1 encoded.")

    if not text.strip():
        raise HTTPException(status_code=400, detail="No extractable text found in the document.")

    job_id = state_store.create_job()
    background_tasks.add_task(analyze_document, job_id, text.strip())
    return {"job_id": job_id, "message": f"Analysis started for {file.filename}."}


# --- Status Endpoint ---
@app.get("/api/session/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the current status and results of an analysis job."""
    job = state_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


# --- WebSocket Endpoint ---
@app.websocket("/ws/analysis/{job_id}")
async def websocket_analysis(websocket: WebSocket, job_id: str):
    """Real-time progress updates via WebSocket."""
    await manager.connect(job_id, websocket)
    try:
        last_progress = -1
        while True:
            # Check for client messages (ping/pong keepalive)
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                if msg == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass

            # Send progress update if changed
            job = state_store.get_job(job_id)
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
                await websocket.send_json({
                    "type": "complete",
                    "status": job["status"],
                    "data": job,
                })
                break

            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
    except Exception:
        manager.disconnect(job_id, websocket)


# --- Entry point ---
if __name__ == "__main__":
    import uvicorn
    import os
    import socket

    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    port_env = os.environ.get("BACKEND_PORT")
    ports_to_try = [int(port_env)] if port_env else [8000, 8001, 8002, 8003, 8004]

    def _port_is_available(h, p):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Try to bind briefly to check availability
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
        print(f"Could not bind to any of the ports: {ports_to_try}.\n" \
              "Possible causes: another process holds the port, OS reserved the port range, or insufficient permissions.\n" \
              "You can try setting BACKEND_PORT to a free port or run the process as Administrator.")
        raise SystemExit(1)

    print(f"Starting server on http://{host}:{chosen_port} (use BACKEND_HOST/BACKEND_PORT to override)")
    uvicorn.run(app, host=host, port=chosen_port)
