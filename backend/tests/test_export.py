import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from export_service import generate_csv_report, generate_txt_report, generate_clause_comparison_csv


class TestExportService:
    def test_csv_report_generation(self):
        clauses = [{
            "original_text": "Test clause with unlimited liability.",
            "suggested_text": "Test clause with capped liability.",
            "risk_score": 0.75,
            "risk_level": "high",
            "category": "liability",
            "flags": ["Unlimited liability exposure"],
            "suggestions": ["Cap liability"],
            "pros": [],
            "cons": ["Unlimited risk"],
            "quality": {"clarity_score": 1},
            "compliance_matches": [],
        }]
        risk_summary = {"high_risk_count": 1, "medium_risk_count": 0, "low_risk_count": 0, "average_risk_score": 0.75}
        doc_summary = {"health_score": 45, "overall_health": "concerning", "verdict": "Review needed"}
        csv_output = generate_csv_report(clauses, risk_summary, doc_summary)
        assert "Clause-Level Analysis" in csv_output
        assert "Test clause with unlimited liability" in csv_output
        assert "0.75" in csv_output

    def test_txt_report_generation(self):
        clauses = [{"original_text": "Test clause.", "suggested_text": "Improved.", "risk_score": 0.5, "risk_level": "medium", "category": "general", "flags": [], "suggestions": []}]
        risk_summary = {"high_risk_count": 0, "medium_risk_count": 1, "low_risk_count": 0, "average_risk_score": 0.5}
        doc_summary = {"health_score": 60, "overall_health": "moderate", "verdict": "Some risk found", "key_findings": ["1 of 1 clauses have moderate risk."]}
        txt_output = generate_txt_report(clauses, risk_summary, doc_summary)
        assert "AI-Driven Legal Document Analyzer" in txt_output
        assert "MODERATE" in txt_output
        assert "RISK SUMMARY" in txt_output

    def test_comparison_csv(self):
        clauses_a = [{"original_text": "Clause A1", "risk_score": 0.8, "risk_level": "high", "category": "liability"}]
        clauses_b = [{"original_text": "Clause B1", "risk_score": 0.3, "risk_level": "low", "category": "liability"}]
        csv_output = generate_clause_comparison_csv(clauses_a, clauses_b)
        assert "Document Comparison Report" in csv_output
        assert "0.8" in csv_output
        assert "0.3" in csv_output

    def test_empty_clauses(self):
        csv_output = generate_csv_report([], {}, {})
        assert "Clause-Level Analysis" in csv_output
