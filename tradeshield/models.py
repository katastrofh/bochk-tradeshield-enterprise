from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tradeshield.database import Base


class Role(str, enum.Enum):
    SME = "SME"
    OFFICER = "OFFICER"
    RISK_MANAGER = "RISK_MANAGER"
    ADMIN = "ADMIN"


class CaseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    SCORED = "SCORED"
    ESCALATED = "ESCALATED"
    APPROVED = "APPROVED"
    PARTIALLY_APPROVED = "PARTIALLY_APPROVED"
    REJECTED = "REJECTED"
    SETTLED = "SETTLED"


class Decision(str, enum.Enum):
    APPROVE = "APPROVE"
    PARTIAL_APPROVE = "PARTIAL_APPROVE"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TradeCase(Base):
    __tablename__ = "trade_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_ref: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sme_name: Mapped[str] = mapped_column(String(255))
    sme_email: Mapped[str] = mapped_column(String(255), index=True)
    buyer_name: Mapped[str] = mapped_column(String(255))
    supplier_name: Mapped[str] = mapped_column(String(255))
    origin_country: Mapped[str] = mapped_column(String(128))
    destination_country: Mapped[str] = mapped_column(String(128))
    goods_description: Mapped[str] = mapped_column(String(255))
    invoice_amount_hkd: Mapped[float] = mapped_column(Float)
    requested_financing_hkd: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(12), default="HKD")
    payment_term_days: Mapped[int] = mapped_column(Integer, default=45)
    supplier_bank_account: Mapped[str] = mapped_column(String(128))
    previous_supplier_bank_account: Mapped[str | None] = mapped_column(String(128), nullable=True)
    shipment_status: Mapped[str] = mapped_column(String(64), default="PENDING")
    status: Mapped[str] = mapped_column(String(64), default=CaseStatus.SUBMITTED.value, index=True)
    assigned_officer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_amount_hkd: Mapped[float | None] = mapped_column(Float, nullable=True)
    settlement_status: Mapped[str] = mapped_column(String(64), default="NOT_READY")
    supplier_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    shipment_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    esg_status: Mapped[str] = mapped_column(String(64), default="NOT_SUBMITTED")
    esg_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    documents: Mapped[list["Document"]] = relationship("Document", back_populates="case", cascade="all, delete-orphan")
    risks: Mapped[list["RiskAssessment"]] = relationship("RiskAssessment", back_populates="case", cascade="all, delete-orphan")
    audits: Mapped[list["AuditEvent"]] = relationship("AuditEvent", back_populates="case", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("trade_cases.id"))
    doc_type: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    storage_path: Mapped[str] = mapped_column(String(512))
    extracted_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    consistency_flags: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped[TradeCase] = relationship("TradeCase", back_populates="documents")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("trade_cases.id"))
    model_version: Mapped[str] = mapped_column(String(64))
    overall_score: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(64))
    recommendation: Mapped[str] = mapped_column(String(64))
    recommended_amount_hkd: Mapped[float] = mapped_column(Float)
    required_actions: Mapped[list] = mapped_column(JSON, default=list)
    sub_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_drivers: Mapped[list] = mapped_column(JSON, default=list)
    mitigating_factors: Mapped[list] = mapped_column(JSON, default=list)
    fraud_indicators: Mapped[list] = mapped_column(JSON, default=list)
    narrative: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped[TradeCase] = relationship("TradeCase", back_populates="risks")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("trade_cases.id"), nullable=True)
    actor_email: Mapped[str] = mapped_column(String(255))
    actor_role: Mapped[str] = mapped_column(String(64))
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    event_summary: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    previous_hash: Mapped[str] = mapped_column(String(64))
    event_hash: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    case: Mapped[TradeCase | None] = relationship("TradeCase", back_populates="audits")


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_name: Mapped[str] = mapped_column(String(255))
    version: Mapped[str] = mapped_column(String(64), unique=True)
    purpose: Mapped[str] = mapped_column(Text)
    validation_status: Mapped[str] = mapped_column(Text)
    limitations: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
