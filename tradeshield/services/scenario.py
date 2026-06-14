"""Scenario simulation service for case-level decision support."""


def stress_scenarios(case, risk=None) -> dict:
    score = getattr(risk, "overall_score", 50) if risk else 50
    requested = getattr(case, "requested_financing_hkd", 0) or 0
    recommended = (
        getattr(risk, "recommended_amount_hkd", requested * 0.6)
        if risk
        else requested * 0.6
    )
    case_ref = getattr(case, "case_ref", "TEST-CASE")

    scenarios = [
        {
            "name": "Base case",
            "risk_score": round(score, 2),
            "limit_hkd": round(recommended, 2),
            "expected_loss_bps": round(30 + score * 1.8, 1),
        },
        {
            "name": "Shipment delay +14 days",
            "risk_score": min(100, round(score + 8, 2)),
            "limit_hkd": round(recommended * 0.90, 2),
            "expected_loss_bps": round(45 + score * 2.1, 1),
        },
        {
            "name": "Beneficiary-account anomaly",
            "risk_score": min(100, round(score + 18, 2)),
            "limit_hkd": round(recommended * 0.70, 2),
            "expected_loss_bps": round(80 + score * 2.5, 1),
        },
        {
            "name": "ESG certificate verified",
            "risk_score": max(0, round(score - 3, 2)),
            "limit_hkd": round(min(requested, recommended * 1.03), 2),
            "expected_loss_bps": round(25 + max(0, score - 3) * 1.6, 1),
        },
    ]

    return {
        "case_ref": case_ref,
        "scenarios": scenarios,
        "note": "Scenario outputs are synthetic decision-support values for demo purposes.",
    }
