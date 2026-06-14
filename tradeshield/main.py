from __future__ import annotations

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from tradeshield.audit import record_event, verify_audit_chain
from tradeshield.config import get_settings
from tradeshield.database import get_db, init_db
from tradeshield.document_parser import consistency_checks, parse_trade_document, sha256_bytes
from tradeshield.fraud_graph import build_fraud_graph
from tradeshield.models import AuditEvent, CaseStatus, Decision, Document, ModelRegistry, RiskAssessment, TradeCase, User
from tradeshield.reporting import risk_passport_pdf
from tradeshield.risk_engine import MODEL_VERSION, calculate_risk
from tradeshield.schemas import CaseCreate, DecisionRequest, ESGRequest, Token
from tradeshield.security import create_access_token, get_current_user, hash_password, require_roles, verify_password
from tradeshield.seed import seed_data
from tradeshield.storage import save_upload

settings = get_settings()
app = FastAPI(title=settings.app_name, version="4.0.0-bank-workflow-edition")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_origins == "*" else [settings.cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    db = next(get_db())
    try:
        seed_data(db)
    finally:
        db.close()


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    return {"status": "ok", "audit": verify_audit_chain(db)}


@app.post("/auth/login", response_model=Token)
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.email, user.role)
    record_event(db, actor=user, event_type="LOGIN", event_summary=f"{user.email} logged in.")
    return Token(access_token=token, role=user.role, email=user.email, full_name=user.full_name)


@app.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"email": user.email, "role": user.role, "full_name": user.full_name}


