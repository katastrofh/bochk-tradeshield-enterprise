from __future__ import annotations

from sqlalchemy.orm import Session

from tradeshield.audit import record_event
from tradeshield.models import ModelRegistry, TradeCase, User
from tradeshield.security import hash_password


USERS = [
    ("admin@tradeshield.ai", "Admin User", "ADMIN", "ChangeMe123!"),
    ("officer@tradeshield.ai", "BOCHK Trade Finance Officer", "OFFICER", "demo12345"),
    ("manager@tradeshield.ai", "BOCHK Risk Manager", "RISK_MANAGER", "demo12345"),
    ("sme@tradeshield.ai", "Demo SME User", "SME", "demo12345"),
    # Backward-compatible aliases for earlier builds.
    ("officer@demo.local", "Legacy Officer Alias", "OFFICER", "demo12345"),
    ("manager@demo.local", "Legacy Manager Alias", "RISK_MANAGER", "demo12345"),
    ("sme@demo.local", "Legacy SME Alias", "SME", "demo12345"),
]


CASES = [
    {
        "case_ref": "TS-HK-CN-001",
        "sme_name": "Harbour Components Limited",
        "sme_email": "sme@tradeshield.ai",
        "buyer_name": "Guangzhou Smart Factory Co.",
        "supplier_name": "Shenzhen Electronics Ltd.",
        "origin_country": "Hong Kong",
        "destination_country": "Mainland China",
        "goods_description": "industrial sensor modules",
        "invoice_amount_hkd": 180000,
        "requested_financing_hkd": 120000,
        "payment_term_days": 30,
        "supplier_bank_account": "CN-SZ-8831-002",
        "previous_supplier_bank_account": "CN-SZ-8831-002",
        "shipment_status": "VERIFIED",
        "shipment_verified": True,
        "supplier_verified": True,
        "esg_status": "VERIFIED",
        "esg_summary": "Supplier ISO 14001 certificate reviewed; green trade tag eligible.",
    },
    {
        "case_ref": "TS-HK-VN-014",
        "sme_name": "Victoria Bay Trading Limited",
        "sme_email": "sme@tradeshield.ai",
        "buyer_name": "Vietnam Retail Group",
        "supplier_name": "Shenzhen Electronics Ltd.",
        "origin_country": "Hong Kong",
        "destination_country": "Vietnam",
        "goods_description": "consumer electronics components",
        "invoice_amount_hkd": 300000,
        "requested_financing_hkd": 300000,
        "payment_term_days": 45,
        "supplier_bank_account": "CN-SZ-9910-NEW",
        "previous_supplier_bank_account": "CN-SZ-8831-002",
        "shipment_status": "PENDING",
    },
    {
        "case_ref": "TS-HK-ID-021",
        "sme_name": "Pacific Micro Exporters",
        "sme_email": "sme@tradeshield.ai",
        "buyer_name": "Jakarta Wholesale Hub",
        "supplier_name": "New Asia Components",
        "origin_country": "Hong Kong",
        "destination_country": "Indonesia",
        "goods_description": "mixed electronic assemblies",
        "invoice_amount_hkd": 920000,
        "requested_financing_hkd": 880000,
        "payment_term_days": 90,
        "supplier_bank_account": "HK-SHARED-4455",
        "previous_supplier_bank_account": None,
        "shipment_status": "PENDING",
    },
    {
        "case_ref": "TS-HK-ID-022",
        "sme_name": "Pearl River Devices",
        "sme_email": "sme@tradeshield.ai",
        "buyer_name": "Surabaya Distribution",
        "supplier_name": "Different Supplier Name",
        "origin_country": "Hong Kong",
        "destination_country": "Indonesia",
        "goods_description": "mobile accessories",
        "invoice_amount_hkd": 550000,
        "requested_financing_hkd": 510000,
        "payment_term_days": 75,
        "supplier_bank_account": "HK-SHARED-4455",
        "previous_supplier_bank_account": None,
        "shipment_status": "PENDING",
    },
]


def seed_data(db: Session) -> None:
    if not db.query(User).first():
        for email, full_name, role, password in USERS:
            db.add(User(email=email, full_name=full_name, role=role, password_hash=hash_password(password)))
        db.commit()
        record_event(db, actor=None, event_type="USER_SEED", event_summary="Demo role-based users seeded.")

    if not db.query(ModelRegistry).first():
        db.add(ModelRegistry(
            model_name="TradeShield Risk Engine",
            version="TS-RISK-2026.04",
            purpose="Explainable trade-finance risk scoring for SME cross-border cases.",
            validation_status="Prototype validated on synthetic cases; requires bank historical-data validation before production use.",
            limitations="Not autonomous lending; requires human approval, model monitoring, and bias/compliance review.",
            owner="Risk Analytics / Trade Finance",
        ))
        db.commit()
        record_event(db, actor=None, event_type="MODEL_REGISTERED", event_summary="Risk model version registered.")

    if not db.query(TradeCase).first():
        for case in CASES:
            db.add(TradeCase(**case, assigned_officer="officer@tradeshield.ai"))
        db.commit()
        record_event(db, actor=None, event_type="CASE_SEED", event_summary="Seeded realistic low, medium, and high-risk trade cases.")
