import re
import math
import json
import numpy as np
from typing import Dict, List, Tuple, Any

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

RISK_THRESHOLDS = {"high": 0.55, "medium": 0.30, "low": 0.0}

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


def tokenize(text: str) -> List[str]:
    return re.findall(r'\b[a-z]{2,}\b', text.lower())

_tokenize = tokenize  # backward compat


def _compute_tf_vector(text: str, vocab: Dict[str, int]) -> np.ndarray:
    tokens = _tokenize(text)
    vec = np.zeros(len(vocab))
    for t in tokens:
        if t in vocab:
            vec[vocab[t]] += 1
    if np.sum(vec) > 0:
        vec = vec / np.sum(vec)
    return vec


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


_build_vocab_cache = None
_corpus_tf_cache = None


def _ensure_corpus():
    global _build_vocab_cache, _corpus_tf_cache
    if _build_vocab_cache is not None:
        return
    all_tokens = set()
    for text in HIGH_RISK_CORPUS:
        all_tokens.update(_tokenize(text))
    _build_vocab_cache = {t: i for i, t in enumerate(sorted(all_tokens))}
    _corpus_tf_cache = np.array([
        _compute_tf_vector(text, _build_vocab_cache) for text in HIGH_RISK_CORPUS
    ])


def _compute_tf_similarity(text: str) -> Tuple[float, int]:
    _ensure_corpus()
    vec = _compute_tf_vector(text, _build_vocab_cache)
    similarities = np.array([_cosine_similarity(vec, cv) for cv in _corpus_tf_cache])
    max_sim = float(np.max(similarities)) if len(similarities) > 0 else 0.0
    best_idx = int(np.argmax(similarities)) if len(similarities) > 0 else 0
    return max_sim, best_idx


def _combine_max_similarity(text: str) -> float:
    sim, _ = _compute_tf_similarity(text)
    return sim


def _keyword_penalty(text: str) -> float:
    text_lower = text.lower()
    penalty = 0.0
    for pattern, weight in KEYWORD_PATTERNS.items():
        if pattern.lower() in text_lower:
            penalty += weight
    return min(penalty, 1.0)


def _detect_category(text: str) -> str:
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
    word_count = len(text.split())
    clarity_score = 0
    if word_count < 10:
        clarity_score = -2
    elif word_count < 20:
        clarity_score = -1
    elif 20 <= word_count <= 60:
        clarity_score = 1
    else:
        clarity_score = 0

    balance_score = 0
    one_sided_patterns = ["provider shall", "client shall", "party shall", "shall not", "must not", "will not"]
    one_sided_count = sum(1 for p in one_sided_patterns if p.lower() in text.lower())
    if one_sided_count >= 3:
        balance_score = -1
    elif one_sided_count <= 1:
        balance_score = 1

    enforceability_score = 0
    enforceable_terms = ["shall", "pursuant to", "notwithstanding", "hereinafter", "whereas", "in the event", "governing law", "severability", "entire agreement"]
    enforce_count = sum(1 for t in enforceable_terms if t.lower() in text.lower())
    if enforce_count >= 3:
        enforceability_score = 1
    elif enforce_count >= 1:
        enforceability_score = 0
    else:
        enforceability_score = -1

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

    return {
        "clarity_score": clarity_score,
        "balance_score": balance_score,
        "enforceability_score": enforceability_score,
        "issues": ". ".join(issues),
        "strengths": ". ".join(strengths),
    }


def _generate_suggestions(text: str, category: str, flags: List[str], quality: Dict[str, Any]) -> List[str]:
    suggestions = []
    text_lower = text.lower()
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
    return suggestions


