import os
import chromadb
from typing import List, Dict, Any


# --- Regulatory Guidelines Seed Data ---
# These represent core industry compliance requirements that clause analysis
# should be matched against for regulatory relevance scoring.

SEED_GUIDELINES = [
    {
        "id": "gdpr_notification_33",
        "text": (
            "GDPR Article 33 requires notification to the supervisory authority "
            "within 72 hours of becoming aware of a personal data breach, unless the "
            "breach is unlikely to result in a risk to the rights and freedoms of natural persons."
        ),
        "metadata": {"regulation": "GDPR", "article": "33", "topic": "breach_notification"},
    },
    {
        "id": "gdpr_consent_7",
        "text": (
            "GDPR Article 7 outlines conditions for consent: it must be freely given, "
            "specific, informed, and unambiguous. The data controller must be able to "
            "demonstrate that consent was given."
        ),
        "metadata": {"regulation": "GDPR", "article": "7", "topic": "consent"},
    },
    {
        "id": "ccpa_right_delete_1798",
        "text": (
            "CCPA Section 1798.105 grants consumers the right to request deletion of "
            "personal information collected by a business. The business must comply within "
            "45 days and notify service providers."
        ),
        "metadata": {"regulation": "CCPA", "section": "1798.105", "topic": "right_to_delete"},
    },
    {
        "id": "hipaa_breach_164_408",
        "text": (
            "HIPAA 45 CFR 164.408 requires covered entities to notify affected individuals "
            "within 60 days of discovering a breach of unsecured protected health information "
            "affecting 500 or more individuals."
        ),
        "metadata": {"regulation": "HIPAA", "section": "45 CFR 164.408", "topic": "breach_notification"},
    },
    {
        "id": "sox_certification_302",
        "text": (
            "SOX Section 302 requires the CEO and CFO to certify the accuracy and "
            "completeness of financial reports. Officers must attest that reports contain "
            "no material misstatements or omissions."
        ),
        "metadata": {"regulation": "SOX", "section": "302", "topic": "certification"},
    },
]


class VectorStore:
    """
    ChromaDB-backed vector store for compliance guideline matching.

    Provides persistent local storage with automatic seeding of regulatory
    guidelines on first initialization.
    """

    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            persist_directory = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

        os.makedirs(persist_directory, exist_ok=True)

        self._client = chromadb.PersistentClient(path=persist_directory)
        self._collection = self._client.get_or_create_collection(
            name="compliance_guidelines",
            metadata={"hnsw:space": "cosine"},
        )
        self._ensure_seeded()

    def _ensure_seeded(self):
        """Seed the collection with regulatory guidelines if empty."""
        if self._collection.count() == 0:
            ids = [g["id"] for g in SEED_GUIDELINES]
            documents = [g["text"] for g in SEED_GUIDELINES]
            metadatas = [g["metadata"] for g in SEED_GUIDELINES]
            self._collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

    def query(self, text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Query the vector store for the most relevant compliance guidelines.

        Args:
            text: The clause text to match against.
            n_results: Maximum number of results to return.

        Returns:
            List of dicts with keys: id, text, metadata, relevance_score
        """
        if self._collection.count() == 0:
            return []

        results = self._collection.query(
            query_texts=[text],
            n_results=min(n_results, self._collection.count()),
        )

        matches = []
        for i in range(len(results["ids"][0])):
            match = {
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "relevance_score": round(results["distances"][0][i], 4) if results["distances"] else 0.0,
            }
            matches.append(match)

        return matches

    def get_all_guidelines(self) -> List[Dict[str, Any]]:
        """Retrieve all stored guidelines."""
        if self._collection.count() == 0:
            return []
        all_data = self._collection.get()
        return [
            {
                "id": all_data["ids"][i],
                "text": all_data["documents"][i],
                "metadata": all_data["metadatas"][i] if all_data["metadatas"] else {},
            }
            for i in range(len(all_data["ids"]))
        ]


# Singleton instance
_vector_store = None


def get_vector_store() -> VectorStore:
    """Get or create the singleton VectorStore instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
