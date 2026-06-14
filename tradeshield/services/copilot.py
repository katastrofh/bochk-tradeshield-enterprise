from __future__ import annotations

from typing import Iterable


def _top(items: Iterable[str], n: int = 4) -> list[str]:
    out: list[str] = []
    for item in items:
        if item and item not in out:
            out.append(item)
        if len(out) >= n:
            break
    return out


def case_copilot_brief(case, risk=None, docs=None, graph=None, compliance=None, pricing=None) -> dict:
    """Deterministic banker-assistant brief.

    No external LLM call is made. This keeps the demo self-contained while still
    showing the product workflow BOCHK judges care about: explain, challenge,
    decide, control, and audit.
    """
    docs = docs or []
    graph = graph or {}
    compliance = compliance or {}
    pricing = pricing or {}
    risk_category = risk.category if risk else "UNSCORED"
    score = risk.overall_score if risk else None
    recommended = risk.recommended_amount_hkd if risk else min(case.requested_financing_hkd, case.invoice_amount_hkd * 0.65)
    blockers = compliance.get("blockers", []) if isinstance(compliance, dict) else []
    indicators = graph.get("indicators", []) if isinstance(graph, dict) else []

    if risk is None:
        next_step = "Generate the Risk Passport before recording a lending decision."
        decision_position = "No credit decision should be entered until the model package and evidence checks exist."
    elif risk_category == "HIGH":
        next_step = "Escalate to a risk manager and resolve enhanced-due-diligence blockers."
        decision_position = "Officer-only approval is blocked; risk-manager sign-off is mandatory."
    elif blockers:
        next_step = "Clear high-severity compliance and settlement blockers before disbursement."
        decision_position = "Conditional approval may be possible, but release should remain blocked."
    elif risk.recommendation == "APPROVE":
        next_step = "Proceed to human approval, then verify supplier and shipment before release."
        decision_position = "Approval path is supportable if the officer agrees with the evidence package."
    else:
        next_step = "Record partial approval with controls matched to the identified risk drivers."
        decision_position = "Partial approval is safer than full invoice advance for this exposure."

    executive_summary = (
        f"{case.case_ref} is a {case.origin_country} to {case.destination_country} trade-finance request for "
        f"HK${case.requested_financing_hkd:,.0f} against an invoice of HK${case.invoice_amount_hkd:,.0f}. "
        f"Current Risk Passport status is {risk_category}"
        + (f" with score {score:.0f}/100" if score is not None else "")
        + f". Suggested working limit is HK${recommended:,.0f}."
    )

    banker_questions = [
        "Does the invoice amount, buyer, supplier, and route match uploaded evidence?",
        "Has the supplier beneficiary account been independently verified?",
        "Does the shipment proof support the goods and corridor claimed by the SME?",
    ]
    if indicators:
        banker_questions.insert(0, "Can the shared-account or beneficiary-change anomaly be explained with documentary evidence?")
    if case.payment_term_days > 75:
        banker_questions.append("Is the extended tenor justified by buyer history or collateral support?")

    objections = [
        {"objection": "The model score is not a final credit decision.", "response": "Correct. The system provides explainable decision support; final approval remains with authorised BOCHK staff."},
        {"objection": "Fraud graph evidence may be noisy.", "response": "Graph signals are treated as review triggers, not automatic rejection rules."},
        {"objection": "Settlement is operational, not only credit risk.", "response": "Release remains gated by supplier and shipment verification even after approval."},
    ]

    return {
        "case_ref": case.case_ref,
        "executive_summary": executive_summary,
        "decision_position": decision_position,
        "next_best_action": next_step,
        "suggested_limit_hkd": round(recommended, 2),
        "pricing_snapshot": {
            "indicative_margin_bps": pricing.get("indicative_margin_bps"),
            "platform_fee_hkd": pricing.get("platform_fee_hkd"),
            "terms": pricing.get("terms", []),
        },
        "top_risk_drivers": _top(risk.risk_drivers if risk else ["Risk Passport has not been generated."], 5),
        "required_controls": _top(risk.required_actions if risk else ["Generate risk score", "Upload/parse evidence", "Run fraud graph"], 6),
        "compliance_blockers": blockers,
        "fraud_indicators": indicators,
        "document_evidence": [
            {"type": d.doc_type, "filename": d.filename, "hash": d.file_hash, "flags": d.consistency_flags} for d in docs
        ],
        "banker_questions": banker_questions,
        "objection_handling": objections,
        "demo_script": [
            "Open the case queue and select this application.",
            "Generate or refresh the Risk Passport.",
            "Show the risk drivers, compliance blockers, and fraud graph.",
            "Record a human decision and then demonstrate settlement gates.",
            "Open audit governance to show tamper-evident history.",
        ],
    }
