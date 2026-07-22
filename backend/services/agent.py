import time
import asyncio
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from scoring import RiskScoringEngine, split_into_clauses
from rag.vector_store import get_vector_store
from database import state_store
from models import Document, Clause
from llm_service import llm_service

_scoring_engine = None
_vector_store = None


def _get_scoring_engine() -> RiskScoringEngine:
    global _scoring_engine
    if _scoring_engine is None:
        _scoring_engine = RiskScoringEngine()
    return _scoring_engine


def _get_vector_store():
    global _vector_store
    if _vector_store is None:
        _vector_store = get_vector_store()
    return _vector_store


def _compute_risk_summary(clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
    high_count = sum(1 for c in clauses if c.get("risk_level") == "high")
    medium_count = sum(1 for c in clauses if c.get("risk_level") == "medium")
    low_count = sum(1 for c in clauses if c.get("risk_level") == "low")
    total_score = sum(c.get("risk_score", 0.0) for c in clauses)
    total = len(clauses)
    avg_score = round(total_score / total, 4) if total > 0 else 0.0
    return {"high_risk_count": high_count, "medium_risk_count": medium_count, "low_risk_count": low_count, "average_risk_score": avg_score}


def _compute_document_summary(clauses: List[Dict[str, Any]], risk_summary: Dict[str, Any]) -> Dict[str, Any]:
    total = len(clauses)
    high = risk_summary["high_risk_count"]
    medium = risk_summary["medium_risk_count"]
    low = risk_summary["low_risk_count"]
    avg_risk = risk_summary["average_risk_score"]

    high_deduction = high * 20
    medium_deduction = medium * 8
    low_deduction = low * 2
    risk_penalty = avg_risk * 30
    health_score = max(0, min(100, 100 - high_deduction - medium_deduction - low_deduction - risk_penalty))
    health_score = round(health_score, 1)

    if health_score >= 80:
        overall_health = "good"
    elif health_score >= 60:
        overall_health = "moderate"
    elif health_score >= 40:
        overall_health = "concerning"
    else:
        overall_health = "critical"

    verdict_map = {
        "good": "Document appears well-structured with minimal risk.",
        "moderate": "Notable risk areas. Negotiate key terms.",
        "concerning": "Significant risk exposure. Legal review recommended.",
        "critical": "Critical issues detected. Do not sign without major revisions.",
    }
    verdict = verdict_map.get(overall_health, "")

    key_findings = []
    if high > 0:
        key_findings.append(f"{high} of {total} clauses carry high risk.")
    if medium > 0:
        key_findings.append(f"{medium} of {total} clauses have moderate risk.")
    if low > 0:
        key_findings.append(f"{low} of {total} clauses are low risk.")

    categories_present = set(c.get("category", "general") for c in clauses)
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

    critical_issues = []
    for clause in clauses:
        if clause.get("risk_level") == "high":
            flags = clause.get("flags", [])
            primary_issue = flags[0] if flags else "High risk detected"
            critical_issues.append({"clause_preview": clause.get("original_text", "")[:100], "risk_score": clause.get("risk_score", 0), "primary_issue": primary_issue})

    pattern_counts = {}
    for clause in clauses:
        for flag in clause.get("flags", []):
            pattern_counts[flag] = pattern_counts.get(flag, 0) + 1
    top_risk_patterns = [{"pattern": p, "count": c} for p, c in sorted(pattern_counts.items(), key=lambda x: -x[1])[:5]]

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
        "categories_detected": list(categories_present),
    }


async def analyze_document(job_id: str, text: str, document_id: Optional[int] = None, db: Optional[Session] = None):
    try:
        clauses = split_into_clauses(text)
        total = len(clauses)
        state_store.set_total_clauses(job_id, total)

        scoring_engine = _get_scoring_engine()
        vector_store_inst = _get_vector_store()

        for i, clause_text in enumerate(clauses):
            clause_result = scoring_engine.score_clause(clause_text)
            compliance_matches = vector_store_inst.query(clause_text, n_results=3)
            clause_result["compliance_matches"] = compliance_matches

            if llm_service.available:
                llm_analysis = llm_service.enhance_clause_analysis(
                    clause_text, clause_result["risk_level"], clause_result["risk_score"], clause_result["category"]
                )
                clause_result["llm_analysis"] = llm_analysis
                if llm_analysis and "suggested_text" in llm_analysis:
                    clause_result["suggested_text"] = llm_analysis["suggested_text"]

            state_store.append_clause(job_id, clause_result)

            if db and document_id:
                db_clause = Clause(
                    document_id=document_id,
                    clause_index=i,
                    original_text=clause_result["original_text"],
                    suggested_text=clause_result.get("suggested_text"),
                    risk_score=clause_result["risk_score"],
                    risk_level=clause_result["risk_level"],
                    cosine_component=clause_result.get("cosine_component", 0.0),
                    keyword_component=clause_result.get("keyword_component", 0.0),
                    category=clause_result["category"],
                    flags=clause_result.get("flags", []),
                    suggestions=clause_result.get("suggestions", []),
                    pros=clause_result.get("pros", []),
                    cons=clause_result.get("cons", []),
                    quality=clause_result.get("quality", {}),
                    compliance_matches=compliance_matches,
                    llm_analysis=clause_result.get("llm_analysis"),
                )
                db.add(db_clause)

            await asyncio.sleep(0.1)

        job_data = state_store.get_job(job_id)
        all_clauses = job_data["clauses"]

        risk_summary = _compute_risk_summary(all_clauses)
        document_summary = _compute_document_summary(all_clauses, risk_summary)

        if llm_service.available:
            clauses_for_llm = "\n".join([
                f"Clause {i+1} [{c.get('risk_level','N/A')}]: {c.get('original_text','')[:300]}"
                for i, c in enumerate(all_clauses[:20])
            ])
            llm_summary = llm_service.generate_document_summary(clauses_for_llm)
            if llm_summary:
                document_summary["llm_executive_summary"] = llm_summary

        state_store.set_completed(job_id, risk_summary, document_summary)

        if db and document_id:
            db_doc = db.query(Document).filter(Document.id == document_id).first()
            if db_doc:
                db_doc.status = "completed"
                db_doc.progress = 100
                db_doc.total_clauses = total
                db_doc.processed_clauses = total
                db_doc.risk_summary = risk_summary
                db_doc.document_summary = document_summary
            db.commit()

    except Exception as e:
        state_store.set_error(job_id, str(e))
        if db and document_id:
            db_doc = db.query(Document).filter(Document.id == document_id).first()
            if db_doc:
                db_doc.status = "error"
                db_doc.error_message = str(e)
            db.commit()
