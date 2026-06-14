from tradeshield.services.pricing import indicative_pricing
from tradeshield.services.scenario import stress_scenarios

class C:
    requested_financing_hkd = 100
    invoice_amount_hkd = 120
    payment_term_days = 45
    esg_status = "VERIFIED"

class R:
    category = "LOW"
    recommended_amount_hkd = 80
    overall_score = 25


def test_pricing_returns_terms():
    p = indicative_pricing(C(), R())
    assert p["indicative_margin_bps"] > 0
    assert p["suggested_limit_hkd"] == 80


def test_scenarios_return_four_cases():
    s = stress_scenarios(C(), R())
    assert len(s["scenarios"]) == 4
