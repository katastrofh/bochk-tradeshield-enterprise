from __future__ import annotations


def compliance_checklist(case, risk=None, graph=None) -> dict:
    graph = graph or {}
    indicators = list((graph or {}).get("indicators", []))
    checks = []
    def add(code, title, status, severity, owner, detail):
        checks.append({"code": code, "title": title, "status": status, "severity": severity, "owner": owner, "detail": detail})

    add("KYC_SME", "SME KYC profile", "PASS", "LOW", "Compliance", "Demo SME profile is known in the synthetic portfolio.")
    add("KYB_SUPPLIER", "Supplier KYB / beneficiary ownership", "PASS" if case.supplier_verified else "PENDING", "HIGH", "Operations", "Verify supplier bank account ownership before settlement.")
    add("SHIPMENT_PROOF", "Shipment evidence", "PASS" if case.shipment_verified else "PENDING", "HIGH", "Operations", "Shipment evidence must match invoice and trade route.")
    add("SANCTIONS_SCREEN", "Sanctions and adverse-media screen", "PENDING" if indicators else "PASS", "HIGH" if indicators else "LOW", "Compliance", "Escalate any graph or beneficiary anomaly for enhanced due diligence.")
    add("AML_GRAPH", "Fraud-network anomaly review", "PENDING" if indicators else "PASS", "HIGH" if indicators else "LOW", "Financial Crime", "; ".join(indicators) if indicators else "No material linked-account anomaly detected.")
    add("ESG_EVIDENCE", "ESG / green-trade evidence", "PASS" if case.esg_status == "VERIFIED" else "OPTIONAL", "LOW", "ESG Desk", "Optional evidence supports green finance tagging; not required for base financing.")

    blockers = [c for c in checks if c["status"] == "PENDING" and c["severity"] == "HIGH"]
    return {
        "case_ref": case.case_ref,
        "approval_blocked": bool(blockers),
        "blockers": blockers,
        "checks": checks,
        "summary": "Enhanced review required." if blockers else "No hard compliance blocker detected for officer review.",
    }
