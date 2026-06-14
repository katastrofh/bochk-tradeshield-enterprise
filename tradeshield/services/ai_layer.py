"""Visible AI layer for TradeShield V7.

This is a local, deterministic AI-workflow prototype:
- no external API calls
- no customer data leaves the app
- outputs are explainable and audit-friendly
- production version should be trained/validated on BOCHK historical cases
"""

from __future__ import annotations

import json
from typing import Any


def _get(obj: Any, name: str, default: Any = None) -> Any:
    return getattr(obj, name, default)


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def document_ai_extract(case, documents: list) -> dict:
    required = [
        "invoice_no",
        "buyer",
        "supplier",
        "amount",
        "currency",
        "goods",
        "due_date",
    ]

    extracted: dict[str, Any] = {}
    evidence_rows = []
    flags = []

    for doc in documents:
        fields = _as_dict(_get(doc, "extracted_fields", {}))
        doc_flags = _as_list(_get(doc, "consistency_flags", []))

        for key, value in fields.items():
            if value not in [None, ""]:
                extracted.setdefault(key, value)

        flags.extend(doc_flags)

        field_count = len([v for v in fields.values() if v not in [None, ""]])
        confidence = min(0.98, 0.58 + field_count * 0.055 - len(doc_flags) * 0.08)

        evidence_rows.append(
            {
                "filename": _get(doc, "filename", "unknown"),
                "doc_type": _get(doc, "doc_type", "UNKNOWN"),
                "fields_found": sorted(fields.keys()),
                "consistency_flags": doc_flags,
                "document_confidence": round(max(0.25, confidence), 2),
                "evidence_hash": _get(doc, "file_hash", None),
            }
        )

    missing = [field for field in required if field not in extracted]
    base = 0.92 if documents else 0.38
    overall_confidence = base - len(missing) * 0.045 - len(flags) * 0.07
    overall_confidence = round(max(0.15, min(0.98, overall_confidence)), 2)

    discrepancies = []
    if flags:
        discrepancies.extend(flags)
    if missing:
        discrepancies.append("Missing fields: " + ", ".join(missing))
    if _get(case, "supplier_bank_account") != _get(case, "previous_supplier_bank_account") and _get(case, "previous_supplier_bank_account"):
        discrepancies.append("Beneficiary bank account changed from previous known account.")

    return {
        "ai_module": "Document AI Extractor",
        "ai_mode": "local deterministic prototype",
        "case_ref": _get(case, "case_ref", "UNKNOWN"),
        "overall_confidence": overall_confidence,
        "extracted_fields": extracted,
        "missing_fields": missing,
        "discrepancies": discrepancies,
        "field_confidence": {
            field: round(0.86 if field in extracted else 0.34, 2)
            for field in required
        },
        "evidence": evidence_rows,
        "human_review_required": bool(discrepancies or overall_confidence < 0.75),
    }


def risk_ai_explanation(case, risk, documents: list, fraud_graph: dict) -> dict:
    score = _get(risk, "overall_score", 50) if risk else 50
    category = _get(risk, "category", "UNSCORED") if risk else "UNSCORED"

    reason_codes = []

    amount = _get(case, "requested_financing_hkd", 0) or 0
    term = _get(case, "payment_term_days", 0) or 0

    if amount >= 750000:
        reason_codes.append(
            {
                "code": "LARGE_EXPOSURE",
                "weight": 0.21,
                "reason": "Requested financing is high for SME trade-finance workflow.",
            }
        )
    if term >= 75:
        reason_codes.append(
            {
                "code": "LONG_PAYMENT_TERM",
                "weight": 0.18,
                "reason": "Longer payment term increases repayment and collection uncertainty.",
            }
        )
    if not _get(case, "supplier_verified", False):
        reason_codes.append(
            {
                "code": "SUPPLIER_NOT_VERIFIED",
                "weight": 0.20,
                "reason": "Supplier beneficiary account is not yet verified.",
            }
        )
    if _get(case, "supplier_bank_account") != _get(case, "previous_supplier_bank_account") and _get(case, "previous_supplier_bank_account"):
        reason_codes.append(
            {
                "code": "BENEFICIARY_ACCOUNT_CHANGE",
                "weight": 0.24,
                "reason": "Beneficiary account changed compared with previous supplier history.",
            }
        )

    indicators = fraud_graph.get("indicators", []) if isinstance(fraud_graph, dict) else []
    if indicators:
        reason_codes.append(
            {
                "code": "FRAUD_GRAPH_SIGNAL",
                "weight": 0.30,
                "reason": f"{len(indicators)} fraud-network indicator(s) detected.",
            }
        )

    if not documents:
        reason_codes.append(
            {
                "code": "NO_DOCUMENT_EVIDENCE",
                "weight": 0.22,
                "reason": "No uploaded document evidence is attached to the case.",
            }
        )

    pd_pct = min(38.0, round(1.5 + score * 0.23, 2))
    fraud_pct = min(55.0, round(2.0 + score * 0.20 + len(indicators) * 4.5, 2))

    return {
        "ai_module": "Explainable Risk AI",
        "ai_mode": "synthetic model-style scoring for prototype",
        "case_ref": _get(case, "case_ref", "UNKNOWN"),
        "risk_score": score,
        "risk_category": category,
        "estimated_default_probability_pct": pd_pct,
        "estimated_fraud_probability_pct": fraud_pct,
        "reason_codes": reason_codes,
        "plain_english_explanation": (
            f"The case is classified as {category}. The strongest signals are: "
            + "; ".join([r["code"] for r in reason_codes[:4]])
            if reason_codes
            else "The case has no major detected risk signals yet, but still requires human review."
        ),
        "model_governance": {
            "training_status": "synthetic demonstration only",
            "production_requirement": "train and validate on BOCHK historical outcomes, fraud labels, repayment data, and document-review decisions",
            "human_in_the_loop": True,
            "autonomous_lending": False,
        },
    }


