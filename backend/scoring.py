import re
import math
import numpy as np
from typing import Dict, List, Tuple, Any

# --- High-Risk Target Corpus ---
# These are canonical high-risk clause templates used for cosine similarity
HIGH_RISK_CORPUS = [
    "automatic renewal without notice or consent required by either party",
    "unlimited liability for all damages losses and expenses incurred",
    "no refund policy under any circumstances including force majeure",
    "termination at any time without cause or advance written notice",
    "binding arbitration waiving all rights to jury trial or class action",
    "indemnification of all parties for any reason whatsoever",
    "intellectual property ownership transferred completely to provider",
    "non-compete clause restricting future employment indefinitely",
    "confidentiality obligation surviving termination indefinitely without limit",
    "unilateral amendment rights allowing changes to terms without notice",
]

# --- Keyword Penalty Patterns ---
KEYWORD_PATTERNS = {
    "unlimited liability": 0.20,
    "automatic renewal": 0.15,
    "no refund": 0.15,
    "termination at any time": 0.15,
    "without notice": 0.10,
    "binding arbitration": 0.10,
    "waiving rights": 0.10,
    "indemnif": 0.10,
    "sole discretion": 0.08,
    "as-is": 0.08,
    "no warranty": 0.10,
    "non-compete": 0.12,
    "perpetual": 0.08,
    "irrevocable": 0.10,
    "hold harmless": 0.06,
    "at-will": 0.08,
    "unilateral": 0.08,
}

# --- Risk Level Thresholds ---
RISK_THRESHOLDS = {
    "high": 0.55,
    "medium": 0.30,
    "low": 0.0,
}

# --- Clause Category Detection ---
CATEGORY_KEYWORDS = {
    "termination": ["terminat", "cancel", "end", "expir", "notice"],
    "liability": ["liabil", "damages", "loss", "indemnif", "responsible"],
    "renewal": ["renew", "renewal", "extend", "continu"],
    "dispute": ["dispute", "arbitrat", "litigat", "court", "jurisdict"],
    "data_privacy": ["gdpr", "ccpa", "hipaa", "privacy", "personal data", "data protection"],
    "confidentiality": ["confidential", "non-disclosure", "proprietary", "trade secret"],
    "intellectual_property": ["intellectual property", "patent", "copyright", "trademark", "ip rights"],
    "payment": ["payment", "fee", "cost", "price", "invoice", "billing"],
    "warranty": ["warranty", "warrant", "guarantee", "represent"],
    "force_majeure": ["force majeure", "act of god", "unforeseeable"],
}

# --- Embedding Cache (loaded once at startup) ---
_embedding_model = None


