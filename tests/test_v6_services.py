from types import SimpleNamespace

from tradeshield.services.copilot import case_copilot_brief
from tradeshield.services.evidence import evidence_bundle, trade_timeline
from tradeshield.services.memo import credit_memo


def fake_case():
    return SimpleNamespace(
        case_ref="TS-TEST-001",
        sme_name="Demo SME",
        buyer_name="Demo Buyer",
        supplier_name="Demo Supplier",
        origin_country="Hong Kong",
        destination_country="Vietnam",
        goods_description="electronics",
        requested_financing_hkd=100000.0,
        invoice_amount_hkd=120000.0,
        payment_term_days=45,
        status="SUBMITTED",
        decision=None,
        decision_reason=None,
        settlement_status="NOT_READY",
        supplier_verified=False,
        shipment_verified=False,
    )


def test_copilot_without_risk():
    brief = case_copilot_brief(fake_case())
    assert brief["case_ref"] == "TS-TEST-001"
    assert "Generate" in brief["next_best_action"]


def test_evidence_bundle_hash_is_stable():
    c = fake_case()
    a = evidence_bundle(c)["bundle_hash"]
    b = evidence_bundle(c)["bundle_hash"]
    assert a == b
    assert len(a) == 64


def test_timeline_and_memo():
    c = fake_case()
    timeline = trade_timeline(c)
    memo = credit_memo(c, evidence=evidence_bundle(c), copilot=case_copilot_brief(c))
    assert len(timeline["timeline"]) >= 6
    assert memo["case_ref"] == c.case_ref
