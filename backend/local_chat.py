import re
from typing import List, Dict, Any


def answer_question_locally(document_text: str, clauses: List[Dict[str, Any]], document_summary: Dict[str, Any], question: str) -> str:
    q = question.lower().strip()

    high_clauses = [c for c in clauses if c.get("risk_level") == "high"]
    medium_clauses = [c for c in clauses if c.get("risk_level") == "medium"]
    critical_issues = document_summary.get("critical_issues", [])
    missing = document_summary.get("missing_protections", [])
    key_findings = document_summary.get("key_findings", [])
    patterns = document_summary.get("top_risk_patterns", [])
    health_score = document_summary.get("health_score")

    if _is_asking_about(q, "high_risk", "riskiest", "worst", "dangerous", "critical"):
        return _answer_high_risk(high_clauses, critical_issues)

    if _is_asking_about(q, "summary", "overview", "summarize", "what is this", "tell me about"):
        return _answer_summary(document_summary, high_clauses, medium_clauses)

    if _is_asking_about(q, "health", "score", "rating", "how risky"):
        return _answer_health(health_score, document_summary, high_clauses, medium_clauses)

    if _is_asking_about(q, "negotiat", "improve", "suggest", "recommend", "fix", "change"):
        return _answer_negotiation(high_clauses)

    if _is_asking_about(q, "missing", "lack", "doesn't have", "absent", "protection", "should add"):
        return _answer_missing(missing)

    if _is_asking_about(q, "termination", "cancel", "end contract"):
        return _answer_category(clauses, "termination", "Termination")

    if _is_asking_about(q, "liability", "damages", "indemn"):
        return _answer_category(clauses, "liability", "Liability")

    if _is_asking_about(q, "renewal", "auto-renew", "extend"):
        return _answer_category(clauses, "renewal", "Renewal")

    if _is_asking_about(q, "dispute", "arbitrat", "litigat", "court", "jurisdiction"):
        return _answer_category(clauses, "dispute", "Dispute Resolution")

    if _is_asking_about(q, "privacy", "data", "gdpr", "ccpa", "hipaa", "personal"):
        return _answer_category(clauses, "data_privacy", "Data Privacy")

    if _is_asking_about(q, "confidential", "non-disclosure", "proprietary", "secret"):
        return _answer_category(clauses, "confidentiality", "Confidentiality")

    if _is_asking_about(q, "ip", "intellectual property", "patent", "copyright", "trademark"):
        return _answer_category(clauses, "intellectual_property", "Intellectual Property")

    if _is_asking_about(q, "payment", "fee", "price", "cost", "invoice", "billing"):
        return _answer_category(clauses, "payment", "Payment")

    if _is_asking_about(q, "warranty", "guarantee"):
        return _answer_category(clauses, "warranty", "Warranty")

    if _is_asking_about(q, "force majeure", "act of god", "unforeseeable"):
        return _answer_category(clauses, "force_majeure", "Force Majeure")

    if _is_asking_about(q, "clause", "count", "how many", "section"):
        return _answer_clause_count(clauses, high_clauses, medium_clauses)

    if _is_asking_about(q, "pattern", "common", "frequent", "trend"):
        return _answer_patterns(patterns)

    if _is_asking_about(q, "compliance", "regulation", "legal require", "gdpr", "regulatory"):
        return _answer_compliance(clauses)

    if _is_asking_about(q, "pros", "strength", "good", "positive", "favorable"):
        return _answer_pros(clauses)

    if _is_asking_about(q, "cons", "weakness", "bad", "negative", "unfavorable", "risk"):
        return _answer_cons(clauses)

    return _answer_general(document_summary, high_clauses, missing)


def _is_asking_about(question: str, *keywords: str) -> bool:
    for kw in keywords:
        if kw in question:
            return True
    return False


def _answer_summary(doc_summary: Dict[str, Any], high_clauses: List, medium_clauses: List) -> str:
    verdict = doc_summary.get("verdict", "No verdict available.")
    findings = doc_summary.get("key_findings", [])
    health = doc_summary.get("health_score", "N/A")
    lines = [f"**Document Summary**\nHealth Score: {health}/100\n{verdict}\n"]
    if findings:
        lines.append("**Key Findings:**")
        for f in findings:
            lines.append(f"- {f}")
    if high_clauses:
        lines.append(f"\n! {len(high_clauses)} high-risk clause(s) detected that need attention.")
    if medium_clauses:
        lines.append(f"* {len(medium_clauses)} medium-risk clause(s) found.")
    return "\n".join(lines)


def _answer_health(health_score, doc_summary, high_clauses, medium_clauses) -> str:
    overall = doc_summary.get("overall_health", "unknown")
    verdict = doc_summary.get("verdict", "")
    h = len(high_clauses)
    m = len(medium_clauses)
    return (
        f"The document health score is **{health_score}/100** ({overall.upper()}).\n"
        f"{verdict}\n"
        f"Breakdown: {h} high-risk, {m} medium-risk clauses."
    )


