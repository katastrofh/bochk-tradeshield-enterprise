from __future__ import annotations

from typing import Any


def latest_risk(case) -> Any | None:
    risks = list(getattr(case, "risks", []) or [])
    if not risks:
        return None
    return sorted(risks, key=lambda r: r.created_at)[-1]


def next_action(case, risk=None, documents=None) -> dict:
    documents = documents or []
    risk = risk or latest_risk(case)
    if not documents:
        return {"code": "UPLOAD_DOCUMENTS", "label": "Upload trade documents", "owner": "SME / Officer", "severity": "MEDIUM"}
    if not risk:
        return {"code": "GENERATE_RISK_PASSPORT", "label": "Generate Risk Passport", "owner": "Trade Finance Officer", "severity": "HIGH"}
    if risk.category == "HIGH" and case.status != "REJECTED" and case.decision is None:
        return {"code": "RISK_MANAGER_REVIEW", "label": "Risk manager review required", "owner": "Risk Manager", "severity": "HIGH"}
    if case.decision is None:
        return {"code": "HUMAN_DECISION", "label": "Record approve / reject decision", "owner": "Officer", "severity": "MEDIUM"}
    if case.status in {"APPROVED", "PARTIALLY_APPROVED"} and not case.supplier_verified:
        return {"code": "VERIFY_SUPPLIER", "label": "Verify beneficiary account", "owner": "Operations", "severity": "HIGH"}
    if case.status in {"APPROVED", "PARTIALLY_APPROVED"} and not case.shipment_verified:
        return {"code": "VERIFY_SHIPMENT", "label": "Verify shipment evidence", "owner": "Operations", "severity": "HIGH"}
    if case.status in {"APPROVED", "PARTIALLY_APPROVED"} and case.settlement_status != "RELEASED":
        return {"code": "RELEASE_SETTLEMENT", "label": "Release conditional settlement", "owner": "Operations", "severity": "MEDIUM"}
    return {"code": "MONITOR", "label": "Monitor case and audit trail", "owner": "Bank", "severity": "LOW"}


def workflow_state(case, risk=None, documents=None, audits=None) -> list[dict]:
    documents = documents or []
    audits = audits or []
    risk = risk or latest_risk(case)
    return [
        {"step": 1, "name": "Case Intake", "complete": case.status != "DRAFT", "owner": "SME / Officer", "explanation": "Trade finance request captured with buyer, supplier, route, amount, and terms."},
        {"step": 2, "name": "Document Evidence", "complete": len(documents) > 0, "owner": "SME / Officer", "explanation": "Invoices, purchase orders, shipment evidence, and extracted fields are linked to the case."},
        {"step": 3, "name": "Risk Passport", "complete": risk is not None, "owner": "Risk Engine", "explanation": "The case receives explainable risk scoring, recommended amount, controls, and fraud indicators."},
        {"step": 4, "name": "Human Decision", "complete": case.decision is not None, "owner": "Bank Officer", "explanation": "A human decision is required; the system is not autonomous lending."},
        {"step": 5, "name": "Settlement Controls", "complete": case.supplier_verified and case.shipment_verified, "owner": "Operations", "explanation": "Settlement cannot release until beneficiary and shipment evidence are verified."},
        {"step": 6, "name": "Audit & Governance", "complete": len(audits) > 0, "owner": "Compliance", "explanation": "Material actions are written to a hash-linked audit trail."},
    ]


def workflow_readiness(case, risk=None, documents=None, audits=None) -> dict:
    wf = workflow_state(case, risk, documents, audits)
    complete = sum(1 for w in wf if w["complete"])
    return {
        "percent": round(100 * complete / len(wf), 1),
        "complete_steps": complete,
        "total_steps": len(wf),
        "next_action": next_action(case, risk, documents),
        "steps": wf,
    }
