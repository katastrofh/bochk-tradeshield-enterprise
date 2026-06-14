from __future__ import annotations

import hashlib
import json


def evidence_bundle(case, risk=None, docs=None, audits=None, graph=None) -> dict:
    docs = docs or []
    audits = audits or []
    graph = graph or {}
    payload = {
        "case_ref": case.case_ref,
        "sme": case.sme_name,
        "buyer": case.buyer_name,
        "supplier": case.supplier_name,
        "route": [case.origin_country, case.destination_country],
        "invoice_amount_hkd": case.invoice_amount_hkd,
        "requested_financing_hkd": case.requested_financing_hkd,
        "status": case.status,
        "decision": case.decision,
        "settlement_status": case.settlement_status,
        "risk": None if not risk else {
            "model_version": risk.model_version,
            "score": risk.overall_score,
            "category": risk.category,
            "recommendation": risk.recommendation,
            "recommended_amount_hkd": risk.recommended_amount_hkd,
        },
        "documents": [{"id": d.id, "type": d.doc_type, "filename": d.filename, "sha256": d.file_hash, "flags": d.consistency_flags} for d in docs],
        "audit_hashes": [a.event_hash for a in audits],
        "fraud_indicators": graph.get("indicators", []),
    }
    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return {
        "case_ref": case.case_ref,
        "bundle_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "evidence_count": len(docs),
        "audit_event_count": len(audits),
        "fraud_indicator_count": len(graph.get("indicators", [])),
        "canonical_payload": payload,
        "explain": "The bundle hash commits to the current case, document hashes, latest risk result, fraud indicators, and audit-event hashes.",
    }


def trade_timeline(case, risk=None, docs=None, audits=None) -> dict:
    docs = docs or []
    audits = audits or []
    items = [
        {"stage": "Case created", "status": "DONE", "owner": "SME / RM", "detail": f"{case.case_ref} submitted for {case.sme_name}."},
        {"stage": "Evidence intake", "status": "DONE" if docs else "PENDING", "owner": "Operations", "detail": f"{len(docs)} document(s) parsed and hashed."},
        {"stage": "Risk Passport", "status": "DONE" if risk else "PENDING", "owner": "Risk analytics", "detail": risk.narrative if risk else "Generate model-supported decision package."},
        {"stage": "Human decision", "status": "DONE" if case.decision else "PENDING", "owner": "Officer / Risk Manager", "detail": case.decision_reason or "Awaiting authorised decision."},
        {"stage": "Supplier verification", "status": "DONE" if case.supplier_verified else "PENDING", "owner": "Operations", "detail": "Beneficiary account verified." if case.supplier_verified else "Independent beneficiary check required."},
        {"stage": "Shipment verification", "status": "DONE" if case.shipment_verified else "PENDING", "owner": "Operations", "detail": "Shipment evidence verified." if case.shipment_verified else "Shipment evidence required before release."},
        {"stage": "Settlement", "status": "DONE" if case.settlement_status == "RELEASED" else case.settlement_status, "owner": "Trade operations", "detail": f"Settlement status: {case.settlement_status}."},
        {"stage": "Audit chain", "status": "LIVE", "owner": "Governance", "detail": f"{len(audits)} case-level audit event(s) recorded."},
    ]
    return {"case_ref": case.case_ref, "timeline": items}
