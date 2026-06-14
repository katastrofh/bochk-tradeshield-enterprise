from __future__ import annotations

import hashlib
import re
from typing import Any

from dateutil import parser as date_parser


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_trade_document(text: str) -> dict[str, Any]:
    def find(pattern: str):
        m = re.search(pattern, text, flags=re.IGNORECASE)
        return m.group(1).strip() if m else None

    def amount(value: str | None):
        if not value:
            return None
        try:
            return float(value.replace(",", ""))
        except Exception:
            return None

    def date(value: str | None):
        if not value:
            return None
        try:
            return date_parser.parse(value, fuzzy=True).date().isoformat()
        except Exception:
            return None

    return {
        "invoice_number": find(r"Invoice\s*(?:No\.?|Number|#)?\s*[:\-]\s*([A-Z0-9\-/]+)"),
        "po_number": find(r"(?:Purchase\s*Order|PO)\s*(?:No\.?|Number|#)?\s*[:\-]\s*([A-Z0-9\-/]+)"),
        "invoice_amount_hkd": amount(find(r"(?:HK\$|HKD)\s*([0-9,]+(?:\.\d+)?)")),
        "invoice_date": date(find(r"Invoice\s*Date\s*[:\-]\s*([^\n]+)")),
        "supplier": find(r"Supplier\s*[:\-]\s*([^\n]+)"),
        "buyer": find(r"Buyer\s*[:\-]\s*([^\n]+)"),
        "supplier_bank_account": find(r"Supplier\s*Bank\s*Account\s*[:\-]\s*([^\n]+)"),
        "shipment_status": find(r"Shipment\s*Status\s*[:\-]\s*([^\n]+)"),
        "payment_term_days": int(find(r"(?:Payment\s*Terms?|Net)\s*[:\-]?\s*(\d{1,3})") or 0) or None,
    }


def consistency_checks(case, fields: dict[str, Any]) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    if fields.get("invoice_amount_hkd") and abs(fields["invoice_amount_hkd"] - case.invoice_amount_hkd) > 1:
        flags.append({"severity": "HIGH", "message": "Uploaded invoice amount does not match the case amount."})
    if fields.get("supplier") and fields["supplier"].lower() not in case.supplier_name.lower():
        flags.append({"severity": "MEDIUM", "message": "Supplier name differs from case supplier."})
    if fields.get("buyer") and fields["buyer"].lower() not in case.buyer_name.lower():
        flags.append({"severity": "MEDIUM", "message": "Buyer name differs from case buyer."})
    if fields.get("supplier_bank_account") and fields["supplier_bank_account"] != case.supplier_bank_account:
        flags.append({"severity": "HIGH", "message": "Supplier bank account in document differs from case record."})
    if not flags:
        flags.append({"severity": "LOW", "message": "No material document inconsistency detected."})
    return flags