def _get_embedding_model():
    """Lazy-load the sentence-transformers model."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def _compute_embedding(text: str) -> np.ndarray:
    """Compute a single sentence embedding."""
    model = _get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors using numpy dot product."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _keyword_penalty(text: str) -> float:
    """Calculate cumulative keyword penalty score from detected risk patterns."""
    text_lower = text.lower()
    penalty = 0.0
    for pattern, weight in KEYWORD_PATTERNS.items():
        if pattern.lower() in text_lower:
            penalty += weight
    return min(penalty, 1.0)


def _detect_category(text: str) -> str:
    """Detect the primary clause category based on keyword presence."""
    text_lower = text.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw.lower() in text_lower)
        if count > 0:
            scores[category] = count
    if scores:
        return max(scores, key=scores.get)
    return "general"


def _compute_quality_scores(text: str, flags: List[str], category: str) -> Dict[str, Any]:
    """Compute clarity, balance, and enforceability scores for a clause."""
    word_count = len(text.split())

    # Clarity: penalize very short or very long clauses
    clarity_score = 0
    if word_count < 10:
        clarity_score = -2
    elif word_count < 20:
        clarity_score = -1
    elif 20 <= word_count <= 60:
        clarity_score = 1
    else:
        clarity_score = 0

    # Balance: check for one-sided language
    balance_score = 0
    one_sided_patterns = [
        "provider shall", "client shall", "party shall",
        "shall not", "must not", "will not",
    ]
    one_sided_count = sum(1 for p in one_sided_patterns if p.lower() in text.lower())
    if one_sided_count >= 3:
        balance_score = -1
    elif one_sided_count <= 1:
        balance_score = 1

    # Enforceability: check for specific legal terms
    enforceability_score = 0
    enforceable_terms = [
        "shall", "pursuant to", "notwithstanding",
        "hereinafter", "whereas", "in the event",
        "governing law", "severability", "entire agreement",
    ]
    enforce_count = sum(1 for t in enforceable_terms if t.lower() in text.lower())
    if enforce_count >= 3:
        enforceability_score = 1
    elif enforce_count >= 1:
        enforceability_score = 0
    else:
        enforceability_score = -1

    # Determine strengths and issues
    issues = []
    strengths = []
    if clarity_score < 0:
        issues.append("Clause is too brief - may lack necessary detail.")
    if clarity_score == 0 and word_count > 60:
        issues.append("Clause is lengthy - consider simplification.")
    if balance_score < 0:
        issues.append("Language may be one-sided or overly restrictive.")
    if balance_score > 0:
        strengths.append("Balanced language applies to both parties.")
    if enforceability_score > 0:
        strengths.append("Uses clear mandatory language with defined obligations.")
    if enforceability_score < 0:
        issues.append("Missing standard legal enforceability language.")

    # Category-specific strengths
    if category == "data_privacy":
        strengths.append("References specific data protection regulations.")
    if category == "termination" and balance_score > 0:
        strengths.append("Obligations are mutual.")

    return {
        "clarity_score": clarity_score,
        "balance_score": balance_score,
        "enforceability_score": enforceability_score,
        "issues": ". ".join(issues),
        "strengths": ". ".join(strengths),
    }


def _generate_suggestions(text: str, category: str, flags: List[str], quality: Dict[str, Any]) -> List[str]:
    """Generate actionable improvement suggestions based on analysis."""
    suggestions = []
    text_lower = text.lower()

    # Category-specific suggestions
    if category == "termination":
        if "notice" not in text_lower:
            suggestions.append("Add a 30-day advance written notice requirement.")
        if "refund" not in text_lower and "no refund" in text_lower:
            suggestions.append("Negotiate pro-rata refund for early termination.")
        suggestions.append("Add termination-for-cause and notice periods.")
    elif category == "liability":
        suggestions.append("This clause is high-risk. Re-negotiate before signing.")
        suggestions.append("Cap liability at 12 months of fees.")
    elif category == "renewal":
        suggestions.append("Add a 30-day opt-out window before renewal.")
    elif category == "dispute":
        suggestions.append("Add venue selection, cost-sharing, and appeal rights.")
    elif category == "confidentiality":
        if "surviv" not in text_lower:
            suggestions.append("Define confidentiality survival period post-termination.")
    elif category == "data_privacy":
        if "breach" not in text_lower:
            suggestions.append("Add data breach notification procedures.")
    elif category == "intellectual_property":
        if "license" not in text_lower:
            suggestions.append("Specify IP licensing terms and restrictions.")
    elif category == "payment":
        if "late" not in text_lower:
            suggestions.append("Define late payment penalties and grace periods.")
    elif category == "warranty":
        if "limit" not in text_lower:
            suggestions.append("Limit warranty scope and duration explicitly.")
    elif category == "force_majeure":
        if "notice" not in text_lower:
            suggestions.append("Add notification requirements for force majeure events.")

    # Flag-based suggestions
    for flag in flags:
        if "unlimited" in flag.lower() and "liability" in flag.lower():
            suggestions.append("Cap liability to total fees paid under the agreement.")
        if "automatic" in flag.lower() and "renewal" in flag.lower():
            suggestions.append("Require affirmative consent for renewal.")
        if "no refund" in flag.lower():
            suggestions.append("Negotiate partial refund terms for early termination.")
        if "without notice" in flag.lower():
            suggestions.append("Require advance written notice of at least 30 days.")
        if "binding" in flag.lower() and "arbitration" in flag.lower():
            suggestions.append("Retain right to seek injunctive relief in court.")
        if "no advance" in flag.lower() or "no warning" in flag.lower():
            suggestions.append("Require advance written warning before material changes.")

    return suggestions


def _generate_pros_cons(text: str, category: str, quality: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Generate pros and cons lists for a clause."""
    pros = []
    cons = []

    # Quality-based pros/cons
    if quality["strengths"]:
        pros.extend([s.strip() for s in quality["strengths"].split(".") if s.strip()])
    if quality["issues"]:
        cons.extend([c.strip() for c in quality["issues"].split(".") if c.strip()])

    # Category-specific analysis
    text_lower = text.lower()
    if category == "termination":
        if "mutual" in text_lower or "either party" in text_lower:
            pros.append("Obligations are mutual.")
        if "at any time" in text_lower:
            cons.append("Allows termination without cause or notice.")
        if "no refund" in text_lower:
            cons.append("Eliminates refund rights upon termination.")
    elif category == "liability":
        if "unlimited" in text_lower:
            cons.append("Exposes party to unlimited financial liability.")
        if "cap" in text_lower or "limit" in text_lower:
            pros.append("Liability is capped.")
    elif category == "renewal":
        if "automatic" in text_lower:
            cons.append("Auto-renewal locks parties without consent.")
    elif category == "dispute":
        if "arbitration" in text_lower:
            cons.append("Removes right to jury trial.")
    elif category == "confidentiality":
        if "surviv" in text_lower:
            pros.append("Confidentiality survives termination.")
    elif category == "data_privacy":
        pros.append("References specific data protection regulations.")
    elif category == "warranty":
        if "limit" in text_lower or "as-is" in text_lower:
            cons.append("Warranty is limited or disclaimed.")
        else:
            pros.append("Provides warranty coverage.")

    # Fallback if no pros/cons yet
    if not pros:
        pros.append("No strongly protective provisions detected.")
    if not cons:
        cons.append("No significant risk indicators found.")

    # Deduplicate
    pros = list(dict.fromkeys(pros))
    cons = list(dict.fromkeys(cons))

    return pros, cons


