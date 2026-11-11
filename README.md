# BOLBUS

**Speak. Confirm. Move.**

A functional local conductor-console prototype for a future voice-first ETM copilot. React + TypeScript + Vite + Tailwind, FastAPI, SQLAlchemy, SQLite and Pydantic. Manual entry is fully functional; speech/AI is not connected.

> DEMONSTRATION ONLY: DEMO-01 is a fictional corridor. All fares and concession rules are invented training data, not official BMTC information. Approval produces a demo database record, never a valid travel ticket.

## Quick start

Requires Python 3.12+ and Node 22+ with npm. From the repository root:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
npm ci --prefix frontend
```

Copy `.env.example` to `backend/.env` (the defaults also work without a file).

Terminal 1, with the virtual environment activated:

```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, from the repository root:

```bash
npm run dev --prefix frontend
```

Open **http://localhost:5173**. Interactive API contracts are at **http://127.0.0.1:8000/docs**. Vite proxies `/api` to FastAPI. On first backend start, tables and demo data are created automatically. SQLite persists at `backend/bolbus.db` when started as above. Stop the backend before deleting this file to reset the demo.

On Linux/macOS, `make setup`, `make backend`, `make frontend`, `make test`, and `make build` wrap these commands. For Windows use the explicit commands above and below.

## Try the workflow

1. Select Central → Lake, 2 passengers, Standard demo. Save the draft.
2. Validate. The invented total is ₹40 (4 stages × ₹5 × 2). Payment verification remains pending.
3. Check “I collected payment” and save verification.
4. Enter a conductor name, check the explicit approval box, then approve the demo request.
5. Find the record in the register, refresh, or restart the backend: it persists.
6. Try an incomplete/reversed journey for clarification, or Demo concession to require a separate manual eligibility check. Edit a nonterminal request to reset its quote and confirmations.

## Verification

```bash
# From root with virtual environment activated
python -m pytest
npm test --prefix frontend
npm run build --prefix frontend
```

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

The UI uses bundled Inter and Noto Kannada/Devanagari fonts without requiring a font CDN. It displays translated demo stop names, not a fully translated interface. No microphone recording is performed.

## Prototype boundaries

This is a local development simulator, not a production service. It has no authentication, trusted conductor identity, official fare ingestion, append-only audit trail, migrations, payment processing, ticket printing, ETM SDK, speech recognition, AI parsing, Gnani integration, or complete offline service-worker/sync support. Do not expose the unauthenticated API on a public network. See [architecture](docs/architecture.md) and [API contracts](docs/api.md) for next steps and precise behavior.
