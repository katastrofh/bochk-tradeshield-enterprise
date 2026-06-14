from types import SimpleNamespace
from tradeshield.risk_engine import calculate_risk


def test_high_risk_requires_escalation():
    case = SimpleNamespace(
        requested_financing_hkd=880000,
        invoice_amount_hkd=920000,
        previous_supplier_bank_account=None,
        supplier_bank_account="HK-SHARED-4455",
        supplier_name="New Asia Components",
        destination_country="Indonesia",
        shipment_verified=False,
        shipment_status="PENDING",
        esg_status="NOT_SUBMITTED",
    )
    result = calculate_risk(case, [], ["Supplier bank account appears in 2 cases."])
    assert result.category in {"MEDIUM", "HIGH"}
    assert "Escalate" in result.narrative or result.recommendation in {"ESCALATE", "PARTIAL_APPROVE"}
    assert result.recommended_amount_hkd <= case.requested_financing_hkd
