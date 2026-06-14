from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors


def risk_passport_pdf(case, risk, audits) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"TradeShield Risk Passport {case.case_ref}")
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("BOC TradeShield Enterprise — Risk Passport", styles["Title"]))
    story.append(Paragraph(f"Case reference: {case.case_ref}", styles["Heading2"]))
    story.append(Paragraph("This report is an officer decision-support artefact, not an autonomous lending decision.", styles["BodyText"]))
    story.append(Spacer(1, 12))

    case_table = [
        ["SME", case.sme_name],
        ["Route", f"{case.origin_country} → {case.destination_country}"],
        ["Supplier", case.supplier_name],
        ["Buyer", case.buyer_name],
        ["Invoice amount", f"HK${case.invoice_amount_hkd:,.0f}"],
        ["Requested financing", f"HK${case.requested_financing_hkd:,.0f}"],
        ["Status", case.status],
        ["Settlement", case.settlement_status],
        ["ESG", case.esg_status],
    ]
    story.append(Table(case_table, colWidths=[150, 350], style=[
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2ff")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(Spacer(1, 12))

    if risk:
        story.append(Paragraph("Risk Decision Summary", styles["Heading2"]))
        summary = [
            ["Overall risk score", f"{risk.overall_score}/100"],
            ["Category", risk.category],
            ["Recommendation", risk.recommendation],
            ["Recommended financing", f"HK${risk.recommended_amount_hkd:,.0f}"],
        ]
        story.append(Table(summary, colWidths=[180, 320], style=[
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#fef3c7")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ]))
        story.append(Spacer(1, 8))
        story.append(Paragraph("Risk Drivers", styles["Heading3"]))
        for item in risk.risk_drivers:
            story.append(Paragraph(f"• {item}", styles["BodyText"]))
        story.append(Paragraph("Mitigating Factors", styles["Heading3"]))
        for item in risk.mitigating_factors:
            story.append(Paragraph(f"• {item}", styles["BodyText"]))
        story.append(Paragraph("Required Actions", styles["Heading3"]))
        for item in risk.required_actions:
            story.append(Paragraph(f"• {item}", styles["BodyText"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Audit Trail Proof", styles["Heading2"]))
    for ev in audits[-8:]:
        story.append(Paragraph(f"{ev.created_at} — {ev.event_type}: {ev.event_summary}", styles["BodyText"]))
        story.append(Paragraph(f"Hash: {ev.event_hash[:24]}...", styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()
