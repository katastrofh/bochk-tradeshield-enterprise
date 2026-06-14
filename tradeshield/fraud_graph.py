from __future__ import annotations

from sqlalchemy.orm import Session

from tradeshield.models import TradeCase


def build_fraud_graph(db: Session, case: TradeCase) -> dict:
    all_cases = db.query(TradeCase).all()
    nodes = [
        {"id": f"case-{case.id}", "label": case.case_ref, "type": "case"},
        {"id": f"sme-{case.sme_name}", "label": case.sme_name, "type": "sme"},
        {"id": f"supplier-{case.supplier_name}", "label": case.supplier_name, "type": "supplier"},
        {"id": f"buyer-{case.buyer_name}", "label": case.buyer_name, "type": "buyer"},
        {"id": f"account-{case.supplier_bank_account}", "label": case.supplier_bank_account, "type": "bank_account"},
        {"id": f"corridor-{case.destination_country}", "label": f"HK → {case.destination_country}", "type": "corridor"},
    ]
    edges = [
        {"from": f"case-{case.id}", "to": f"sme-{case.sme_name}", "label": "applicant"},
        {"from": f"case-{case.id}", "to": f"supplier-{case.supplier_name}", "label": "supplier"},
        {"from": f"case-{case.id}", "to": f"buyer-{case.buyer_name}", "label": "buyer"},
        {"from": f"supplier-{case.supplier_name}", "to": f"account-{case.supplier_bank_account}", "label": "beneficiary"},
        {"from": f"case-{case.id}", "to": f"corridor-{case.destination_country}", "label": "trade route"},
    ]

    indicators: list[str] = []
    shared_account_cases = [
        c for c in all_cases
        if c.id != case.id and c.supplier_bank_account == case.supplier_bank_account
    ]
    if shared_account_cases:
        indicators.append(f"Supplier bank account appears in {len(shared_account_cases) + 1} cases.")
        for c in shared_account_cases:
            nodes.append({"id": f"case-{c.id}", "label": c.case_ref, "type": "linked_case"})
            edges.append({"from": f"case-{c.id}", "to": f"account-{case.supplier_bank_account}", "label": "same account"})

    same_supplier_cases = [c for c in all_cases if c.id != case.id and c.supplier_name == case.supplier_name]
    if same_supplier_cases:
        indicators.append(f"Supplier appears in {len(same_supplier_cases) + 1} total cases.")

    if case.previous_supplier_bank_account and case.previous_supplier_bank_account != case.supplier_bank_account:
        indicators.append("Supplier beneficiary account changed from historical account.")
        nodes.append({"id": f"old-account-{case.previous_supplier_bank_account}", "label": case.previous_supplier_bank_account, "type": "old_bank_account"})
        edges.append({"from": f"supplier-{case.supplier_name}", "to": f"old-account-{case.previous_supplier_bank_account}", "label": "previous account"})

    narrative = (
        "Fraud graph links the case to entities that may indicate mule accounts, reused documents, "
        "or abnormal supplier behaviour. No document content is stored on-chain; only audit metadata and hashes are logged."
    )

    return {
        "nodes": nodes,
        "edges": edges,
        "indicators": list(dict.fromkeys(indicators)),
        "narrative": narrative,
    }
