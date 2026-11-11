# Working on BOLBUS

## Product invariants
- Label all training routes, fares and concessions as demonstration data. Never invent official BMTC information or integration claims.
- The conductor checks eligibility, collects payment and explicitly approves. Never infer approval from speech, payment, validation or a UI timeout.
- No extra hardware, passenger app, Aadhaar or biometric storage.
- Provider secrets stay on the backend. Never put credentials in VITE_* variables.
- No fake AI or speech results. Gnani is outside the foundation scope.

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
