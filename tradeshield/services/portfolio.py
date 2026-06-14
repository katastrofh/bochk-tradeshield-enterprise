from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from tradeshield.models import RiskAssessment, TradeCase


def _latest_risk_for_cases(db, case_ids: list[int]) -> dict[int, RiskAssessment]:
    latest = {}
    for case_id in case_ids:
        r = db.query(RiskAssessment).filter(RiskAssessment.case_id == case_id).order_by(RiskAssessment.id.desc()).first()
        if r:
            latest[case_id] = r
    return latest


def portfolio_summary(db) -> dict:
    cases = db.query(TradeCase).order_by(TradeCase.id.asc()).all()
    latest = _latest_risk_for_cases(db, [c.id for c in cases])
    total_requested = sum(c.requested_financing_hkd or 0 for c in cases)
    total_approved = sum(c.approved_amount_hkd or 0 for c in cases)
    total_released = sum((c.approved_amount_hkd or 0) for c in cases if c.settlement_status == "RELEASED")
    status_counts = Counter(c.status for c in cases)
    corridor_counts = Counter(f"{c.origin_country} → {c.destination_country}" for c in cases)
    risk_counts = Counter(latest[c.id].category for c in cases if c.id in latest)
    risk_scores = [latest[c.id].overall_score for c in cases if c.id in latest]
    pending_decisions = [c for c in cases if c.decision is None]
    return {
        "case_count": len(cases),
        "total_requested_hkd": round(total_requested, 2),
        "total_approved_hkd": round(total_approved, 2),
        "total_released_hkd": round(total_released, 2),
        "status_counts": dict(status_counts),
        "risk_counts": dict(risk_counts),
        "corridor_counts": dict(corridor_counts),
        "average_risk_score": round(mean(risk_scores), 2) if risk_scores else None,
        "pending_decisions": len(pending_decisions),
        "scored_cases": len(risk_scores),
        "unscored_cases": len(cases) - len(risk_scores),
    }


def exposure_by_corridor(db) -> list[dict]:
    cases = db.query(TradeCase).order_by(TradeCase.id.asc()).all()
    latest = _latest_risk_for_cases(db, [c.id for c in cases])
    agg = defaultdict(lambda: {"cases": 0, "requested_hkd": 0.0, "approved_hkd": 0.0, "high_risk_cases": 0, "medium_risk_cases": 0})
    for c in cases:
        corridor = f"{c.origin_country} → {c.destination_country}"
        a = agg[corridor]
        a["cases"] += 1
        a["requested_hkd"] += c.requested_financing_hkd or 0
        a["approved_hkd"] += c.approved_amount_hkd or 0
        r = latest.get(c.id)
        if r and r.category == "HIGH":
            a["high_risk_cases"] += 1
        if r and r.category == "MEDIUM":
            a["medium_risk_cases"] += 1
    return [{"corridor": k, **{kk: round(vv, 2) if isinstance(vv, float) else vv for kk, vv in v.items()}} for k, v in agg.items()]


def risk_matrix(db) -> list[dict]:
    cases = db.query(TradeCase).order_by(TradeCase.id.asc()).all()
    latest = _latest_risk_for_cases(db, [c.id for c in cases])
    rows = []
    for c in cases:
        r = latest.get(c.id)
        rows.append({
            "case_id": c.id,
            "case_ref": c.case_ref,
            "sme": c.sme_name,
            "corridor": f"{c.origin_country} → {c.destination_country}",
            "requested_hkd": c.requested_financing_hkd,
            "status": c.status,
            "decision": c.decision,
            "settlement_status": c.settlement_status,
            "risk_category": r.category if r else "UNSCORED",
            "risk_score": r.overall_score if r else None,
            "recommended_amount_hkd": r.recommended_amount_hkd if r else None,
        })
    return rows