def _generate_pros_cons(text: str, category: str, quality: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    pros = []
    cons = []
    if quality["strengths"]:
        pros.extend([s.strip() for s in quality["strengths"].split(".") if s.strip()])
    if quality["issues"]:
        cons.extend([c.strip() for c in quality["issues"].split(".") if c.strip()])
    text_lower = text.lower()
    if category == "termination":
        if "mutual" in text_lower or "either party" in text_lower:
            pros.append("Obligations are mutual.")
        if "at any time" in text_lower:
            cons.append("Allows termination without cause or notice.")
    elif category == "liability":
        if "unlimited" in text_lower:
            cons.append("Exposes party to unlimited financial liability.")
        if "cap" in text_lower or "limit" in text_lower:
            pros.append("Liability is capped.")
    elif category == "dispute":
        if "arbitration" in text_lower:
            cons.append("Removes right to jury trial.")
    if not pros:
        pros.append("No strongly protective provisions detected.")
    if not cons:
        cons.append("No significant risk indicators found.")
    pros = list(dict.fromkeys(pros))
    cons = list(dict.fromkeys(cons))
    return pros, cons


def _generate_suggested_text(original: str, category: str, flags: List[str]) -> str:
    suggested = original
    original_lower = original.lower()
    if "unlimited liability" in original_lower:
        suggested = suggested.replace("unlimited liability", "liability capped at total fees paid")
        suggested = suggested.replace("Unlimited Liability", "Liability Capped at Total Fees Paid")
    if "automatic renewal" in original_lower and "notice" not in original_lower:
        suggested = suggested.replace("automatic renewal", "renewal with opt-out (30-day notice required)")
        suggested = suggested.replace("Automatic Renewal", "Renewal with Opt-Out (30-Day Notice Required)")
    if "no refund" in original_lower:
        suggested = suggested.replace("No refunds", "Pro-rata refund for unused period")
        suggested = suggested.replace("no refunds", "pro-rata refund for unused period")
    if "terminate at any time" in original_lower and "notice" not in original_lower:
        suggested = suggested.replace("terminate at any time without notice", "terminate at any time with at least 30 days prior written notice")
    if "binding arbitration" in original_lower and "appeal" not in original_lower:
        suggested = suggested.rstrip(".") + " with appeal rights and cost-sharing provisions."
    return suggested


def split_into_clauses(text: str) -> List[str]:
    clauses = []
    section_pattern = re.compile(r'(?:^|\n)\s*(?:Section\s+|Article\s+|Clause\s+)?\s*(\d+)\s*[\.\)]\s+', re.IGNORECASE | re.MULTILINE)
    matches = list(section_pattern.finditer(text))
    if len(matches) >= 2:
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            clause = text[start:end].strip()
            if len(clause.split()) >= 3:
                clauses.append(clause)
    if len(clauses) < 2:
        paragraphs = re.split(r'\n\s*\n', text.strip())
        clauses = [p.strip() for p in paragraphs if len(p.strip().split()) >= 3]
    if len(clauses) < 2:
        lines = text.strip().split('\n')
        clauses = [l.strip() for l in lines if len(l.strip().split()) >= 3]
    return clauses if clauses else [text.strip()]


def score_clause(text: str) -> Dict[str, Any]:
    max_sim = _combine_max_similarity(text)
    kw_penalty = _keyword_penalty(text)
    risk_score = round((0.6 * max_sim) + (0.4 * kw_penalty), 4)
    risk_score = min(max(risk_score, 0.0), 1.0)

    if risk_score >= RISK_THRESHOLDS["high"]:
        risk_level = "high"
    elif risk_score >= RISK_THRESHOLDS["medium"]:
        risk_level = "medium"
    else:
        risk_level = "low"

    category = _detect_category(text)

    flags = []
    text_lower = text.lower()
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
    for pattern, readable in flag_map.items():
        if pattern.lower() in text_lower:
            flags.append(readable)

    quality = _compute_quality_scores(text, flags, category)
    suggestions = _generate_suggestions(text, category, flags, quality)
    pros, cons = _generate_pros_cons(text, category, quality)
    suggested_text = _generate_suggested_text(text, category, flags)

    return {
        "original_text": text,
        "suggested_text": suggested_text,
        "original_preview": text,
        "suggested_preview": suggested_text,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "cosine_component": round(max_sim, 4),
        "keyword_component": round(kw_penalty, 4),
        "category": category,
        "flags": flags,
        "suggestions": suggestions,
        "pros": pros,
        "cons": cons,
        "quality": quality,
        "compliance_matches": [],
    }
