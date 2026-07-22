import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scoring import (
    _keyword_penalty, _detect_category, _cosine_similarity,
    _compute_quality_scores, _generate_suggested_text,
    split_into_clauses, HIGH_RISK_CORPUS, KEYWORD_PATTERNS,
    CATEGORY_KEYWORDS, RISK_THRESHOLDS,
)
import numpy as np


class TestKeywordPenalty:
    def test_no_match(self):
        assert _keyword_penalty("This is a benign clause.") == 0.0

    def test_single_match(self):
        penalty = _keyword_penalty("This includes unlimited liability for all damages.")
        assert penalty >= 0.20

    def test_multiple_matches_capped(self):
        text = "unlimited liability binding arbitration no refund no warranty non-compete"
        penalty = _keyword_penalty(text)
        assert penalty <= 1.0

    def test_case_insensitive(self):
        p1 = _keyword_penalty("Unlimited Liability")
        p2 = _keyword_penalty("unlimited liability")
        assert p1 == p2


class TestDetectCategory:
    def test_termination(self):
        assert _detect_category("termination at any time without notice") == "termination"

    def test_liability(self):
        assert _detect_category("liability for damages") == "liability"

    def test_general_fallback(self):
        assert _detect_category("The sky is blue.") == "general"

    def test_data_privacy(self):
        assert _detect_category("GDPR compliance required for data protection") == "data_privacy"


class TestCosmeticSimilarity:
    def test_identical(self):
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])
        assert _cosine_similarity(a, b) == pytest.approx(1.0)

    def test_orthogonal(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_zero_vector(self):
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 0.0])
        assert _cosine_similarity(a, b) == 0.0


class TestQualityScores:
    def test_clarity_short(self):
        quality = _compute_quality_scores("Short.", [], "general")
        assert quality["clarity_score"] < 0

    def test_clarity_optimal(self):
        words = "This clause has a reasonable length with enough detail to be clear and specific about obligations."
        quality = _compute_quality_scores(words, [], "general")
        assert quality["clarity_score"] > 0

    def test_balance_one_sided(self):
        text = "Provider shall do X. Provider shall do Y. Provider shall do Z. Client shall not."
        quality = _compute_quality_scores(text, [], "general")
        assert quality["balance_score"] < 0


class TestGeneratedSuggestedText:
    def test_unlimited_liability(self):
        original = "Party A bears unlimited liability for all damages."
        suggested = _generate_suggested_text(original, "liability", ["Unlimited liability exposure"])
        assert "capped" in suggested.lower()

    def test_no_refund(self):
        original = "No refunds under any circumstances."
        suggested = _generate_suggested_text(original, "payment", ["No refund policy"])
        assert "pro-rata" in suggested.lower()

    def test_no_change_for_good_clause(self):
        original = "This is a fair and balanced clause."
        suggested = _generate_suggested_text(original, "general", [])
        assert suggested == original


class TestSplitIntoClauses:
    def test_section_split(self):
        text = "Section 1. First clause.\nSection 2. Second clause.\nSection 3. Third clause."
        clauses = split_into_clauses(text)
        assert len(clauses) >= 2

    def test_paragraph_split(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        clauses = split_into_clauses(text)
        assert len(clauses) >= 2

    def test_single_clause(self):
        text = "Just one short clause here."
        clauses = split_into_clauses(text)
        assert len(clauses) == 1

    def test_empty_text(self):
        clauses = split_into_clauses("")
        assert len(clauses) == 1


class TestConstants:
    def test_high_risk_corpus_count(self):
        assert len(HIGH_RISK_CORPUS) >= 10

    def test_keyword_patterns(self):
        assert len(KEYWORD_PATTERNS) >= 17

    def test_thresholds_ordered(self):
        assert RISK_THRESHOLDS["high"] > RISK_THRESHOLDS["medium"] > RISK_THRESHOLDS["low"]

    def test_categories(self):
        assert "termination" in CATEGORY_KEYWORDS
        assert "liability" in CATEGORY_KEYWORDS
        assert "data_privacy" in CATEGORY_KEYWORDS
