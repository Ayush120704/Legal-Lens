import time
import asyncio
from typing import Dict, Any, List

from scoring import RiskScoringEngine, split_into_clauses
from rag.vector_store import get_vector_store
from database import state_store


# Global scoring engine instance (initialized lazily to avoid import-time model loading)
_scoring_engine = None
_vector_store = None


def _get_scoring_engine() -> RiskScoringEngine:
    """Lazy-initialize the scoring engine."""
    global _scoring_engine
    if _scoring_engine is None:
        _scoring_engine = RiskScoringEngine()
    return _scoring_engine


def _get_vector_store():
    """Lazy-initialize the vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = get_vector_store()
    return _vector_store


def _compute_risk_summary(clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate risk summary from all analyzed clauses."""
    high_count = 0
    medium_count = 0
    low_count = 0
    total_score = 0.0

    for clause in clauses:
        level = clause.get("risk_level", "low")
        score = clause.get("risk_score", 0.0)
        total_score += score

        if level == "high":
            high_count += 1
        elif level == "medium":
            medium_count += 1
        else:
            low_count += 1

    total = len(clauses)
    avg_score = round(total_score / total, 4) if total > 0 else 0.0

    return {
        "high_risk_count": high_count,
        "medium_risk_count": medium_count,
        "low_risk_count": low_count,
        "average_risk_score": avg_score,
    }


def _compute_document_summary(clauses: List[Dict[str, Any]], risk_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Compute document-level summary with health score, findings, and missing protections."""
    total = len(clauses)
    high = risk_summary["high_risk_count"]
    medium = risk_summary["medium_risk_count"]
    low = risk_summary["low_risk_count"]
    avg_risk = risk_summary["average_risk_score"]

    # Health score: 100 = perfectly safe, 0 = extremely risky
    # Formula: 100 - (weighted risk deductions)
    high_deduction = high * 20
    medium_deduction = medium * 8
    low_deduction = low * 2
    risk_penalty = avg_risk * 30
    health_score = max(0, min(100, 100 - high_deduction - medium_deduction - low_deduction - risk_penalty))
    health_score = round(health_score, 1)

    # Overall health classification
    if health_score >= 80:
        overall_health = "good"
    elif health_score >= 60:
        overall_health = "moderate"
    elif health_score >= 40:
        overall_health = "concerning"
    else:
        overall_health = "critical"

    # Generate verdict
    if overall_health == "good":
        verdict = "Document appears well-structured with minimal risk."
    elif overall_health == "moderate":
        verdict = "Notable risk areas. Negotiate key terms."
    elif overall_health == "concerning":
        verdict = "Significant risk exposure. Legal review recommended."
    else:
        verdict = "Critical issues detected. Do not sign without major revisions."

    # Key findings
    key_findings = []
    if high > 0:
        key_findings.append(f"{high} of {total} clauses carry high risk.")
    if medium > 0:
        key_findings.append(f"{medium} of {total} clauses have moderate risk.")
    if low > 0:
        key_findings.append(f"{low} of {total} clauses are low risk.")

    # Detect missing protections
    categories_present = set()
    for clause in clauses:
        categories_present.add(clause.get("category", "general"))

    missing_protections = []
    expected_categories = {
        "warranty": ("warranty", "No warranty clause"),
        "force_majeure": ("force_majeure", "No force majeure"),
        "payment": ("payment", "No payment terms"),
        "ip_rights": ("intellectual_property", "No IP clause"),
        "confidentiality": ("confidentiality", "No confidentiality clause"),
        "dispute": ("dispute", "No dispute resolution mechanism"),
    }

    for key, (cat, desc) in expected_categories.items():
        if cat not in categories_present:
            missing_protections.append({"key": key, "description": desc})

    if missing_protections:
        missing_descs = [m["description"] for m in missing_protections]
        key_findings.append(f"Missing {len(missing_protections)} protections: {', '.join(missing_descs)}.")

    # Critical issues (high-risk clauses)
    critical_issues = []
    for clause in clauses:
        if clause.get("risk_level") == "high":
            flags = clause.get("flags", [])
            primary_issue = flags[0] if flags else "High risk detected"
            critical_issues.append({
                "clause_preview": clause.get("original_text", "")[:100],
                "risk_score": clause.get("risk_score", 0),
                "primary_issue": primary_issue,
            })

    # Top risk patterns
    pattern_counts = {}
    for clause in clauses:
        for flag in clause.get("flags", []):
            pattern_counts[flag] = pattern_counts.get(flag, 0) + 1

    top_risk_patterns = [
        {"pattern": pattern, "count": count}
        for pattern, count in sorted(pattern_counts.items(), key=lambda x: -x[1])[:5]
    ]

    # Categories detected
    categories_detected = list(categories_present)

    return {
        "overall_health": overall_health,
        "health_score": health_score,
        "total_clauses": total,
        "high_risk_count": high,
        "medium_risk_count": medium,
        "low_risk_count": low,
        "average_risk_score": avg_risk,
        "verdict": verdict,
        "key_findings": key_findings,
        "missing_protections": missing_protections,
        "critical_issues": critical_issues,
        "top_risk_patterns": top_risk_patterns,
        "categories_detected": categories_detected,
    }


async def analyze_document(job_id: str, text: str):
    """
    Background worker that processes a legal document asynchronously.

    Steps:
        1. Split text into individual clauses
        2. For each clause, compute risk score, detect category, match compliance
        3. Broadcast progress via WebSocket
        4. Compute aggregate summary on completion
    """
    try:
        # Step 1: Split into clauses
        clauses = split_into_clauses(text)
        total = len(clauses)
        state_store.set_total_clauses(job_id, total)

        scoring_engine = _get_scoring_engine()
        vector_store = _get_vector_store()

        # Step 2: Process each clause sequentially
        for i, clause_text in enumerate(clauses):
            # Score the clause
            clause_result = scoring_engine.score_clause(clause_text)

            # Query ChromaDB for compliance matches
            compliance_matches = vector_store.query(clause_text, n_results=3)
            clause_result["compliance_matches"] = compliance_matches

            # Store the clause result
            state_store.append_clause(job_id, clause_result)

            # Small delay to simulate processing and allow WebSocket messages
            await asyncio.sleep(0.1)

        # Step 3: Compute final aggregates
        job_data = state_store.get_job(job_id)
        all_clauses = job_data["clauses"]

        risk_summary = _compute_risk_summary(all_clauses)
        document_summary = _compute_document_summary(all_clauses, risk_summary)

        # Step 4: Mark as completed
        state_store.set_completed(job_id, risk_summary, document_summary)

    except Exception as e:
        state_store.set_error(job_id, str(e))
