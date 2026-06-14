# TradeShield Enterprise V6 — BOCHK Control Tower Edition

A production-oriented banking workflow prototype for the **BOCHK Challenge 2026**.

TradeShield turns each cross-border SME trade-finance request into a **Risk Passport**: one controlled case object joining document evidence, explainable risk scoring, fraud-network analytics, deterministic banker-copilot guidance, human decisioning, conditional settlement, ESG evidence, and tamper-evident audit history.

## Run

```bash
cp .env.example .env
sudo docker compose down -v --remove-orphans
sudo docker compose build app
sudo docker compose up
```

Open:

```text
http://127.0.0.1:8000/?v=6
```

Hard refresh the browser after upgrading:

```text
Ctrl+Shift+R
```

## Demo users

| Role | Email | Password |
|---|---|---|
| Officer | officer@tradeshield.ai | demo12345 |
| Risk Manager | manager@tradeshield.ai | demo12345 |
| SME | sme@tradeshield.ai | demo12345 |
| Admin | admin@tradeshield.ai | ChangeMe123! |

## V6 upgrades

- Fixed model-version mismatch: scoring now reports `TS-RISK-2026.05`.
- Fixed authenticated exports: audit CSV, portfolio CSV, and PDF report are downloaded with the Bearer token instead of unauthenticated `window.open`.
- Officer can download audit CSV for demo purposes.
- Added **Portfolio Stress Desk** with deterministic stress scenarios and top exposure table.
- Added **Banker Copilot Brief**: deterministic, no external LLM, converts Risk Passport into executive summary, decision position, questions, controls, and objection handling.
- Added **Credit Memo Generator** endpoint.
- Added **Evidence Bundle Hash** endpoint committing to case, documents, risk, fraud indicators, and audit hashes.
- Added **Trade Timeline** endpoint.
- Added portfolio CSV export.
- Updated frontend to V6 cache-busting and cleaner navigation.
- Replaced legacy root static JS/CSS with stubs so only modular V6 files are used.

## Core endpoints

```text
GET  /health
POST /auth/login
GET  /dashboard/summary
GET  /operations/command-center
GET  /portfolio/exposure
GET  /portfolio/stress
GET  /cases
POST /cases/{case_id}/score
GET  /cases/{case_id}/passport
GET  /cases/{case_id}/copilot
GET  /cases/{case_id}/credit-memo
GET  /cases/{case_id}/evidence-bundle
GET  /cases/{case_id}/timeline
POST /cases/{case_id}/decision
POST /cases/{case_id}/settlement/verify-supplier
POST /cases/{case_id}/settlement/verify-shipment
POST /cases/{case_id}/settlement/release
GET  /audit
GET  /exports/audit.csv
GET  /exports/portfolio.csv
GET  /cases/{case_id}/report.pdf
```

## Demo flow

1. Login as **Officer**.
2. Open **Case Queue**.
3. Select `TS-HK-VN-014` or `TS-HK-ID-021`.
4. Generate **Risk Passport**.
5. Open **Copilot Brief** and show banker questions + credit memo.
6. Open **Portfolio Stress** and show corridor exposure.
7. Record partial approval or escalation.
8. Verify supplier and shipment.
9. Release settlement where allowed.
10. Show audit chain, model registry, PDF report, audit CSV, and portfolio CSV.

## Safety wording

This is **not** an autonomous lending system and is **not** bank-certified production software. It is a production-oriented workflow prototype for competition demonstration and architecture review. All credit decisions remain human-controlled.
