from tradeshield.services.ai_layer import (
    document_ai_extract,
    risk_ai_explanation,
    genai_credit_memo,
    ask_case_ai,
)


class Case:
    case_ref = "TS-TEST-AI"
    sme_name = "Demo SME"
    requested_financing_hkd = 800000
    invoice_amount_hkd = 900000
    payment_term_days = 90
    supplier_verified = False
    shipment_verified = False
    supplier_bank_account = "HK-NEW-1"
    previous_supplier_bank_account = "HK-OLD-1"
    goods_description = "electronics"
    destination_country = "Vietnam"


class Risk:
    overall_score = 72
    category = "HIGH"
    recommended_amount_hkd = 420000


class Doc:
    filename = "invoice.txt"
    doc_type = "INVOICE"
    file_hash = "abc123"
    extracted_fields = {
        "invoice_no": "INV-1",
        "buyer": "Buyer Co",
        "supplier": "Supplier Co",
        "amount": "900000",
        "currency": "HKD",
    }
    consistency_flags = ["Amount mismatch needs review"]


def test_document_ai_extracts_confidence_and_discrepancies():
    out = document_ai_extract(Case(), [Doc()])
    assert out["ai_module"] == "Document AI Extractor"
    assert out["human_review_required"] is True
    assert out["overall_confidence"] > 0
    assert out["discrepancies"]


def test_risk_ai_returns_reason_codes():
    out = risk_ai_explanation(Case(), Risk(), [Doc()], {"indicators": ["shared_account"]})
    assert out["ai_module"] == "Explainable Risk AI"
    assert out["risk_category"] == "HIGH"
    assert out["reason_codes"]


def test_genai_memo_and_ask_case():
    doc_ai = document_ai_extract(Case(), [Doc()])
    risk_ai = risk_ai_explanation(Case(), Risk(), [Doc()], {"indicators": []})
    memo = genai_credit_memo(Case(), Risk(), doc_ai, risk_ai)
    ans = ask_case_ai(Case(), Risk(), doc_ai, risk_ai, "Why is this risky?")
    assert "Credit Memo" in memo["title"]
    assert ans["answer"]
