# V6 Review Fixes

V6 is a fixed upgrade over V5.

## Bugs / demo blockers fixed

- `MODEL_VERSION` in the risk engine is now aligned with the seeded model registry: `TS-RISK-2026.05`.
- `/health` reports `6.0.0-enterprise-control-tower`.
- Browser asset cache-busting now uses `?v=6`.
- Audit CSV and PDF downloads no longer use unauthenticated `window.open`; the frontend fetches files with the session Bearer token and downloads a Blob.
- Audit CSV is accessible to Officer, Risk Manager, and Admin for demo judging.
- Legacy root `static/app.js` and `static/style.css` are now harmless stubs; the real frontend is modular under `static/js` and `static/css`.

## New V6 product additions

- Portfolio Stress Desk.
- Portfolio CSV export.
- Deterministic Banker Copilot Brief.
- Credit memo generator.
- Evidence bundle SHA-256 hash.
- Trade timeline.
- Clearer judge demo narrative.
- Expanded dashboard command-center summary.

## Validation performed in package build

- Python compile check over `tradeshield/`.
- Static file packaging check.
- Added `pytest.ini` so local `pytest` resolves the package root after installing requirements.
- No `.env` included in the zip.

You should still run Docker locally before pushing because the runtime database is created on your machine.