@app.get("/governance/model-registry")
def model_registry(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(ModelRegistry).order_by(ModelRegistry.id.desc()).all()


@app.get("/cases")
def list_cases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(TradeCase).order_by(TradeCase.id.asc())
    if user.role == "SME":
        query = query.filter(TradeCase.sme_email.in_([user.email, "sme@tradeshield.ai"]))
    cases = query.all()
    latest_risk = {}
    for c in cases:
        r = db.query(RiskAssessment).filter(RiskAssessment.case_id == c.id).order_by(RiskAssessment.id.desc()).first()
        latest_risk[c.id] = None if not r else {"score": r.overall_score, "category": r.category, "recommendation": r.recommendation}
    return {"cases": cases, "latest_risk": latest_risk}


@app.post("/cases")
def create_case(payload: CaseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.requested_financing_hkd > payload.invoice_amount_hkd:
        raise HTTPException(status_code=400, detail="Requested financing cannot exceed invoice amount.")
    next_id = db.query(TradeCase).count() + 1
    case = TradeCase(case_ref=f"TS-NEW-{next_id:04d}", **payload.model_dump(), status=CaseStatus.SUBMITTED.value)
    db.add(case)
    db.commit()
    db.refresh(case)
    record_event(db, actor=user, case_id=case.id, event_type="CASE_CREATED", event_summary=f"Case {case.case_ref} created.", payload=payload.model_dump())
    return case


@app.get("/cases/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    risk = db.query(RiskAssessment).filter(RiskAssessment.case_id == case_id).order_by(RiskAssessment.id.desc()).first()
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    audits = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.id.asc()).all()
    return {"case": case, "latest_risk": risk, "documents": docs, "audit_events": audits}


@app.post("/cases/{case_id}/documents")
async def upload_document(
    case_id: int,
    doc_type: str = Form("INVOICE"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    content = await file.read()
    digest = sha256_bytes(content)
    storage_path, stored_name = save_upload(content, file.filename or "document.txt")
    try:
        text = content.decode("utf-8", errors="ignore")
    except Exception:
        text = ""
    fields = parse_trade_document(text)
    flags = consistency_checks(case, fields)
    doc = Document(
        case_id=case.id,
        doc_type=doc_type,
        filename=file.filename or stored_name,
        file_hash=digest,
        storage_path=storage_path,
        extracted_fields=fields,
        consistency_flags=flags,
    )
    db.add(doc)
    case.updated_at = __import__("datetime").datetime.utcnow()
    db.commit()
    db.refresh(doc)
    record_event(
        db,
        actor=user,
        case_id=case.id,
        event_type="DOCUMENT_UPLOADED",
        event_summary=f"{doc_type} uploaded and parsed; SHA-256 evidence hash recorded.",
        payload={"filename": doc.filename, "hash": digest, "flags": flags, "fields": fields},
    )
    return doc


@app.post("/cases/{case_id}/score")
def score_case(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    graph = build_fraud_graph(db, case)
    docs = db.query(Document).filter(Document.case_id == case.id).all()
    result = calculate_risk(case, docs, graph.get("indicators", []))
    risk = RiskAssessment(
        case_id=case.id,
        model_version=MODEL_VERSION,
        overall_score=result.overall_score,
        category=result.category,
        recommendation=result.recommendation,
        recommended_amount_hkd=result.recommended_amount_hkd,
        required_actions=result.required_actions,
        sub_scores=result.sub_scores,
        risk_drivers=result.risk_drivers,
        mitigating_factors=result.mitigating_factors,
        fraud_indicators=result.fraud_indicators,
        narrative=result.narrative,
    )
    db.add(risk)
    case.status = CaseStatus.SCORED.value if result.category != "HIGH" else CaseStatus.ESCALATED.value
    db.commit()
    db.refresh(risk)
    record_event(
        db,
        actor=user,
        case_id=case.id,
        event_type="RISK_SCORED",
        event_summary=f"Risk passport generated: {result.category} risk, {result.recommendation}.",
        payload={"score": result.overall_score, "model_version": MODEL_VERSION, "recommendation": result.recommendation},
    )
    return risk


@app.get("/cases/{case_id}/passport")
def risk_passport(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    risk = db.query(RiskAssessment).filter(RiskAssessment.case_id == case_id).order_by(RiskAssessment.id.desc()).first()
    docs = db.query(Document).filter(Document.case_id == case_id).all()
    graph = build_fraud_graph(db, case)
    audits = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.id.asc()).all()
    workflow = [
        {"step": "Case intake", "complete": case.status != "DRAFT"},
        {"step": "Document evidence", "complete": len(docs) > 0},
        {"step": "Risk scoring", "complete": risk is not None},
        {"step": "Human decision", "complete": case.decision is not None},
        {"step": "Settlement controls", "complete": case.settlement_status in ["READY_TO_RELEASE", "RELEASED"]},
        {"step": "Audit proof", "complete": len(audits) > 0},
    ]
    return {
        "case": case,
        "latest_risk": risk,
        "documents": docs,
        "fraud_graph": graph,
        "workflow": workflow,
        "audit_chain": verify_audit_chain(db),
    }


@app.post("/cases/{case_id}/decision")
def decide(case_id: int, payload: DecisionRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    risk = db.query(RiskAssessment).filter(RiskAssessment.case_id == case_id).order_by(RiskAssessment.id.desc()).first()
    if not risk:
        raise HTTPException(status_code=400, detail="Generate a risk passport before decisioning.")
    decision = payload.decision.upper()
    if decision not in {d.value for d in Decision}:
        raise HTTPException(status_code=400, detail="Invalid decision.")
    if risk.category == "HIGH" and decision in {"APPROVE", "PARTIAL_APPROVE"} and user.role not in {"RISK_MANAGER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="High-risk cases require risk-manager approval.")
    if decision in {"APPROVE", "PARTIAL_APPROVE"}:
        if payload.approved_amount_hkd is None or payload.approved_amount_hkd <= 0:
            raise HTTPException(status_code=400, detail="Approved amount is required.")
        if payload.approved_amount_hkd > case.requested_financing_hkd or payload.approved_amount_hkd > case.invoice_amount_hkd:
            raise HTTPException(status_code=400, detail="Approved amount cannot exceed requested financing or invoice amount.")
        case.approved_amount_hkd = payload.approved_amount_hkd
        case.settlement_status = "PENDING_CONDITIONS"
    else:
        case.approved_amount_hkd = 0
        case.settlement_status = "BLOCKED"

    case.decision = decision
    case.decision_reason = payload.reason
    if decision == "APPROVE":
        case.status = CaseStatus.APPROVED.value
    elif decision == "PARTIAL_APPROVE":
        case.status = CaseStatus.PARTIALLY_APPROVED.value
    elif decision == "REJECT":
        case.status = CaseStatus.REJECTED.value
    else:
        case.status = CaseStatus.ESCALATED.value
    db.commit()
    record_event(db, actor=user, case_id=case.id, event_type="HUMAN_DECISION", event_summary=f"Decision recorded: {decision}.", payload=payload.model_dump())
    return case


@app.post("/cases/{case_id}/settlement/verify-supplier")
def verify_supplier(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.supplier_verified = True
    if case.shipment_verified and case.status in {CaseStatus.APPROVED.value, CaseStatus.PARTIALLY_APPROVED.value}:
        case.settlement_status = "READY_TO_RELEASE"
    db.commit()
    record_event(db, actor=user, case_id=case.id, event_type="SUPPLIER_VERIFIED", event_summary="Supplier beneficiary account verified.")
    return case


@app.post("/cases/{case_id}/settlement/verify-shipment")
def verify_shipment(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.shipment_verified = True
    case.shipment_status = "VERIFIED"
    if case.supplier_verified and case.status in {CaseStatus.APPROVED.value, CaseStatus.PARTIALLY_APPROVED.value}:
        case.settlement_status = "READY_TO_RELEASE"
    db.commit()
    record_event(db, actor=user, case_id=case.id, event_type="SHIPMENT_VERIFIED", event_summary="Shipment evidence verified.")
    return case


@app.post("/cases/{case_id}/settlement/release")
def release(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.status not in {CaseStatus.APPROVED.value, CaseStatus.PARTIALLY_APPROVED.value}:
        raise HTTPException(status_code=400, detail="Settlement requires approved or partially approved case.")
    if not (case.supplier_verified and case.shipment_verified):
        raise HTTPException(status_code=400, detail="Supplier and shipment verification are required before release.")
    case.settlement_status = "RELEASED"
    case.status = CaseStatus.SETTLED.value
    db.commit()
    record_event(db, actor=user, case_id=case.id, event_type="SETTLEMENT_RELEASED", event_summary=f"Conditional settlement released: HK${case.approved_amount_hkd:,.0f}.")
    return case


@app.post("/cases/{case_id}/esg/verify")
def verify_esg(case_id: int, payload: ESGRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case.esg_status = "VERIFIED"
    case.esg_summary = f"{payload.issuer} certificate {payload.certificate_id}, scope: {payload.scope}, expires {payload.expiry_date}."
    db.commit()
    record_event(db, actor=user, case_id=case.id, event_type="ESG_VERIFIED", event_summary="ESG certificate verified.", payload=payload.model_dump())
    return case


@app.get("/cases/{case_id}/fraud-graph")
def fraud_graph(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return build_fraud_graph(db, case)


@app.get("/audit")
def audit(db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    events = db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(100).all()
    return {"chain": verify_audit_chain(db), "events": events}


@app.get("/cases/{case_id}/report.pdf")
def report(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    risk = db.query(RiskAssessment).filter(RiskAssessment.case_id == case_id).order_by(RiskAssessment.id.desc()).first()
    audits = db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.id.asc()).all()
    pdf = risk_passport_pdf(case, risk, audits)
    record_event(db, actor=user, case_id=case_id, event_type="REPORT_EXPORTED", event_summary="Risk Passport PDF exported.")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={case.case_ref}_risk_passport.pdf"},
    )
