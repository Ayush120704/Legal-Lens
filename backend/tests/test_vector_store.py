import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rag.vector_store import SEED_GUIDELINES


class TestSeedGuidelines:
    def test_guidelines_count(self):
        assert len(SEED_GUIDELINES) >= 30, f"Expected at least 30 guidelines, got {len(SEED_GUIDELINES)}"

    def test_gdpr_present(self):
        gdpr_guidelines = [g for g in SEED_GUIDELINES if g["metadata"]["regulation"] == "GDPR"]
        assert len(gdpr_guidelines) >= 4

    def test_ccpa_present(self):
        ccpa_guidelines = [g for g in SEED_GUIDELINES if g["metadata"]["regulation"] == "CCPA"]
        assert len(ccpa_guidelines) >= 3

    def test_hipaa_present(self):
        hipaa_guidelines = [g for g in SEED_GUIDELINES if g["metadata"]["regulation"] == "HIPAA"]
        assert len(hipaa_guidelines) >= 3

    def test_sox_present(self):
        sox_guidelines = [g for g in SEED_GUIDELINES if g["metadata"]["regulation"] == "SOX"]
        assert len(sox_guidelines) >= 2

    def test_iso_present(self):
        iso_guidelines = [g for g in SEED_GUIDELINES if g["metadata"]["regulation"] == "ISO 27001"]
        assert len(iso_guidelines) >= 2

    def test_all_have_ids(self):
        for g in SEED_GUIDELINES:
            assert g["id"], f"Guideline missing ID: {g}"

    def test_all_have_text(self):
        for g in SEED_GUIDELINES:
            assert g["text"], f"Guideline missing text: {g['id']}"

    def test_all_have_metadata_with_regulation(self):
        for g in SEED_GUIDELINES:
            assert "regulation" in g["metadata"], f"Guideline missing regulation metadata: {g['id']}"
