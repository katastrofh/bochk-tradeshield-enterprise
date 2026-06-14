from __future__ import annotations

from sqlalchemy.orm import Session
from tradeshield.models import TradeCase


def counterparty_dossier(db: Session, case: TradeCase) -> dict:
    supplier_cases = db.query(TradeCase).filter(TradeCase.supplier_name == case.supplier_name).all()
    buyer_cases = db.query(TradeCase).filter(TradeCase.buyer_name == case.buyer_name).all()
    account_cases = db.query(TradeCase).filter(TradeCase.supplier_bank_account == case.supplier_bank_account).all()
    alerts = []
    if len(account_cases) > 1:
        alerts.append(f"Supplier bank account appears in {len(account_cases)} cases.")
    if case.previous_supplier_bank_account and case.previous_supplier_bank_account != case.supplier_bank_account:
        alerts.append("Supplier beneficiary account changed versus prior record.")
    return {
        "supplier": {
            "name": case.supplier_name,
            "known_cases": len(supplier_cases),
            "bank_account": case.supplier_bank_account,
            "shared_account_cases": [c.case_ref for c in account_cases if c.id != case.id],
        },
        "buyer": {"name": case.buyer_name, "known_cases": len(buyer_cases)},
        "route": {"origin": case.origin_country, "destination": case.destination_country},
        "alerts": alerts,
        "assessment": "Review required" if alerts else "No material counterparty anomaly in synthetic portfolio.",
    }
