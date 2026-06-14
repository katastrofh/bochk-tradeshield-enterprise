from __future__ import annotations

import csv
import io
from datetime import datetime

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
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
from tradeshield.security import create_access_token, get_current_user, require_roles, verify_password
from tradeshield.seed import seed_data
from tradeshield.services.compliance import compliance_checklist
from tradeshield.services.copilot import case_copilot_brief
from tradeshield.services.counterparty import counterparty_dossier
from tradeshield.services.evidence import evidence_bundle, trade_timeline
from tradeshield.services.memo import credit_memo
from tradeshield.services.notifications import notification_feed
from tradeshield.services.portfolio import exposure_by_corridor, portfolio_summary, risk_matrix
from tradeshield.services.pricing import indicative_pricing
from tradeshield.services.scenario import stress_scenarios
from tradeshield.services.stress import portfolio_stress
from tradeshield.services.workflow import next_action, workflow_readiness, workflow_state
from tradeshield.services.ai_layer import document_ai_extract, risk_ai_explanation, genai_credit_memo, ask_case_ai
from tradeshield.storage import save_upload

settings = get_settings()
app = FastAPI(title=settings.app_name, version="6.0.0-enterprise-control-tower")

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


def _latest_risk(db: Session, case_id: int) -> RiskAssessment | None:
    return db.query(RiskAssessment).filter(RiskAssessment.case_id == case_id).order_by(RiskAssessment.id.desc()).first()


def _documents(db: Session, case_id: int) -> list[Document]:
    return db.query(Document).filter(Document.case_id == case_id).order_by(Document.id.asc()).all()


def _audits(db: Session, case_id: int) -> list[AuditEvent]:
    return db.query(AuditEvent).filter(AuditEvent.case_id == case_id).order_by(AuditEvent.id.asc()).all()


