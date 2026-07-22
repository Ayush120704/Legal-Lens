import csv
import io
from typing import List, Dict, Any


def generate_csv_report(clauses: List[Dict[str, Any]], risk_summary: Dict[str, Any], document_summary: Dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["AI-Driven Legal Document Analyzer - Report"])
    writer.writerow([])

    if document_summary:
        writer.writerow(["Document Health Summary"])
        writer.writerow(["Health Score", document_summary.get("health_score", "N/A")])
        writer.writerow(["Overall Health", document_summary.get("overall_health", "N/A")])
        writer.writerow(["Verdict", document_summary.get("verdict", "N/A")])
        writer.writerow([])

    if risk_summary:
        writer.writerow(["Risk Summary"])
        writer.writerow(["High Risk Clauses", risk_summary.get("high_risk_count", 0)])
        writer.writerow(["Medium Risk Clauses", risk_summary.get("medium_risk_count", 0)])
        writer.writerow(["Low Risk Clauses", risk_summary.get("low_risk_count", 0)])
        writer.writerow(["Average Risk Score", risk_summary.get("average_risk_score", 0.0)])
        writer.writerow([])

    writer.writerow(["Clause-Level Analysis"])
    writer.writerow([
        "Index", "Category", "Risk Level", "Risk Score",
        "Original Text Preview", "Suggested Text Preview",
        "Flags", "Suggestions"
    ])

    for i, clause in enumerate(clauses):
        writer.writerow([
            i + 1,
            clause.get("category", "general"),
            clause.get("risk_level", "low"),
            clause.get("risk_score", 0.0),
            clause.get("original_text", "")[:200],
            clause.get("suggested_text", "")[:200],
            "; ".join(clause.get("flags", [])),
            "; ".join(clause.get("suggestions", [])),
        ])

    return output.getvalue()


def generate_clause_comparison_csv(clauses_a: List[Dict[str, Any]], clauses_b: List[Dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Document Comparison Report"])
    writer.writerow([])
    writer.writerow(["Index", "Doc A Category", "Doc A Risk", "Doc A Score", "Doc B Category", "Doc B Risk", "Doc B Score", "Risk Delta"])

    max_len = max(len(clauses_a), len(clauses_b))
    for i in range(max_len):
        ca = clauses_a[i] if i < len(clauses_a) else {}
        cb = clauses_b[i] if i < len(clauses_b) else {}
        delta = (cb.get("risk_score", 0) - ca.get("risk_score", 0)) if ca and cb else 0
        writer.writerow([
            i + 1,
            ca.get("category", "-") if ca else "-",
            ca.get("risk_level", "-") if ca else "-",
            ca.get("risk_score", "-") if ca else "-",
            cb.get("category", "-") if cb else "-",
            cb.get("risk_level", "-") if cb else "-",
            cb.get("risk_score", "-") if cb else "-",
            round(delta, 4) if delta else "-",
        ])

    return output.getvalue()


def generate_txt_report(clauses: List[Dict[str, Any]], risk_summary: Dict[str, Any], document_summary: Dict[str, Any]) -> str:
    lines = []
    lines.append("=" * 60)
    lines.append("AI-Driven Legal Document Analyzer - Analysis Report")
    lines.append("=" * 60)
    lines.append("")

    if document_summary:
        lines.append("DOCUMENT HEALTH SUMMARY")
        lines.append("-" * 40)
        lines.append(f"  Health Score:  {document_summary.get('health_score', 'N/A')}/100")
        lines.append(f"  Overall:       {document_summary.get('overall_health', 'N/A').upper()}")
        lines.append(f"  Verdict:       {document_summary.get('verdict', 'N/A')}")
        if document_summary.get("key_findings"):
            lines.append("  Key Findings:")
            for f in document_summary["key_findings"]:
                lines.append(f"    - {f}")
        lines.append("")

    if risk_summary:
        lines.append("RISK SUMMARY")
        lines.append("-" * 40)
        lines.append(f"  High Risk:   {risk_summary.get('high_risk_count', 0)}")
        lines.append(f"  Medium Risk: {risk_summary.get('medium_risk_count', 0)}")
        lines.append(f"  Low Risk:    {risk_summary.get('low_risk_count', 0)}")
        lines.append(f"  Avg Score:   {risk_summary.get('average_risk_score', 0.0)}")
        lines.append("")

    lines.append("CLAUSE-LEVEL ANALYSIS")
    lines.append("=" * 60)
    for i, clause in enumerate(clauses):
        lines.append(f"\n--- Clause {i + 1} ---")
        lines.append(f"  Category:    {clause.get('category', 'general')}")
        lines.append(f"  Risk Level:  {clause.get('risk_level', 'low').upper()}")
        lines.append(f"  Risk Score:  {clause.get('risk_score', 0.0)}")
        original = clause.get("original_text", "")
        lines.append(f"  Original:    {original[:150]}{'...' if len(original) > 150 else ''}")
        suggested = clause.get("suggested_text", "")
        if suggested:
            lines.append(f"  Suggested:   {suggested[:150]}{'...' if len(suggested) > 150 else ''}")
        if clause.get("flags"):
            lines.append(f"  Flags:       {'; '.join(clause['flags'])}")
        if clause.get("suggestions"):
            lines.append(f"  Suggestions: {'; '.join(clause['suggestions'])}")
        lines.append("")

    return "\n".join(lines)
