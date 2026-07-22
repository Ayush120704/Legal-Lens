import json
import re
from typing import Optional, List, Dict, Any
from config import settings


class LLMService:
    def __init__(self):
        self._client = None
        self._initialized = False

    def _ensure_client(self):
        if not self._initialized:
            if settings.OPENAI_API_KEY:
                try:
                    from openai import OpenAI
                    self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
                except Exception:
                    self._client = None
            self._initialized = True

    @property
    def available(self) -> bool:
        self._ensure_client()
        return self._client is not None and bool(settings.OPENAI_API_KEY)

    def _call_llm(self, system_prompt: str, user_prompt: str, max_tokens: int = 1024, temperature: float = 0.3) -> Optional[str]:
        if not self.available:
            return None
        try:
            response = self._client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return None

    def enhance_clause_analysis(self, clause_text: str, risk_level: str, risk_score: float, category: str) -> Optional[Dict[str, Any]]:
        if not self.available:
            return None
        system_prompt = """You are a legal AI assistant. Analyze the given clause and return JSON with:
- "suggested_text": improved version of the clause that reduces legal risk
- "legal_analysis": brief explanation of why the original is risky (1-2 sentences)
- "negotiation_tips": 2-3 actionable negotiation points
- "legal_risk_details": specific legal risks (e.g., "Could be unenforceable under UCC 2-302")
- "jurisdiction_notes": relevant jurisdiction considerations if any
Return ONLY valid JSON, no markdown."""
        user_prompt = f"""Clause: "{clause_text}"
Risk Level: {risk_level}
Risk Score: {risk_score}
Category: {category}"""
        result = self._call_llm(system_prompt, user_prompt, max_tokens=1500)
        if not result:
            return None
        result_clean = re.sub(r'^```(?:json)?\s*|\s*```$', '', result, flags=re.DOTALL).strip()
        try:
            return json.loads(result_clean)
        except json.JSONDecodeError:
            return {"raw_response": result}

    def generate_document_summary(self, clauses_analysis: str) -> Optional[str]:
        if not self.available:
            return None
        system_prompt = "You are a legal document analyst. Summarize the key risks, strengths, and recommendations based on the clause-by-clause analysis provided."
        user_prompt = f"Here is the clause-by-clause analysis:\n\n{clauses_analysis}\n\nProvide a concise executive summary with key risks (bullet points), strengths (bullet points), and top 3 recommendations."
        return self._call_llm(system_prompt, user_prompt, max_tokens=1000, temperature=0.4)

    def answer_question(self, document_text: str, clauses_analysis: str, question: str) -> Optional[str]:
        if not self.available:
            return None
        system_prompt = "You are a legal document Q&A assistant. Answer the user's question based on the document text and analysis provided. Be concise, accurate, and cite specific clauses where relevant."
        user_prompt = f"""DOCUMENT TEXT:
{document_text[:8000]}

CLAUSE-LEVEL ANALYSIS:
{clauses_analysis[:4000]}

USER QUESTION: {question}

Answer based on the document content above. If the answer cannot be determined from the document, say so."""
        return self._call_llm(system_prompt, user_prompt, max_tokens=1500, temperature=0.3)

    def compare_clauses(self, clause_a: str, clause_b: str) -> Optional[str]:
        if not self.available:
            return None
        system_prompt = "You are a legal document comparison expert. Compare the two clauses and identify key differences, risks, and which version is more favorable and why."
        user_prompt = f"""CLAUSE A:
{clause_a}

CLAUSE B:
{clause_b}

Compare these clauses. Identify:
1. Key differences
2. Which is more favorable and why
3. Specific risk implications of each version"""
        return self._call_llm(system_prompt, user_prompt, max_tokens=1000, temperature=0.3)

    def detect_language(self, text: str) -> str:
        from langdetect import detect, LangDetectException
        try:
            return detect(text)
        except LangDetectException:
            return "en"


llm_service = LLMService()