def _generate_suggested_text(original: str, category: str, flags: List[str]) -> str:
    """Generate an improved version of the clause with risk mitigations applied."""
    suggested = original
    original_lower = original.lower()

    if "unlimited liability" in original_lower:
        suggested = suggested.replace(
            "unlimited liability",
            "liability capped at total fees paid"
        ).replace(
            "Unlimited Liability",
            "Liability Capped at Total Fees Paid"
        )
    if "automatic renewal" in original_lower and "notice" not in original_lower:
        suggested = suggested.replace(
            "automatic renewal",
            "renewal with opt-out (30-day notice required)"
        ).replace(
            "Automatic Renewal",
            "Renewal with Opt-Out (30-Day Notice Required)"
        )
    if "no refund" in original_lower:
        suggested = suggested.replace(
            "No refunds",
            "Pro-rata refund for unused period"
        ).replace(
            "no refunds",
            "pro-rata refund for unused period"
        )
    if "terminate at any time" in original_lower and "notice" not in original_lower:
        suggested = suggested.replace(
            "terminate at any time without notice",
            "terminate at any time with at least 30 days prior written notice"
        ).replace(
            "Terminate at any time without notice",
            "Terminate at any time with at least 30 days prior written notice"
        )
    if "binding arbitration" in original_lower and "appeal" not in original_lower:
        suggested = suggested.rstrip(".")
        suggested += " with appeal rights and cost-sharing provisions."

    return suggested


