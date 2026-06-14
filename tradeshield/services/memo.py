from __future__ import annotations


def credit_memo(case, risk=None, compliance=None, pricing=None, evidence=None, copilot=None) -> dict:
    compliance = compliance or {}
    pricing = pricing or {}
    evidence = evidence or {}
    copilot = copilot or {}
    recommended_amount = risk.recommended_amount_hkd if risk else pricing.get("suggested_limit_hkd", 0)
    decision = "DEFER UNTIL RISK PASSPORT" if risk is None else risk.recommendation
    if compliance.get("approval_blocked"):
        decision = "CONDITIONAL / BLOCKED UNTIL CONTROLS CLEARED"
    sections = [
        {"title": "Applicant and transaction", "body": f"{case.sme_name} requests HK${case.requested_financing_hkd:,.0f} for goods: {case.goods_description}. Corridor: {case.origin_country} to {case.destination_country}."},
        {"title": "Risk position", "body": risk.narrative if risk else "Risk Passport not yet generated."},
        {"title": "Recommended structure", "body": f"Suggested limit HK${recommended_amount:,.0f}; indicative margin {pricing.get('indicative_margin_bps', '—')} bps; release gated by supplier and shipment controls."},
        {"title": "Governance evidence", "body": f"Evidence bundle hash {evidence.get('bundle_hash', 'not generated')} commits to documents, audit hashes, and risk state."},
        {"title": "Next best action", "body": copilot.get("next_best_action", "Review case in workbench.")},
    ]
    return {"case_ref": case.case_ref, "proposed_decision": decision, "recommended_amount_hkd": recommended_amount, "sections": sections, "generated_by": "TradeShield deterministic credit memo generator"}
