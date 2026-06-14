"""Grounded LLM workflows for TradeShield cases."""

from __future__ import annotations

from tradeshield.fraud_graph import build_fraud_graph
from tradeshield.services.compliance import compliance_checklist
from tradeshield.services.counterparty import counterparty_dossier
from tradeshield.services.evidence import evidence_bundle
from tradeshield.services.llm_client import (
    LLMUnavailable,
    build_case_prompt,
    build_trade_finance_system_prompt,
    ollama_chat,
)


def make_case_pack(db, case, risk, documents: list, audits: list | None = None) -> dict:
    graph = build_fraud_graph(db, case)
    audits = audits or []

    return {
        "case": {
            "id": case.id,
            "case_ref": case.case_ref,
            "sme_name": case.sme_name,
            "buyer_name": case.buyer_name,
            "supplier_name": case.supplier_name,
            "origin_country": case.origin_country,
            "destination_country": case.destination_country,
            "goods_description": case.goods_description,
            "invoice_amount_hkd": case.invoice_amount_hkd,
            "requested_financing_hkd": case.requested_financing_hkd,
            "payment_term_days": case.payment_term_days,
            "supplier_bank_account": case.supplier_bank_account,
            "previous_supplier_bank_account": case.previous_supplier_bank_account,
            "supplier_verified": case.supplier_verified,
            "shipment_verified": case.shipment_verified,
            "shipment_status": case.shipment_status,
            "esg_status": case.esg_status,
            "settlement_status": case.settlement_status,
            "status": case.status,
            "decision": case.decision,
            "approved_amount_hkd": case.approved_amount_hkd,
        },
        "latest_risk": None if not risk else {
            "model_version": risk.model_version,
            "overall_score": risk.overall_score,
            "category": risk.category,
            "recommendation": risk.recommendation,
            "recommended_amount_hkd": risk.recommended_amount_hkd,
            "required_actions": risk.required_actions,
            "risk_drivers": risk.risk_drivers,
            "mitigating_factors": risk.mitigating_factors,
            "fraud_indicators": risk.fraud_indicators,
            "narrative": risk.narrative,
        },
        "documents": [
            {
                "filename": d.filename,
                "doc_type": d.doc_type,
                "file_hash": d.file_hash,
                "extracted_fields": d.extracted_fields,
                "consistency_flags": d.consistency_flags,
            }
            for d in documents
        ],
        "fraud_graph": graph,
        "compliance": compliance_checklist(case, risk, graph),
        "counterparty_dossier": counterparty_dossier(db, case),
        "evidence_bundle": evidence_bundle(case, risk, documents, audits, graph),
    }


def llm_case_chat(case_pack: dict, question: str) -> dict:
    messages = [
        {"role": "system", "content": build_trade_finance_system_prompt()},
        {"role": "user", "content": build_case_prompt(case_pack, question)},
    ]

    try:
        out = ollama_chat(messages)
        return {
            "mode": "real_llm",
            "provider": out["provider"],
            "model": out["model"],
            "answer": out["content"],
            "grounding_sources": list(case_pack.keys()),
            "disclaimer": "LLM output is decision support only. Human approval remains mandatory.",
            "raw": out["raw"],
        }
    except LLMUnavailable as exc:
        return {
            "mode": "llm_unavailable",
            "answer": str(exc),
            "grounding_sources": list(case_pack.keys()),
            "disclaimer": "No fake fallback answer was generated.",
        }


def llm_credit_memo(case_pack: dict) -> dict:
    question = (
        "Generate a credit committee memo for this trade-finance case. "
        "Include executive summary, transaction overview, key risk drivers, document gaps, "
        "fraud or beneficiary-account concerns, recommended limit, conditions precedent, "
        "and final human-review caveat."
    )
    return llm_case_chat(case_pack, question)
