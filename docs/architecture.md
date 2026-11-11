# Architecture and scope

React Router provides create, register and request detail pages. ConsoleContext shares route/request data, mutation status and errors; forms keep local state. Typed API utilities send JSON through the Vite proxy to FastAPI. HTTP routes delegate to services, Pydantic schemas and SQLAlchemy models. SQLite stores routes, ordered multilingual stops, fare rules and requests with foreign keys.

## State machine

| Current state | Action | Result |
| --- | --- | --- |
| new | create | draft |
| any nonterminal | edit | draft; reset quote, payment and eligibility confirmations |
| any nonterminal | validate | needs-clarification for missing/reversed stops; otherwise pending-verification or ready-for-approval |
| pending-verification / ready-for-approval | verify | recalculate quote and readiness from explicit manual flags |
| ready-for-approval | approve | revalidate and mark approved with name and UTC time |
| any nonterminal | cancel | cancelled |
| approved / cancelled | mutation | rejected, except a narrow idempotent approval retry |

The fictional corridor travels in increasing stop order. Passenger count is 1–20. Invented standard fares are 500 paise per stage per passenger; invented demo concessions are 250 paise and require a manual eligibility check. All valid journeys also require payment confirmation. Approval never creates a real travel ticket.

## Consistency and connectivity

Requests use UUID IDs, unique client creation UUIDs, integer paise, UTC timestamps and optimistic SQLAlchemy versions. Mutations require the last-read version; stale reads and database write races return 409. SQLite foreign keys and busy timeout are enabled; lock/unavailability returns 503. `create_all` and an idempotent demo seed bootstrap fresh databases, not schema migrations.

The unsaved browser draft is retained in local storage. Corrupt drafts are ignored; unavailable storage displays a warning. Changing fields rotates the creation key. Identical creation retries return the existing request; a reused key with changed data conflicts. The browser does not automatically replay mutations. After an uncertain response refresh the register. Only approval retries with the immediately previous version and same conductor name return the existing approved record. Conductor names are self-declared demo labels, not authenticated identities.

Network indicators describe browser connectivity, not server health. Fetch failures/timeouts surface separately. Saved request edits have no offline recovery. There is no service worker or cached offline application delivery. The register shows the latest 100; API limit/offset supports future pagination. Local storage is shared on the browser profile; no passenger identity or audio should be entered.

## Implemented

Persistent demo catalog and requests; manual journey entry; multilingual stop labels; deterministic disclosed fares; clarification, verification, approval and cancellation; terminal immutability; retry safety and version checks; local draft recovery; visible errors; tests and CI.

## Not implemented

Speech recording/transcription, AI interpretation/confidence, Gnani, official route/fare/concession ingestion, ETM SDK, printing, payment gateway, authentication/authorization, append-only event audit, historical fare versions, database migrations, full UI translation, complete offline sync, production telemetry and rate limits. None are represented as live integrations. Before operational deployment add authenticated approval, trusted fare ingestion, Alembic migrations, quote provenance and an immutable audit trail.