def _case_or_404(db: Session, case_id: int) -> TradeCase:
    case = db.get(TradeCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        user_count = db.query(User).count()
        case_count = db.query(TradeCase).count()
        model_count = db.query(ModelRegistry).count()
        audit_count = db.query(AuditEvent).count()
        chain = verify_audit_chain(db)
        return {
            "status": "ok",
            "database": "connected",
            "version": "6.0.0-enterprise-control-tower",
            "counts": {"users": user_count, "cases": case_count, "models": model_count, "audit_events": audit_count},
            "audit_chain": chain,
        }
    except Exception as exc:
        return {"status": "degraded", "database": "error", "error": str(exc)}


@app.get("/debug/seed-status")
def seed_status(db: Session = Depends(get_db), user: User = Depends(require_roles("ADMIN", "RISK_MANAGER", "OFFICER"))):
    return {
        "users": [{"email": u.email, "role": u.role, "active": u.is_active} for u in db.query(User).order_by(User.id.asc()).all()],
        "cases": [{"id": c.id, "case_ref": c.case_ref, "status": c.status, "sme": c.sme_name} for c in db.query(TradeCase).order_by(TradeCase.id.asc()).all()],
        "models": [{"name": m.model_name, "version": m.version, "status": m.validation_status} for m in db.query(ModelRegistry).order_by(ModelRegistry.id.asc()).all()],
        "audit_count": db.query(AuditEvent).count(),
        "generated_at": datetime.utcnow().isoformat(),
    }


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


@app.get("/dashboard/summary")
def dashboard_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return {
        "portfolio": portfolio_summary(db),
        "exposure_by_corridor": exposure_by_corridor(db),
        "audit_chain": verify_audit_chain(db),
        "operating_model": [
            "Case Intake", "Document Evidence", "Risk Passport", "Copilot Brief", "Human Decision", "Conditional Settlement", "Fraud Network", "Audit & Governance"
        ],
    }


@app.get("/portfolio/exposure")
def portfolio_exposure(db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    return {"summary": portfolio_summary(db), "corridors": exposure_by_corridor(db), "risk_matrix": risk_matrix(db)}


@app.get("/portfolio/stress")
def portfolio_stress_view(db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    return portfolio_stress(db)


@app.get("/governance/model-registry")
def model_registry(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(ModelRegistry).order_by(ModelRegistry.id.desc()).all()


@app.get("/operations/command-center")
def command_center(db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    cases = db.query(TradeCase).order_by(TradeCase.id.asc()).all()
    rows = []
    for c in cases:
        risk = _latest_risk(db, c.id)
        docs = _documents(db, c.id)
        rows.append({
            "case_ref": c.case_ref,
            "status": c.status,
            "risk": risk.category if risk else "UNSCORED",
            "next_action": next_action(c, risk, docs),
            "settlement_status": c.settlement_status,
            "assigned_officer": c.assigned_officer,
        })
    return {"queue": rows, "generated_at": datetime.utcnow().isoformat()}


@app.get("/cases")
def list_cases(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = db.query(TradeCase).order_by(TradeCase.id.asc())
    if user.role == "SME":
        query = query.filter(TradeCase.sme_email.in_([user.email, "sme@tradeshield.ai"]))
    cases = query.all()
    latest_risk = {}
    next_actions = {}
    for c in cases:
        r = _latest_risk(db, c.id)
        docs = _documents(db, c.id)
        latest_risk[c.id] = None if not r else {"score": r.overall_score, "category": r.category, "recommendation": r.recommendation, "recommended_amount_hkd": r.recommended_amount_hkd}
        next_actions[c.id] = next_action(c, r, docs)
    return {"cases": cases, "latest_risk": latest_risk, "next_actions": next_actions}


@app.post("/cases")
def create_case(payload: CaseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.requested_financing_hkd > payload.invoice_amount_hkd:
        raise HTTPException(status_code=400, detail="Requested financing cannot exceed invoice amount.")
    next_id = db.query(TradeCase).count() + 1
    case = TradeCase(case_ref=f"TS-NEW-{next_id:04d}", **payload.model_dump(), status=CaseStatus.SUBMITTED.value, assigned_officer="officer@tradeshield.ai")
    db.add(case)
    db.commit()
    db.refresh(case)
    record_event(db, actor=user, case_id=case.id, event_type="CASE_CREATED", event_summary=f"Case {case.case_ref} created.", payload=payload.model_dump())
    return case


@app.get("/cases/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _case_or_404(db, case_id)
    return {"case": case, "latest_risk": _latest_risk(db, case_id), "documents": _documents(db, case_id), "audit_events": _audits(db, case_id)}


@app.post("/cases/{case_id}/documents")
async def upload_document(case_id: int, doc_type: str = Form("INVOICE"), file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _case_or_404(db, case_id)
    content = await file.read()
    digest = sha256_bytes(content)
    storage_path, stored_name = save_upload(content, file.filename or "document.txt")
    text = content.decode("utf-8", errors="ignore")
    fields = parse_trade_document(text)
    flags = consistency_checks(case, fields)
    doc = Document(case_id=case.id, doc_type=doc_type, filename=file.filename or stored_name, file_hash=digest, storage_path=storage_path, extracted_fields=fields, consistency_flags=flags)
    db.add(doc)
    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(doc)
    record_event(db, actor=user, case_id=case.id, event_type="DOCUMENT_UPLOADED", event_summary=f"{doc_type} uploaded and parsed; SHA-256 evidence hash recorded.", payload={"filename": doc.filename, "hash": digest, "flags": flags, "fields": fields})
    return doc


@app.get("/documents/templates")
def document_templates(user: User = Depends(get_current_user)):
    return {"templates": [
        {"type": "INVOICE", "required_fields": ["invoice_no", "buyer", "supplier", "amount", "currency", "due_date"]},
        {"type": "PURCHASE_ORDER", "required_fields": ["po_no", "buyer", "supplier", "goods", "amount"]},
        {"type": "BILL_OF_LADING", "required_fields": ["vessel", "origin", "destination", "goods", "ship_date"]},
        {"type": "ESG_CERTIFICATE", "required_fields": ["issuer", "certificate_id", "scope", "expiry_date"]},
    ]}


@app.post("/cases/{case_id}/score")
def score_case(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    graph = build_fraud_graph(db, case)
    docs = _documents(db, case.id)
    result = calculate_risk(case, docs, graph.get("indicators", []))
    risk = RiskAssessment(case_id=case.id, model_version=MODEL_VERSION, overall_score=result.overall_score, category=result.category, recommendation=result.recommendation, recommended_amount_hkd=result.recommended_amount_hkd, required_actions=result.required_actions, sub_scores=result.sub_scores, risk_drivers=result.risk_drivers, mitigating_factors=result.mitigating_factors, fraud_indicators=result.fraud_indicators, narrative=result.narrative)
    db.add(risk)
    case.status = CaseStatus.SCORED.value if result.category != "HIGH" else CaseStatus.ESCALATED.value
    case.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(risk)
    record_event(db, actor=user, case_id=case.id, event_type="RISK_SCORED", event_summary=f"Risk passport generated: {result.category} risk, {result.recommendation}.", payload={"score": result.overall_score, "model_version": MODEL_VERSION, "recommendation": result.recommendation})
    return risk


@app.get("/cases/{case_id}/passport")
def risk_passport(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _case_or_404(db, case_id)
    risk = _latest_risk(db, case_id)
    docs = _documents(db, case_id)
    graph = build_fraud_graph(db, case)
    audits = _audits(db, case_id)
    workflow = workflow_state(case, risk, docs, audits)
    return {"case": case, "latest_risk": risk, "documents": docs, "fraud_graph": graph, "workflow": workflow, "readiness": workflow_readiness(case, risk, docs, audits), "pricing": indicative_pricing(case, risk), "compliance": compliance_checklist(case, risk, graph), "counterparty": counterparty_dossier(db, case), "notifications": notification_feed(case, risk), "audit_chain": verify_audit_chain(db)}


@app.get("/cases/{case_id}/copilot")
def copilot(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    risk = _latest_risk(db, case_id)
    docs = _documents(db, case_id)
    graph = build_fraud_graph(db, case)
    comp = compliance_checklist(case, risk, graph)
    price = indicative_pricing(case, risk)
    return case_copilot_brief(case, risk, docs, graph, comp, price)


@app.get("/cases/{case_id}/evidence-bundle")
def evidence(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    return evidence_bundle(case, _latest_risk(db, case_id), _documents(db, case_id), _audits(db, case_id), build_fraud_graph(db, case))


@app.get("/cases/{case_id}/timeline")
def timeline(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _case_or_404(db, case_id)
    return trade_timeline(case, _latest_risk(db, case_id), _documents(db, case_id), _audits(db, case_id))


@app.get("/cases/{case_id}/credit-memo")
def memo(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    risk = _latest_risk(db, case_id)
    docs = _documents(db, case_id)
    audits = _audits(db, case_id)
    graph = build_fraud_graph(db, case)
    comp = compliance_checklist(case, risk, graph)
    price = indicative_pricing(case, risk)
    evidence = evidence_bundle(case, risk, docs, audits, graph)
    brief = case_copilot_brief(case, risk, docs, graph, comp, price)
    return credit_memo(case, risk, comp, price, evidence, brief)


@app.get("/cases/{case_id}/workflow")
def workflow(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _case_or_404(db, case_id)
    return workflow_readiness(case, _latest_risk(db, case_id), _documents(db, case_id), _audits(db, case_id))


@app.get("/cases/{case_id}/compliance-checklist")
def compliance(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    return compliance_checklist(case, _latest_risk(db, case_id), build_fraud_graph(db, case))


@app.get("/cases/{case_id}/pricing")
def pricing(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    return indicative_pricing(case, _latest_risk(db, case_id))


@app.get("/cases/{case_id}/scenario")
def scenario(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    return stress_scenarios(case, _latest_risk(db, case_id))


@app.get("/cases/{case_id}/counterparty-dossier")
def counterparty(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    return counterparty_dossier(db, _case_or_404(db, case_id))


@app.get("/cases/{case_id}/notifications")
def notifications(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _case_or_404(db, case_id)
    return {"items": notification_feed(case, _latest_risk(db, case_id))}


@app.post("/cases/{case_id}/decision")
def decide(case_id: int, payload: DecisionRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    risk = _latest_risk(db, case_id)
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
    case.status = {"APPROVE": CaseStatus.APPROVED.value, "PARTIAL_APPROVE": CaseStatus.PARTIALLY_APPROVED.value, "REJECT": CaseStatus.REJECTED.value, "ESCALATE": CaseStatus.ESCALATED.value}[decision]
    case.updated_at = datetime.utcnow()
    db.commit()
    record_event(db, actor=user, case_id=case.id, event_type="HUMAN_DECISION", event_summary=f"Decision recorded: {decision}.", payload=payload.model_dump())
    return case


@app.post("/cases/{case_id}/settlement/verify-supplier")
def verify_supplier(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    case.supplier_verified = True
    if case.shipment_verified and case.status in {CaseStatus.APPROVED.value, CaseStatus.PARTIALLY_APPROVED.value}:
        case.settlement_status = "READY_TO_RELEASE"
    case.updated_at = datetime.utcnow()
    db.commit()
    record_event(db, actor=user, case_id=case.id, event_type="SUPPLIER_VERIFIED", event_summary="Supplier beneficiary account verified.")
    return case


@app.post("/cases/{case_id}/settlement/verify-shipment")
def verify_shipment(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    case.shipment_verified = True
    case.shipment_status = "VERIFIED"
    if case.supplier_verified and case.status in {CaseStatus.APPROVED.value, CaseStatus.PARTIALLY_APPROVED.value}:
        case.settlement_status = "READY_TO_RELEASE"
    case.updated_at = datetime.utcnow()
    db.commit()
    record_event(db, actor=user, case_id=case.id, event_type="SHIPMENT_VERIFIED", event_summary="Shipment evidence verified.")
    return case


@app.post("/cases/{case_id}/settlement/release")
def release(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    if case.status not in {CaseStatus.APPROVED.value, CaseStatus.PARTIALLY_APPROVED.value}:
        raise HTTPException(status_code=400, detail="Settlement requires approved or partially approved case.")
    if not (case.supplier_verified and case.shipment_verified):
        raise HTTPException(status_code=400, detail="Supplier and shipment verification are required before release.")
    case.settlement_status = "RELEASED"
    case.status = CaseStatus.SETTLED.value
    case.updated_at = datetime.utcnow()
    db.commit()
    record_event(db, actor=user, case_id=case.id, event_type="SETTLEMENT_RELEASED", event_summary=f"Conditional settlement released: HK${case.approved_amount_hkd:,.0f}.")
    return case


@app.post("/cases/{case_id}/esg/verify")
def verify_esg(case_id: int, payload: ESGRequest, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    case.esg_status = "VERIFIED"
    case.esg_summary = f"{payload.issuer} certificate {payload.certificate_id}, scope: {payload.scope}, expires {payload.expiry_date}."
    case.updated_at = datetime.utcnow()
    db.commit()
    record_event(db, actor=user, case_id=case.id, event_type="ESG_VERIFIED", event_summary="ESG certificate verified.", payload=payload.model_dump())
    return case


@app.get("/cases/{case_id}/fraud-graph")
def fraud_graph(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return build_fraud_graph(db, _case_or_404(db, case_id))


@app.get("/audit")
def audit(db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    events = db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(100).all()
    return {"chain": verify_audit_chain(db), "events": events}


@app.get("/exports/audit.csv")
def audit_csv(db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "case_id", "actor_email", "actor_role", "event_type", "event_summary", "event_hash", "created_at"])
    for ev in db.query(AuditEvent).order_by(AuditEvent.id.asc()).all():
        writer.writerow([ev.id, ev.case_id, ev.actor_email, ev.actor_role, ev.event_type, ev.event_summary, ev.event_hash, ev.created_at])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=tradeshield_audit.csv"})


@app.get("/exports/portfolio.csv")
def portfolio_csv(db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    rows = risk_matrix(db)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["case_ref", "sme", "corridor", "requested_hkd", "status", "decision", "settlement_status", "risk_category", "risk_score", "recommended_amount_hkd"])
    for row in rows:
        writer.writerow([row["case_ref"], row["sme"], row["corridor"], row["requested_hkd"], row["status"], row["decision"], row["settlement_status"], row["risk_category"], row["risk_score"], row["recommended_amount_hkd"]])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=tradeshield_portfolio.csv"})


@app.get("/cases/{case_id}/report.pdf")
def report(case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    case = _case_or_404(db, case_id)
    risk = _latest_risk(db, case_id)
    audits = _audits(db, case_id)
    pdf = risk_passport_pdf(case, risk, audits)
    record_event(db, actor=user, case_id=case_id, event_type="REPORT_EXPORTED", event_summary="Risk Passport PDF exported.")
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={case.case_ref}_risk_passport.pdf"})


@app.get("/ai/cases/{case_id}/document-intelligence")
def ai_document_intelligence(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    return document_ai_extract(case, _documents(db, case_id))


@app.get("/ai/cases/{case_id}/risk-explanation")
def ai_risk_view(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    risk = _latest_risk(db, case_id)
    docs = _documents(db, case_id)
    graph = build_fraud_graph(db, case)
    return risk_ai_explanation(case, risk, docs, graph)


@app.get("/ai/cases/{case_id}/genai-memo")
def ai_genai_memo(case_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    risk = _latest_risk(db, case_id)
    docs = _documents(db, case_id)
    graph = build_fraud_graph(db, case)
    doc_ai = document_ai_extract(case, docs)
    risk_ai = risk_ai_explanation(case, risk, docs, graph)
    return genai_credit_memo(case, risk, doc_ai, risk_ai)


@app.post("/ai/cases/{case_id}/ask")
def ai_ask_case(case_id: int, question: str = Form(...), db: Session = Depends(get_db), user: User = Depends(require_roles("OFFICER", "RISK_MANAGER", "ADMIN"))):
    case = _case_or_404(db, case_id)
    risk = _latest_risk(db, case_id)
    docs = _documents(db, case_id)
    graph = build_fraud_graph(db, case)
    doc_ai = document_ai_extract(case, docs)
    risk_ai = risk_ai_explanation(case, risk, docs, graph)
    return ask_case_ai(case, risk, doc_ai, risk_ai, question)
