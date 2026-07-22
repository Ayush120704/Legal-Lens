import os
import chromadb
from typing import List, Dict, Any

SEED_GUIDELINES = [
    # GDPR
    {"id": "gdpr_breach_33", "text": "GDPR Article 33 requires notification to the supervisory authority within 72 hours of becoming aware of a personal data breach, unless the breach is unlikely to result in a risk to the rights and freedoms of natural persons.", "metadata": {"regulation": "GDPR", "article": "33", "topic": "breach_notification"}},
    {"id": "gdpr_consent_7", "text": "GDPR Article 7 outlines conditions for consent: it must be freely given, specific, informed, and unambiguous. The data controller must be able to demonstrate that consent was given.", "metadata": {"regulation": "GDPR", "article": "7", "topic": "consent"}},
    {"id": "gdpr_dpor_37", "text": "GDPR Article 37 requires designation of a Data Protection Officer (DPO) for public authorities, organizations engaging in large-scale systematic monitoring, or large-scale processing of special categories of data.", "metadata": {"regulation": "GDPR", "article": "37", "topic": "dpo"}},
    {"id": "gdpr_data_portability_20", "text": "GDPR Article 20 grants data subjects the right to receive their personal data in a structured, commonly used, machine-readable format and the right to transmit that data to another controller.", "metadata": {"regulation": "GDPR", "article": "20", "topic": "data_portability"}},
    {"id": "gdpr_right_erasure_17", "text": "GDPR Article 17 provides the right to erasure ('right to be forgotten'), allowing data subjects to request deletion of personal data without undue delay under specified conditions.", "metadata": {"regulation": "GDPR", "article": "17", "topic": "right_to_erasure"}},
    {"id": "gdpr_dpia_35", "text": "GDPR Article 35 requires data controllers to carry out a Data Protection Impact Assessment (DPIA) for processing that is likely to result in high risk to individuals' rights and freedoms.", "metadata": {"regulation": "GDPR", "article": "35", "topic": "dpia"}},

    # CCPA
    {"id": "ccpa_right_delete_1798", "text": "CCPA Section 1798.105 grants consumers the right to request deletion of personal information collected by a business. The business must comply within 45 days and notify service providers.", "metadata": {"regulation": "CCPA", "section": "1798.105", "topic": "right_to_delete"}},
    {"id": "ccpa_right_know_1798_100", "text": "CCPA Section 1798.100 grants consumers the right to know what personal information is being collected, used, shared, or sold by a business, including categories of sources and purposes.", "metadata": {"regulation": "CCPA", "section": "1798.100", "topic": "right_to_know"}},
    {"id": "ccpa_opt_out_1798_120", "text": "CCPA Section 1798.120 grants consumers the right to opt-out of the sale of their personal information to third parties. Businesses must provide a clear 'Do Not Sell My Personal Information' link.", "metadata": {"regulation": "CCPA", "section": "1798.120", "topic": "opt_out"}},
    {"id": "ccpa_non_discrimination_1798_125", "text": "CCPA Section 1798.125 prohibits businesses from discriminating against consumers who exercise their CCPA rights, including denying services, charging different prices, or providing different quality.", "metadata": {"regulation": "CCPA", "section": "1798.125", "topic": "non_discrimination"}},

    # HIPAA
    {"id": "hipaa_breach_164_408", "text": "HIPAA 45 CFR 164.408 requires covered entities to notify affected individuals within 60 days of discovering a breach of unsecured protected health information affecting 500 or more individuals.", "metadata": {"regulation": "HIPAA", "section": "45 CFR 164.408", "topic": "breach_notification"}},
    {"id": "hipaa_privacy_164_502", "text": "HIPAA 45 CFR 164.502 establishes permitted uses and disclosures of protected health information (PHI), requiring patient authorization except for treatment, payment, or healthcare operations.", "metadata": {"regulation": "HIPAA", "section": "45 CFR 164.502", "topic": "privacy_rule"}},
    {"id": "hipaa_security_164_312", "text": "HIPAA 45 CFR 164.312 requires technical safeguards including access controls, audit controls, integrity controls, person or entity authentication, and transmission security for electronic PHI.", "metadata": {"regulation": "HIPAA", "section": "45 CFR 164.312", "topic": "security_safeguards"}},
    {"id": "hipaa_business_associate_164_504", "text": "HIPAA 45 CFR 164.504 requires covered entities to have written business associate agreements that mandate appropriate safeguards for PHI and limit use and disclosure.", "metadata": {"regulation": "HIPAA", "section": "45 CFR 164.504", "topic": "business_associate"}},

    # SOX
    {"id": "sox_certification_302", "text": "SOX Section 302 requires the CEO and CFO to certify the accuracy and completeness of financial reports. Officers must attest that reports contain no material misstatements or omissions.", "metadata": {"regulation": "SOX", "section": "302", "topic": "certification"}},
    {"id": "sox_internal_controls_404", "text": "SOX Section 404 requires management to assess and report on the effectiveness of internal controls over financial reporting, with auditors attesting to that assessment.", "metadata": {"regulation": "SOX", "section": "404", "topic": "internal_controls"}},
    {"id": "sox_whistleblower_806", "text": "SOX Section 806 provides whistleblower protections for employees of publicly traded companies who report fraudulent activities that could harm shareholders.", "metadata": {"regulation": "SOX", "section": "806", "topic": "whistleblower"}},

    # ISO 27001
    {"id": "iso27001_risk_assessment", "text": "ISO 27001 requires organizations to establish an information security risk assessment process that identifies risks, analyzes risk likelihood and impact, and evaluates risk treatment options.", "metadata": {"regulation": "ISO 27001", "clause": "6.1", "topic": "risk_assessment"}},
    {"id": "iso27001_access_control", "text": "ISO 27001 Annex A.9 requires access control policies including user access management, user responsibilities, and system and application access control.", "metadata": {"regulation": "ISO 27001", "clause": "A.9", "topic": "access_control"}},
    {"id": "iso27001_incident_response", "text": "ISO 27001 Annex A.16 requires organizations to establish incident management responsibilities, procedures for reporting, and response to information security incidents.", "metadata": {"regulation": "ISO 27001", "clause": "A.16", "topic": "incident_response"}},

    # US State Privacy Laws
    {"id": "virginia_cdpa", "text": "Virginia Consumer Data Protection Act (CDPA) grants consumers rights to access, correct, delete, and port personal data. Requires data protection assessments for processing activities involving targeted advertising or sensitive data.", "metadata": {"regulation": "VCDPA", "topic": "consumer_rights"}},
    {"id": "colorado_privacy_act", "text": "Colorado Privacy Act (CPA) grants consumers rights to access, correct, delete, and port personal data. Requires universal opt-out mechanisms and data protection assessments.", "metadata": {"regulation": "CPA", "topic": "consumer_rights"}},
    {"id": "connecticut_data_privacy", "text": "Connecticut Data Privacy Act (CTDPA) grants consumers rights to access, correct, delete, and obtain a copy of personal data. Applies to entities processing data of over 100,000 consumers.", "metadata": {"regulation": "CTDPA", "topic": "consumer_rights"}},

    # LGPD (Brazil)
    {"id": "lgpd_consent", "text": "Brazilian LGPD Article 7 requires consent for data processing. Consent must be provided in writing or by electronic means and must be specific and unambiguous.", "metadata": {"regulation": "LGPD", "article": "7", "topic": "consent"}},
    {"id": "lgpd_rights", "text": "Brazilian LGPD Articles 17-22 grant data subjects rights including confirmation of processing existence, access, correction, anonymization, portability, and deletion of personal data.", "metadata": {"regulation": "LGPD", "article": "17-22", "topic": "data_subject_rights"}},

    # PIPEDA (Canada)
    {"id": "pipeda_consent", "text": "PIPEDA Principle 3 requires meaningful consent for collection, use, and disclosure of personal information. Organizations must inform individuals of the purposes for data collection.", "metadata": {"regulation": "PIPEDA", "principle": "3", "topic": "consent"}},
    {"id": "pipeda_safeguards", "text": "PIPEDA Principle 7 requires organizations to protect personal information with security safeguards appropriate to the sensitivity of the information.", "metadata": {"regulation": "PIPEDA", "principle": "7", "topic": "safeguards"}},

    # UK GDPR
    {"id": "uk_gdpr_transfers", "text": "UK GDPR Article 45-49 governs international data transfers, requiring adequate levels of protection through adequacy decisions, standard contractual clauses, or binding corporate rules.", "metadata": {"regulation": "UK GDPR", "articles": "45-49", "topic": "data_transfers"}},

    # Financial Regulations
    {"id": "miFID2_compliance", "text": "MiFID II requires investment firms to act honestly, fairly, and professionally, with enhanced disclosure requirements and suitability assessments for clients.", "metadata": {"regulation": "MiFID II", "topic": "investor_protection"}},
    {"id": "aml_directive", "text": "EU Anti-Money Laundering Directive (AMLD) requires customer due diligence, beneficial ownership registers, and reporting of suspicious transactions to financial intelligence units.", "metadata": {"regulation": "AMLD", "topic": "anti_money_laundering"}},

    # Contract Law Principles
    {"id": "ucc_implied_warranty", "text": "UCC 2-314 implies a warranty of merchantability in sales of goods, requiring goods to be fit for ordinary purposes. This warranty can be disclaimed but must be conspicuous.", "metadata": {"regulation": "UCC", "section": "2-314", "topic": "implied_warranty"}},
    {"id": "ucc_unconscionability", "text": "UCC 2-302 allows courts to refuse enforcement of unconscionable contract clauses, protecting parties from oppressive terms or surprise terms in standard form contracts.", "metadata": {"regulation": "UCC", "section": "2-302", "topic": "unconscionability"}},
    {"id": "ucc_merchantability", "text": "UCC 2-314 implies warranty of merchantability in sales contracts unless disclaimed conspicuously in writing. Goods must be fit for ordinary purposes.", "metadata": {"regulation": "UCC", "section": "2-314", "topic": "warranty"}},
    {"id": "statute_of_frauds", "text": "Statute of Frauds requires certain contracts to be in writing and signed by the party to be charged, including contracts for sale of land, contracts lasting over one year, and suretyship agreements.", "metadata": {"regulation": "Common Law", "topic": "statute_of_frauds"}},

    # Employment Law
    {"id": "at_will_employment", "text": "At-will employment allows either party to terminate employment at any time for any lawful reason. Exceptions include public policy, implied contracts, and good faith covenants.", "metadata": {"regulation": "Employment Law", "topic": "at_will_employment"}},
    {"id": "non_compete_reasonableness", "text": "Non-compete agreements must be reasonable in geographic scope, duration, and business purpose to be enforceable. Many states require consideration beyond continued employment.", "metadata": {"regulation": "Employment Law", "topic": "non_compete"}},

    # Intellectual Property
    {"id": "copyright_ownership", "text": "Copyright law provides that works created within the scope of employment are owned by the employer (work made for hire). Independent contractor works require written assignment.", "metadata": {"regulation": "Copyright Law", "topic": "ownership"}},
    {"id": "patent_ownership", "text": "Patent ownership vests in the inventor unless there is a written agreement assigning rights. Employers typically require invention assignment agreements for employees.", "metadata": {"regulation": "Patent Law", "topic": "ownership"}},
]


