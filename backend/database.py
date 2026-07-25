import threading
import time
from uuid import uuid4
from typing import Any, Dict, Optional, List


class InMemoryStateStore:
    """Thread-safe in-memory state store for managing analysis job lifecycle.
    Automatically reclaims memory by removing finished jobs after a timeout.
    """

    MEMORY_CLEANUP_AGE = 60

    def __init__(self):
        self._lock = threading.Lock()
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._job_timestamps: Dict[str, float] = {}

    def create_job(self, job_id: Optional[str] = None) -> str:
        """Create a new analysis job and return its ID."""
        if job_id is None:
            job_id = str(uuid4())
        now = time.time()
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "processing",
                "progress": 0,
                "total_clauses": 0,
                "processed_clauses": 0,
                "clauses": [],
                "risk_summary": {
                    "high_risk_count": 0,
                    "medium_risk_count": 0,
                    "low_risk_count": 0,
                    "average_risk_score": 0.0,
                },
                "document_summary": None,
            }
            self._job_timestamps[job_id] = now
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve current state of a job. Returns None if not found."""
        with self._lock:
            return self._jobs.get(job_id, None)

    def update_job(self, job_id: str, **updates) -> bool:
        """Apply partial updates to a job. Returns False if job not found."""
        with self._lock:
            if job_id not in self._jobs:
                return False
            for key, value in updates.items():
                self._jobs[job_id][key] = value
            return True

    def set_total_clauses(self, job_id: str, total: int):
        """Set the total number of clauses for progress tracking."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["total_clauses"] = total

    def append_clause(self, job_id: str, clause_data: Dict[str, Any]):
        """Add an analyzed clause result to the job and increment progress."""
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id]["clauses"].append(clause_data)
            self._jobs[job_id]["processed_clauses"] = len(
                self._jobs[job_id]["clauses"]
            )
            total = self._jobs[job_id]["total_clauses"]
            if total > 0:
                self._jobs[job_id]["progress"] = int(
                    (self._jobs[job_id]["processed_clauses"] / total) * 100
                )

    def set_completed(self, job_id: str, risk_summary: Dict[str, Any], document_summary: Dict[str, Any]):
        """Mark a job as completed with final aggregates."""
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id]["status"] = "completed"
            self._jobs[job_id]["progress"] = 100
            self._jobs[job_id]["risk_summary"] = risk_summary
            self._jobs[job_id]["document_summary"] = document_summary
            self._job_timestamps[job_id] = time.time()

    def set_error(self, job_id: str, error_message: str):
        """Mark a job as failed with error details."""
        with self._lock:
            if job_id not in self._jobs:
                return
            self._jobs[job_id]["status"] = "error"
            self._jobs[job_id]["error"] = error_message
            self._job_timestamps[job_id] = time.time()

    def clear_clauses(self, job_id: str):
        """Remove clause data from memory once persisted to DB."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id]["clauses"] = []

    def cleanup_finished_jobs(self):
        """Evict completed/errored jobs older than MEMORY_CLEANUP_AGE seconds."""
        now = time.time()
        with self._lock:
            expired = [
                jid for jid, job in self._jobs.items()
                if job["status"] in ("completed", "error")
                and (now - self._job_timestamps.get(jid, 0)) > self.MEMORY_CLEANUP_AGE
            ]
            for jid in expired:
                del self._jobs[jid]
                self._job_timestamps.pop(jid, None)

    def get_summary(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a lightweight status summary without full clause payloads."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            return {
                "job_id": job["job_id"],
                "status": job["status"],
                "progress": job["progress"],
                "total_clauses": job["total_clauses"],
                "processed_clauses": job["processed_clauses"],
                "risk_summary": job["risk_summary"],
                "document_summary": job["document_summary"],
            }


# Singleton instance used across all backend modules
state_store = InMemoryStateStore()
