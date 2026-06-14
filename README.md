# BOC TradeShield Enterprise V4 — Bank Workflow Edition

This version is a product and workflow redesign, not just a feature patch.

## Product intuition

TradeShield is a cross-border SME trade-finance operating layer for BOCHK.

Every application becomes a **Risk Passport** containing:

- case profile and trade route;
- document evidence and SHA-256 evidence hashes;
- document consistency checks;
- explainable risk scoring;
- fraud-network indicators;
- human decision controls;
- conditional settlement controls;
- ESG verification;
- tamper-evident audit chain;
- model-governance record;
- PDF risk passport export.

The app should be presented as a **production-oriented banking workflow prototype**, not as a bank-certified production deployment.

## Why V4 exists

A hard review of earlier versions found that the UI was not intuitive enough and the product looked like isolated fintech buttons. V4 fixes that by organizing the system around the banking lifecycle:

```text
Case Intake → Document Evidence → Risk Passport → Human Decision → Conditional Settlement → Audit/Governance
```

## Run with Docker

```bash
cd ~/Desktop/BOCHK
unzip tradeshield_enterprise_v4_bank_workflow.zip
cd tradeshield_enterprise
cp .env.example .env
sudo docker compose down -v --remove-orphans
sudo docker compose build --no-cache app
sudo docker compose up
```

Open:

```text
http://127.0.0.1:8000
```

## Login accounts

| Role | Email | Password |
|---|---|---|
| Officer | officer@tradeshield.ai | demo12345 |
| Risk Manager | manager@tradeshield.ai | demo12345 |
| SME | sme@tradeshield.ai | demo12345 |
| Admin | admin@tradeshield.ai | ChangeMe123! |

Legacy aliases also work:

- officer@demo.local / demo12345
- manager@demo.local / demo12345
- sme@demo.local / demo12345

## Best live demo flow

1. Login as `officer@tradeshield.ai`.
2. Open Case Queue.
3. Select `TS-HK-VN-014` or `TS-HK-ID-021`.
4. Generate / Refresh Risk Passport.
5. Explain risk drivers and required controls.
6. Show Fraud Network.
7. Record Partial Approval.
8. Verify supplier account.
9. Verify shipment evidence.
10. Release conditional settlement.
11. Show Audit & Governance.
12. Download PDF Risk Passport.

## Reviewer-safe positioning

Say:

> TradeShield implements a production-oriented architecture and operating workflow. For bank deployment, it would integrate with BOCHK SSO, core banking, AML/KYC services, document repositories, SIEM, and model-governance infrastructure.

Do not say:

> This is already bank-certified production software.

## Local run without Docker

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn tradeshield.main:app --reload --host 0.0.0.0 --port 8000
```

Local mode defaults to SQLite unless `DATABASE_URL` is set.

## API docs

```text
http://127.0.0.1:8000/docs
```
