from __future__ import annotations


def indicative_pricing(case, risk=None) -> dict:
    base_margin_bps = 250
    risk_adj = 0
    if risk:
        if risk.category == "LOW":
            risk_adj = 60
        elif risk.category == "MEDIUM":
            risk_adj = 180
        else:
            risk_adj = 420
    tenor_adj = 0 if case.payment_term_days <= 45 else 60 if case.payment_term_days <= 75 else 120
    esg_discount = -35 if case.esg_status == "VERIFIED" else 0
    total_margin = base_margin_bps + risk_adj + tenor_adj + esg_discount
    platform_fee = max(300, round((case.requested_financing_hkd or 0) * 0.0025, 2))
    return {
        "base_margin_bps": base_margin_bps,
        "risk_adjustment_bps": risk_adj,
        "tenor_adjustment_bps": tenor_adj,
        "esg_discount_bps": esg_discount,
        "indicative_margin_bps": total_margin,
        "platform_fee_hkd": platform_fee,
        "suggested_limit_hkd": risk.recommended_amount_hkd if risk else min(case.requested_financing_hkd, case.invoice_amount_hkd * 0.65),
        "terms": [
            "Subject to human credit approval.",
            "Supplier beneficiary verification required before settlement.",
            "Shipment evidence required before disbursement.",
            "Indicative pricing only; not a binding offer.",
        ],
    }
