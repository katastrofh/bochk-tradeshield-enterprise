from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MODEL_VERSION = "TS-RISK-2026.04"


@dataclass
class RiskResult:
    overall_score: float
    category: str
    recommendation: str
    recommended_amount_hkd: float
    required_actions: list[str]
    sub_scores: dict[str, float]
    risk_drivers: list[str]
    mitigating_factors: list[str]
    fraud_indicators: list[str]
    narrative: str


HIGH_RISK_DESTINATIONS = {"indonesia", "philippines"}
MEDIUM_RISK_DESTINATIONS = {"vietnam", "thailand", "malaysia"}


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def calculate_risk(case, documents: list[Any], graph_indicators: list[str] | None = None) -> RiskResult:
    graph_indicators = graph_indicators or []
    drivers: list[str] = []
    mitigants: list[str] = []
    required: list[str] = []
    fraud: list[str] = list(graph_indicators)

    amount_ratio = case.requested_financing_hkd / max(case.invoice_amount_hkd, 1)
    document_flags = []
    for doc in documents:
        document_flags.extend(doc.consistency_flags or [])

    high_doc_flags = [f for f in document_flags if f.get("severity") == "HIGH"]
    medium_doc_flags = [f for f in document_flags if f.get("severity") == "MEDIUM"]

    doc_risk = 20 + 25 * len(high_doc_flags) + 12 * len(medium_doc_flags)
    if not documents:
        doc_risk += 35
        drivers.append("No supporting trade document has been uploaded.")
        required.append("Upload invoice, purchase order, and shipment evidence.")
    elif high_doc_flags:
        drivers.append("Material document inconsistency detected.")
        required.append("Resolve document inconsistencies before unconditional approval.")
    else:
        mitigants.append("Trade documents are materially consistent with the case profile.")

    supplier_risk = 28
    if case.previous_supplier_bank_account and case.previous_supplier_bank_account != case.supplier_bank_account:
        supplier_risk += 38
        drivers.append("Supplier bank account changed from prior transaction history.")
        required.append("Verify supplier bank account ownership.")
        fraud.append("Changed supplier beneficiary account")
    else:
        mitigants.append("Supplier beneficiary account is stable or has no negative history.")

    if "unknown" in case.supplier_name.lower() or "new" in case.supplier_name.lower():
        supplier_risk += 20
        drivers.append("Supplier appears new or weakly known to the bank.")

    corridor = case.destination_country.lower()
    corridor_risk = 22
    if corridor in HIGH_RISK_DESTINATIONS:
        corridor_risk += 38
        drivers.append(f"{case.destination_country} corridor requires enhanced monitoring.")
    elif corridor in MEDIUM_RISK_DESTINATIONS:
        corridor_risk += 20
        drivers.append(f"{case.destination_country} corridor has medium cross-border risk.")
    else:
        mitigants.append("Trade corridor is within a lower-risk monitored route.")

    financing_risk = 20
    if amount_ratio > 0.85:
        financing_risk += 26
        drivers.append("Requested financing is high relative to invoice value.")
    elif amount_ratio <= 0.75:
        mitigants.append("Requested financing is conservatively below invoice value.")

    shipment_risk = 20
    if not case.shipment_verified and case.shipment_status.upper() not in {"VERIFIED", "DELIVERED"}:
        shipment_risk += 25
        drivers.append("Shipment proof is not independently verified.")
        required.append("Verify shipment evidence before settlement release.")
    else:
        mitigants.append("Shipment status is verified or near completion.")

    graph_risk = 15 + min(45, 15 * len(graph_indicators))
    if graph_indicators:
        drivers.append("Fraud network analytics found linked suspicious entities.")
        required.append("Review fraud network before final approval.")

    aml_risk = 18
    if len(fraud) >= 2:
        aml_risk += 20
        drivers.append("Multiple fraud/AML indicators require enhanced due diligence.")

    esg_risk = 15
    if case.esg_status == "VERIFIED":
        mitigants.append("ESG evidence is verified and supports green-trade eligibility.")
        esg_risk = 5
    elif case.esg_status == "NOT_SUBMITTED":
        required.append("Optional: upload ESG certificate for green-trade finance eligibility.")

    sub_scores = {
        "document_risk": _clamp(doc_risk),
        "supplier_risk": _clamp(supplier_risk),
        "corridor_risk": _clamp(corridor_risk),
        "financing_risk": _clamp(financing_risk),
        "shipment_risk": _clamp(shipment_risk),
        "fraud_graph_risk": _clamp(graph_risk),
        "aml_risk": _clamp(aml_risk),
        "esg_risk": _clamp(esg_risk),
    }

    overall = (
        sub_scores["document_risk"] * 0.18
        + sub_scores["supplier_risk"] * 0.18
        + sub_scores["corridor_risk"] * 0.12
        + sub_scores["financing_risk"] * 0.12
        + sub_scores["shipment_risk"] * 0.12
        + sub_scores["fraud_graph_risk"] * 0.16
        + sub_scores["aml_risk"] * 0.08
        + sub_scores["esg_risk"] * 0.04
    )
    overall = round(_clamp(overall), 2)

    if overall < 35:
        category = "LOW"
        recommendation = "APPROVE"
        recommended_amount = min(case.requested_financing_hkd, case.invoice_amount_hkd * 0.85)
        if not required:
            required.append("Standard officer review.")
    elif overall < 65:
        category = "MEDIUM"
        recommendation = "PARTIAL_APPROVE"
        recommended_amount = min(case.requested_financing_hkd, case.invoice_amount_hkd * 0.70)
        required.append("Apply conditional settlement controls.")
    else:
        category = "HIGH"
        recommendation = "ESCALATE"
        recommended_amount = min(case.requested_financing_hkd, case.invoice_amount_hkd * 0.40)
        required.append("Escalate to risk manager; do not release settlement without enhanced due diligence.")

    if not drivers:
        drivers.append("No dominant risk driver identified.")
    if not mitigants:
        mitigants.append("No strong mitigating factor identified.")

    narrative = (
        f"This case is classified as {category} risk with an overall score of {overall}/100. "
        f"The recommended action is {recommendation}, with a suggested financing amount of "
        f"HK${recommended_amount:,.0f}. The system is decision-support: final approval remains "
        "with authorised BOCHK personnel."
    )

    return RiskResult(
        overall_score=overall,
        category=category,
        recommendation=recommendation,
        recommended_amount_hkd=round(recommended_amount, 2),
        required_actions=list(dict.fromkeys(required)),
        sub_scores=sub_scores,
        risk_drivers=list(dict.fromkeys(drivers)),
        mitigating_factors=list(dict.fromkeys(mitigants)),
        fraud_indicators=list(dict.fromkeys(fraud)),
        narrative=narrative,
    )
