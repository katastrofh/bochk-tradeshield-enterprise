from __future__ import annotations

from tradeshield.models import RiskAssessment, TradeCase


def _latest_risk(db, case_id: int):
    return db.query(RiskAssessment).filter(RiskAssessment.case_id == case_id).order_by(RiskAssessment.id.desc()).first()


def portfolio_stress(db) -> dict:
    cases = db.query(TradeCase).order_by(TradeCase.id.asc()).all()
    rows = []
    for c in cases:
        r = _latest_risk(db, c.id)
        score = r.overall_score if r else 50
        exposure = c.approved_amount_hkd or c.requested_financing_hkd or 0
        rows.append({"case_ref": c.case_ref, "corridor": f"{c.origin_country} → {c.destination_country}", "exposure_hkd": exposure, "risk_score": score})

    base = sum(x["exposure_hkd"] for x in rows)
    scenarios = []
    for name, multiplier, add_bps in [
        ("Base expected loss", 1.0, 0),
        ("Corridor disruption", 1.35, 55),
        ("Buyer default cluster", 1.80, 120),
        ("Fraud-ring discovery", 2.40, 250),
    ]:
        weighted_bps = 0.0
        for row in rows:
            weighted_bps += row["exposure_hkd"] * ((row["risk_score"] * 4.5) + add_bps) / 10000
        loss = weighted_bps * multiplier
        scenarios.append({"name": name, "gross_exposure_hkd": round(base, 2), "stressed_loss_hkd": round(loss, 2), "loss_bps_of_exposure": round((loss / base * 10000) if base else 0, 1)})

    top_exposures = sorted(rows, key=lambda x: x["exposure_hkd"], reverse=True)[:5]
    return {"scenarios": scenarios, "top_exposures": top_exposures, "method": "Synthetic deterministic stress test for demo governance; not a regulatory capital model."}
