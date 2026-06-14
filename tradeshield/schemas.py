from __future__ import annotations

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class CaseCreate(BaseModel):
    sme_name: str
    sme_email: str
    buyer_name: str
    supplier_name: str
    origin_country: str
    destination_country: str
    goods_description: str
    invoice_amount_hkd: float = Field(gt=0)
    requested_financing_hkd: float = Field(gt=0)
    payment_term_days: int = Field(default=45, ge=1, le=365)
    supplier_bank_account: str
    previous_supplier_bank_account: str | None = None


class DecisionRequest(BaseModel):
    decision: str
    approved_amount_hkd: float | None = None
    reason: str


class ESGRequest(BaseModel):
    certificate_id: str
    issuer: str
    expiry_date: str
    scope: str


class CaseOut(BaseModel):
    id: int
    case_ref: str
    sme_name: str
    buyer_name: str
    supplier_name: str
    origin_country: str
    destination_country: str
    invoice_amount_hkd: float
    requested_financing_hkd: float
    status: str
    settlement_status: str
    esg_status: str
    supplier_verified: bool
    shipment_verified: bool

    class Config:
        from_attributes = True
