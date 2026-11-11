# Working on BOLBUS

## Product invariants
- Label all training routes, fares and concessions as demonstration data. Never invent official BMTC information or integration claims.
- The conductor checks eligibility, collects payment and explicitly approves. Never infer approval from speech, payment, validation or a UI timeout.
- No extra hardware, passenger app, Aadhaar or biometric storage.
- Provider secrets stay on the backend. Never put credentials in VITE_* variables.
- No fake AI or speech results. Gnani speech may use documented APIs only; fixtures must be explicitly labeled and must never masquerade as live transcription.

## Structure and changes
- Keep HTTP wiring in backend/app/routes; business/state logic in services; contracts in schemas; persistence in models.
- Keep frontend network access in lib/api.ts, shared server state in ConsoleContext and page-specific form state in pages.
- Store monetary values as integer paise. Fare authority is server-side.
- Preserve optimistic versions, immutable terminal states, explicit errors and retry keys.
- Editing resets fare validation, payment and eligibility confirmations.
- Local drafts may be saved offline; do not silently replay approvals.
- Do not commit .env, databases, virtual environments, build outputs or node_modules.

## Checks
Run `python -m pytest` with backend dependencies installed, `npm test --prefix frontend`, and `npm run build --prefix frontend`. Add meaningful state/API tests when business behavior changes. Update docs/api.md when contracts change. Schema changes require a migration plan before use with valuable data; create_all is demo bootstrap only.


## Python runtime and Windows setup
- Standardize on Python 3.12, as selected by `.python-version` and CI. Do not assume Python 3.13/3.14 compatibility or upgrade dependencies to work around an interpreter mismatch.
- From the repository root in PowerShell: `py -3.12 -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt` and `.\.venv\Scripts\python.exe -m pip check`.
- Verify `.\.venv\Scripts\python.exe --version` reports 3.12. Existing virtual environments retain their original interpreter; stop servers, deactivate and rename an old environment before recreating it. Preserve databases and existing .env files.
- Run backend tests from root with `.\.venv\Scripts\python.exe -m pytest`. Start the server from `backend/` with `..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
- Direct interpreter paths avoid activation and execution-policy changes. On Linux/macOS create with `python3.12 -m venv .venv` and use `.venv/bin/python`.