class VectorStore:
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
        if self._collection.count() == 0:
            ids = [g["id"] for g in SEED_GUIDELINES]
            documents = [g["text"] for g in SEED_GUIDELINES]
            metadatas = [g["metadata"] for g in SEED_GUIDELINES]
            self._collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def query(self, text: str, n_results: int = 3) -> List[Dict[str, Any]]:
        if self._collection.count() == 0:
            return []
        results = self._collection.query(
            query_texts=[text],
            n_results=min(n_results, self._collection.count()),
        )
        matches = []
        for i in range(len(results["ids"][0])):
            matches.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "relevance_score": round(1 - results["distances"][0][i], 4) if results["distances"] else 0.0,
            })
        return matches

    def get_all_guidelines(self) -> List[Dict[str, Any]]:
        if self._collection.count() == 0:
            return []
        all_data = self._collection.get()
        return [{"id": all_data["ids"][i], "text": all_data["documents"][i], "metadata": all_data["metadatas"][i] if all_data["metadatas"] else {}} for i in range(len(all_data["ids"]))]

    def add_guideline(self, gid: str, text: str, metadata: dict = None):
        self._collection.add(ids=[gid], documents=[text], metadatas=[metadata or {}])

    def get_count(self) -> int:
        return self._collection.count()


_vector_store = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