def genai_credit_memo(case, risk, document_ai: dict, risk_ai: dict) -> dict:
    recommended = _get(risk, "recommended_amount_hkd", None) if risk else None
    if recommended is None:
        requested = _get(case, "requested_financing_hkd", 0) or 0
        recommended = round(requested * 0.55, 2)

    blockers = []
    if document_ai.get("human_review_required"):
        blockers.append("Resolve document discrepancies or missing extracted fields.")
    if not _get(case, "supplier_verified", False):
        blockers.append("Verify beneficiary bank account before settlement.")
    if not _get(case, "shipment_verified", False):
        blockers.append("Verify shipment evidence before fund release.")

    return {
        "ai_module": "GenAI Credit Memo Composer",
        "ai_mode": "local template-grounded generation; external LLM optional in production",
        "case_ref": _get(case, "case_ref", "UNKNOWN"),
        "title": f"Credit Memo — {_get(case, 'case_ref', 'UNKNOWN')}",
        "proposed_decision": "ESCALATE" if blockers else "CONDITIONAL_APPROVE",
        "recommended_limit_hkd": recommended,
        "executive_summary": (
            f"{_get(case, 'sme_name', 'The SME')} requests HK${_get(case, 'requested_financing_hkd', 0):,.0f} "
            f"for {_get(case, 'goods_description', 'trade goods')} from Hong Kong to {_get(case, 'destination_country', 'destination market')}. "
            f"The AI risk view is {risk_ai.get('risk_category')} with score {risk_ai.get('risk_score')}."
        ),
        "conditions_precedent": blockers or [
            "Maintain standard KYC and trade-document checks.",
            "Release only after final settlement checklist is complete.",
        ],
        "banker_questions": [
            "Can the SME provide latest purchase order and shipping confirmation?",
            "Has the beneficiary bank account been used in prior clean transactions?",
            "Is the buyer relationship recurring or first-time?",
            "Are there adverse-media or sanctions concerns for related entities?",
        ],
        "committee_ready_summary": [
            "AI output is decision support, not autonomous approval.",
            "Risk reasons are exposed as reason codes.",
            "Evidence is hash-linked for auditability.",
            "Human officer remains final decision owner.",
        ],
    }


def ask_case_ai(case, risk, document_ai: dict, risk_ai: dict, question: str) -> dict:
    q = question.lower().strip()

    if any(word in q for word in ["document", "invoice", "missing", "evidence"]):
        answer = (
            f"Document AI confidence is {document_ai.get('overall_confidence')}. "
            f"Missing fields: {', '.join(document_ai.get('missing_fields') or ['none'])}. "
            f"Discrepancies: {', '.join(document_ai.get('discrepancies') or ['none'])}."
        )
    elif any(word in q for word in ["risk", "risky", "why", "score"]):
        answer = risk_ai.get("plain_english_explanation")
    elif any(word in q for word in ["approve", "decision", "limit"]):
        answer = (
            "The system should not auto-approve. It can recommend a limit, but final approval must remain with "
            "an officer or risk manager. Check document discrepancies, fraud graph signals, and settlement gates first."
        )
    elif any(word in q for word in ["settlement", "release", "payment"]):
        answer = (
            "Settlement should be blocked until supplier verification and shipment verification are complete. "
            "The tool supports conditional release only after these controls pass."
        )
    else:
        answer = (
            f"For case {_get(case, 'case_ref', 'UNKNOWN')}, review the Risk Passport, Document AI discrepancies, "
            "fraud graph, and recommended conditions before making a human decision."
        )

    return {
        "ai_module": "Ask-the-Case AI",
        "question": question,
        "answer": answer,
        "grounding_sources": [
            "case fields",
            "document AI extraction",
            "risk AI explanation",
            "fraud graph",
            "human-in-the-loop policy",
        ],
        "disclaimer": "Prototype answer. Not autonomous lending advice.",
    }
