from __future__ import annotations


def notification_feed(case=None, risk=None) -> list[dict]:
    items = []
    if not case:
        return items
    items.append({"level": "INFO", "title": f"Case {case.case_ref} selected", "body": "Risk Passport workspace is ready."})
    if risk is None:
        items.append({"level": "ACTION", "title": "Generate Risk Passport", "body": "No current model assessment exists for this case."})
    elif risk.category == "HIGH":
        items.append({"level": "HIGH", "title": "Risk manager review required", "body": "High-risk cases cannot be approved by officer alone."})
    if case.status in {"APPROVED", "PARTIALLY_APPROVED"} and case.settlement_status != "RELEASED":
        items.append({"level": "ACTION", "title": "Settlement controls pending", "body": "Supplier and shipment verification are required before release."})
    if case.esg_status != "VERIFIED":
        items.append({"level": "LOW", "title": "ESG evidence optional", "body": "Verify ESG certificate to activate green-trade tagging."})
    return items
