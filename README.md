# BOLBUS

**Speak. Confirm. Move.**

A functional local conductor-console prototype for a future voice-first ETM copilot. React + TypeScript + Vite + Tailwind, FastAPI, SQLAlchemy, SQLite and Pydantic. Manual entry is functional. Optional Gnani REST speech capture and deterministic text extraction are documented in [speech integration](docs/speech.md); live service requires a server-side key.

> DEMONSTRATION ONLY: DEMO-01 is a fictional corridor. All fares and concession rules are invented training data, not official BMTC information. Approval produces a demo database record, never a valid travel ticket.

## Quick start

Use **Python 3.12** for the backend and Node 22+ with npm. Python 3.14 is not supported by the current dependency set: the reported SQLAlchemy 2.0.36 model initialization error occurred on Python 3.14.5. Do not use an unqualified `python -m venv` when multiple Python versions are installed. `.python-version` selects 3.12 for compatible version managers; it does not install Python or change an existing virtual environment. CI also uses Python 3.12.

### Windows PowerShell

Install Python 3.12, then run from the repository root:

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip check
npm ci --prefix frontend
Copy-Item .env.example backend\.env
```

If `.venv` was created using Python 3.14, stop running servers and deactivate it first (run `deactivate` if activated). Rename it with `Rename-Item .venv .venv-python314-backup`, then create the new environment with `py -3.12 -m venv .venv`. Reinstall requirements; do not reuse the old environment's site-packages. Your SQLite database and `.env` are outside `.venv`; keep them. Only copy `.env.example` if `backend/.env` does not already exist.

Terminal 1, from the repository root:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, from the repository root:

```powershell
npm run dev --prefix frontend
```

These commands use the virtual environment directly, so activation and PowerShell execution-policy changes are unnecessary.

### Linux/macOS

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
# Only if backend/.env does not already exist:
cp .env.example backend/.env
cd backend
../.venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run `npm run dev --prefix frontend` in another terminal from the repository root. `make setup` requires `python` to resolve to Python 3.12; otherwise use the explicit commands above.

Open **http://127.0.0.1:5173**. Interactive API contracts are at **http://127.0.0.1:8000/docs**. Vite proxies `/api` to FastAPI. On first backend start, tables and demo data are created automatically. SQLite persists at `backend/bolbus.db` when started as above. Stop the backend before deleting this file to reset the demo.

## Try the workflow

1. Select Central → Lake, 2 passengers, Standard demo. Save the draft.
2. Validate. The invented total is ₹40 (4 stages × ₹5 × 2). Payment verification remains pending.
3. Check “I collected payment” and save verification.
4. Enter a conductor name, check the explicit approval box, then approve the demo request.
5. Find the record in the register, refresh, or restart the backend: it persists.
6. Try an incomplete/reversed journey for clarification, or Demo concession to require a separate manual eligibility check. Edit a nonterminal request to reset its quote and confirmations.

## Verification

```powershell
# Windows PowerShell, from repository root
.\.venv\Scripts\python.exe -m pytest
npm test --prefix frontend
npm run build --prefix frontend
```

On Linux/macOS run `.venv/bin/python -m pytest` from the root.

Backend tests cover state transitions, malformed data, route membership, concession/payment gating, stale updates, terminal immutability, persistence reads and retry safety. Frontend tests exercise the conductor flow, explicit approval, draft recovery and network/conflict errors. GitHub Actions runs both suites and the TypeScript/Vite build.

## Structure

```text
backend/app/
  config.py, database.py, main.py
  models/      SQLAlchemy persistence
  schemas/     Pydantic contracts
  services/    demo seed, state and fare logic
  routes/      HTTP endpoints
frontend/src/
  components/  journey fields and status
  pages/       create, register, detail
  lib/         typed API, types, draft storage
  state/       shared console context
  workflow.test.tsx
tests/backend/  API regression tests
docs/           architecture, contracts, scope
```

## Connectivity and safety

The browser retains the unsaved manual draft in local storage, including its stable creation key. Connectivity errors are visible, requests time out, and mutations are not automatically queued or replayed. After an uncertain action, refresh the register before retrying. Server-side validation is authoritative. Local storage is best effort and shared on that browser profile; do not enter personal passenger data. Clearing storage removes recovery.

The UI uses bundled Inter and Noto Kannada/Devanagari fonts without requiring a font CDN. It displays translated demo stop names, not a fully translated interface. Microphone recording occurs only after an explicit Record action on the speech screen; manual entry does not activate it.

## Prototype boundaries

This is a local development simulator, not a production service. It has no authentication, trusted conductor identity, official fare ingestion, payment processing, ticket printing, ETM SDK, general AI language understanding, or complete offline service-worker/sync support. Do not expose the unauthenticated API on a public network. See [architecture](docs/architecture.md) and [API contracts](docs/api.md) for next steps and precise behavior.


## Deterministic engine

See [ticket engine](docs/ticket-engine.md) for fare-table provenance, exact journey prices, Shakti-style demo checks, API additions, audit evidence and migration details. New and existing SQLite databases are initialized with an additive migration at startup; existing records are preserved. Quotes and approved simulated tickets carry frozen source/version/date information. Missing fares block approval. No official fare or concession dataset is connected.


## Speech and manual text

Open Voice entry on Home. Set `SPEECH_MODE=gnani` and `GNANI_API_KEY` in `backend/.env` to enable the documented API adapter, or `SPEECH_MODE=fixture` for explicitly labeled developer samples. Text extraction works with speech disabled. See [speech setup and validation](docs/speech.md). No live Gnani test was possible without credentials.