def _answer_high_risk(high_clauses: List, critical_issues: List) -> str:
    if not high_clauses and not critical_issues:
        return "No high-risk clauses detected in this document."
    lines = ["**High-Risk Clauses:**"]
    issues = critical_issues or [
        {"clause_preview": c.get("original_text", "")[:120], "risk_score": c.get("risk_score", 0), "primary_issue": (c.get("flags") or ["High risk"])[0]}
        for c in high_clauses
    ]
    for i, issue in enumerate(issues, 1):
        score = issue.get("risk_score", 0)
        if isinstance(score, float):
            score = f"{score * 100:.0f}%"
        lines.append(f"\n{i}. **Risk Score: {score}**")
        lines.append(f"   Issue: {issue.get('primary_issue', 'High risk')}")
        preview = issue.get("clause_preview", "")
        if preview:
            lines.append(f"   Text: \"{preview[:100]}...\"")
    return "\n".join(lines)


def _answer_negotiation(high_clauses: List) -> str:
    if not high_clauses:
        return "No critical clauses found that need negotiation. The document appears well-structured."
    lines = ["**Negotiation Recommendations:**\n"]
    for c in high_clauses[:5]:
        category = c.get("category", "general")
        suggestions = c.get("suggestions", [])
        flags = c.get("flags", [])
        lines.append(f"**{category.replace('_', ' ').title()} Clause:**")
        if flags:
            lines.append(f"  Risk: {flags[0]}")
        if suggestions:
            for s in suggestions[:2]:
                lines.append(f"  Tip: {s}")
        lines.append("")
    if len(high_clauses) > 5:
        lines.append(f"... and {len(high_clauses) - 5} more clause(s).")
    return "\n".join(lines)


def _answer_missing(missing: List) -> str:
    if not missing:
        return "No missing standard protections detected. The document covers the essential clauses."
    descs = [m["description"] for m in missing]
    return (
        f"**Missing Protections Detected:** {len(missing)}\n\n"
        + "\n".join(f"- {d}" for d in descs)
        + "\n\nConsider adding these clauses to protect your interests."
    )


def _answer_category(clauses: List, category: str, display_name: str) -> str:
    cat_clauses = [c for c in clauses if c.get("category") == category]
    if not cat_clauses:
        return f"No **{display_name}** clauses found in this document."
    lines = [f"**{display_name} Clauses ({len(cat_clauses)} found):**\n"]
    for i, c in enumerate(cat_clauses, 1):
        risk = c.get("risk_level", "low").upper()
        score = c.get("risk_score", 0)
        if isinstance(score, float):
            score = f"{score * 100:.0f}%"
        lines.append(f"{i}. [{risk}] Score: {score}")
        lines.append(f"   \"{c.get('original_text', '')[:150]}...\"")
        flags = c.get("flags", [])
        if flags:
            lines.append(f"   Flags: {', '.join(flags[:3])}")
        lines.append("")
    return "\n".join(lines)


def _answer_clause_count(clauses: List, high: List, medium: List) -> str:
    total = len(clauses)
    low = len([c for c in clauses if c.get("risk_level") == "low"])
    return f"The document has **{total}** clause(s) in total.\n- {len(high)} high risk\n- {len(medium)} medium risk\n- {low} low risk"


def _answer_patterns(patterns: List) -> str:
    if not patterns:
        return "No recurring risk patterns detected."
    lines = ["**Top Risk Patterns:**"]
    for p in patterns:
        lines.append(f"- {p['pattern']} (appears {p['count']} time(s))")
    return "\n".join(lines)


def _answer_compliance(clauses: List) -> str:
    all_matches = []
    for c in clauses:
        for m in c.get("compliance_matches", []):
            all_matches.append(m)
    seen = set()
    unique = []
    for m in all_matches:
        mid = m.get("id", "")
        if mid not in seen:
            seen.add(mid)
            unique.append(m)
    if not unique:
        return "No specific regulatory compliance matches were found for this document's clauses."
    lines = ["**Compliance Guideline Matches:**\n"]
    for m in unique[:8]:
        reg = m.get("metadata", {}).get("regulation", "Unknown")
        tid = m.get("id", "")
        score = m.get("relevance_score", 0)
        lines.append(f"- **{reg}** ({tid}) - relevance: {score:.2f}")
    if len(unique) > 8:
        lines.append(f"\n... and {len(unique) - 8} more matches.")
    return "\n".join(lines)


def _answer_pros(clauses: List) -> str:
    all_pros = []
    for c in clauses:
        for p in c.get("pros", []):
            if p not in all_pros:
                all_pros.append(p)
    if not all_pros:
        return "No specific strengths identified in the clause analysis."
    return "**Detected Strengths:**\n" + "\n".join(f"+ {p}" for p in all_pros[:8])


def _answer_cons(clauses: List) -> str:
    all_cons = []
    for c in clauses:
        for p in c.get("cons", []):
            if p not in all_cons:
                all_cons.append(p)
    if not all_cons:
        return "No significant weaknesses identified."
    return "**Detected Weaknesses:**\n" + "\n".join(f"- {p}" for p in all_cons[:8])


def _answer_general(doc_summary: Dict[str, Any], high_clauses: List, missing: List) -> str:
    health = doc_summary.get("health_score", "N/A")
    verdict = doc_summary.get("verdict", "")
    lines = [
        f"I analyzed this document. Health score: **{health}/100**. {verdict}",
    ]
    if high_clauses:
        lines.append(f"\n! {len(high_clauses)} high-risk clause(s) found. Try asking \"What are the high-risk clauses?\" for details.")
    if missing:
        lines.append(f"\n* {len(missing)} missing standard protection(s). Try asking \"What's missing?\"")
    lines.append("\nYou can ask me: \"Summarize the document\", \"What should I negotiate?\", \"Show me liability clauses\", or \"What compliance issues exist?\"")
    return "\n".join(lines)