class RiskScoringEngine:
    """
    Deterministic risk scoring engine using a 60/40 weighted formula:
        Risk Score = (0.6 * Cosine Similarity to High-Risk Corpus)
                   + (0.4 * Keyword Penalties)

    Uses sentence-transformers for semantic embeddings and regex for keyword matching.
    """

    def __init__(self):
        self._corpus_embeddings = None

    def _ensure_corpus_embeddings(self):
        """Compute and cache embeddings for the high-risk corpus."""
        if self._corpus_embeddings is None:
            self._corpus_embeddings = np.array([
                _compute_embedding(text) for text in HIGH_RISK_CORPUS
            ])

    def score_clause(self, text: str) -> Dict[str, Any]:
        """
        Score a single clause and return a comprehensive analysis dict.

        Returns:
            Dict with keys: risk_score, risk_level, category, flags, suggestions,
            quality, original_text, suggested_text, cosine_component, keyword_component
        """
        self._ensure_corpus_embeddings()

        # 1. Compute clause embedding
        clause_embedding = _compute_embedding(text)

        # 2. Compute cosine similarity against each high-risk corpus entry
        similarities = np.array([
            _cosine_similarity(clause_embedding, corpus_emb)
            for corpus_emb in self._corpus_embeddings
        ])
        max_cosine = float(np.max(similarities))
        best_match_idx = int(np.argmax(similarities))

        # 3. Compute keyword penalties
        kw_penalty = _keyword_penalty(text)

        # 4. Calculate weighted risk score (60/40 formula)
        risk_score = round((0.6 * max_cosine) + (0.4 * kw_penalty), 4)
        risk_score = min(max(risk_score, 0.0), 1.0)

        # 5. Determine risk level
        if risk_score >= RISK_THRESHOLDS["high"]:
            risk_level = "high"
        elif risk_score >= RISK_THRESHOLDS["medium"]:
            risk_level = "medium"
        else:
            risk_level = "low"

        # 6. Detect category
        category = _detect_category(text)

        # 7. Build flags list from keyword matches
        flags = []
        text_lower = text.lower()
        for pattern in KEYWORD_PATTERNS:
            if pattern.lower() in text_lower:
                # Human-readable flag description
                flag_map = {
                    "unlimited liability": "Unlimited liability exposure",
                    "automatic renewal": "Auto-renewal without clear opt-out",
                    "no refund": "No refund policy",
                    "termination at any time": "Termination at any time",
                    "without notice": "Changes without advance notice",
                    "binding arbitration": "Forced binding arbitration",
                    "waiving rights": "Waiving legal rights",
                    "indemnif": "Broad indemnification clause",
                    "sole discretion": "Sole discretion clause",
                    "as-is": "As-is disclaimer",
                    "no warranty": "No warranty provision",
                    "non-compete": "Non-compete restriction",
                    "perpetual": "Perpetual obligation",
                    "irrevocable": "Irrevocable terms",
                    "hold harmless": "Hold harmless clause",
                    "at-will": "At-will termination",
                    "unilateral": "Unilateral amendment right",
                }
                flags.append(flag_map.get(pattern, f"Risk pattern: {pattern}"))

        # 8. Compute quality scores
        quality = _compute_quality_scores(text, flags, category)

        # 9. Generate suggestions
        suggestions = _generate_suggestions(text, category, flags, quality)

        # 10. Generate pros and cons
        pros, cons = _generate_pros_cons(text, category, quality)

        # 11. Generate suggested text
        suggested_text = _generate_suggested_text(text, category, flags)

        return {
            "original_text": text,
            "suggested_text": suggested_text,
            "original_preview": text,
            "suggested_preview": suggested_text,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "cosine_component": round(max_cosine, 4),
            "keyword_component": round(kw_penalty, 4),
            "category": category,
            "flags": flags,
            "suggestions": suggestions,
            "pros": pros,
            "cons": cons,
            "quality": quality,
            "compliance_matches": [],
        }


def split_into_clauses(text: str) -> List[str]:
    """
    Split document text into individual clause strings.

    Uses section numbering patterns, paragraph breaks, and line-by-line detection.
    """
    clauses = []

    # Try splitting by section numbering patterns (e.g., "1.", "Section 1.", "Article 1.")
    section_pattern = re.compile(
        r'(?:^|\n)\s*(?:Section\s+|Article\s+|Clause\s+)?\s*(\d+)\s*[\.\)]\s+',
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(section_pattern.finditer(text))

    if len(matches) >= 2:
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            clause = text[start:end].strip()
            if len(clause.split()) >= 3:
                clauses.append(clause)

    # Fallback: split by double newlines if section splitting failed
    if len(clauses) < 2:
        paragraphs = re.split(r'\n\s*\n', text.strip())
        clauses = [p.strip() for p in paragraphs if len(p.strip().split()) >= 3]

    # Final fallback: split by single newlines
    if len(clauses) < 2:
        lines = text.strip().split('\n')
        clauses = [l.strip() for l in lines if len(l.strip().split()) >= 3]

    return clauses if clauses else [text.strip()]
