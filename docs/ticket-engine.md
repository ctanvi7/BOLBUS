# Deterministic ticket engine

No model or speech system participates in fares, policy decisions or approval. Configuration resides in SQLite through SQLAlchemy models. No official BMTC infrastructure or data is connected.

## Fare source model

`FareTable` stores a route, unique version, source description, effective date, optional inclusive expiry date, and `is_demo`. Dates use ISO YYYY-MM-DD in Asia/Kolkata. `FareEntry` supplies an exact integer-paise unit fare for one boarding stage, destination stage, service type and category. The total is that unit fare times quantity. The engine does not extrapolate from other stages or substitute services/categories.

The latest effective, unexpired table is authoritative for that request. Two active tables starting on the same day are ambiguous and block pricing. An absent exact entry, negative amount, missing table, required-but-missing concession policy, or zero price without a concession policy returns `Fare unavailable`. There is no fallback to an older table with a matching entry. Expired rules cannot approve a saved quote.

`synthetic-1` is explicitly synthetic BOLBUS training data, effective 2026-01-01. Its ordinary standard examples use ₹5/stage, reduced demo examples ₹2.50/stage; express examples are twice those amounts. These rates are expanded into exact journey entries during seeding. They are neither BMTC fares nor official concession policies. The legacy `fare_rules` table is retained as a category/display catalog for backward compatibility, and is never used to authorize a fare.

`ConcessionRule` is scoped to a fare table, service and category. It stores the conductor's required applicability/eligibility and document-check instructions and its demo status. A `shakti-demo` zero-price workflow requires both explicit checks. It does not claim to encode the actual Shakti eligibility rules. Reduced concessions require both checks plus payment when the amount is positive. Only boolean check results are retained; no Aadhaar numbers, ID photos, passenger names or inferred eligibility are accepted by these contracts.

## Configuration

Trusted development tooling can create `Route`, ordered `Stop`, `StopAlias`, `FareTable`, `FareEntry` and `ConcessionRule` records through SQLAlchemy. This foundation does not expose public configuration write endpoints. Create new versioned tables rather than editing deployed fare/policy records. Retire old tables with expiry dates. Keep provenance and verified operator approval for any future authoritative dataset. Route/service/category combinations need explicit entries; custom routes receive no synthetic prices automatically.

Stop resolution performs Unicode normalization, case folding and whitespace normalization. It matches exact multilingual names or configured aliases on the selected route. Multiple matching IDs cause clarification even if one is an exact name. No fuzzy guess is selected. Requests may use stop IDs or `origin_text`/`destination_text`, never both for the same field. Unknown/ambiguous text is retained as an unfinished request with `needs-clarification`; the conductor supplies a specific stop ID using edit. Foreign-route IDs are rejected. Stage order must strictly increase.

## State and evidence

Create saves `draft`. Validate resolves the journey and price, producing `needs-clarification` or `pending-verification`. Verify saves explicit checks and enables `ready-for-approval` only when complete. Approve requires `confirmed: true`, a conductor name, the current request version, ready state and an unchanged current quote. Fare changes block approval until validate and verify run again. Every edit resets quote and checks, including quantity changes after payment.

The canonical quote snapshot contains fare table/source/version/dates/demo status, exact entry, route/service/stages/category/quantity, unit/total paise, and concession instructions. A changed snapshot invalidates confirmations even if the monetary total did not change.

Every successful mutation records an `AuditEvent` with action, before/after state, request version, timestamp, actor when supplied and request snapshot. Approval atomically creates a unique `SimulatedTicket` with frozen quote and total. Approved/cancelled requests are immutable. Approval retries from the same conductor with the approval's preceding/current version return the same request without another audit event or ticket. Other stale calls return 409.

SQLite mutations acquire `BEGIN IMMEDIATE` before reading. The unique request-to-ticket constraint and request versions provide additional guards. The ticket, transition and audit evidence commit together. Audit events have no edit/delete API; this is application-level history, not a cryptographically tamper-proof log against a database administrator. Conductor names remain self-declared until authentication is integrated.

## Migration and API additions

Startup runs an idempotent additive migration. It preserves previous rows and adds service type, optional stop text, document confirmation and quote snapshot columns plus the new tables. Historical approved requests are retained without fabricating past tickets or audit events. Previous nonterminal requests need validation and verification against the new table. Back up valuable SQLite files before startup migrations.

Existing request endpoints remain. Create/edit accept optional `service_type` (default ordinary), stop text and configured category. Verify additionally accepts `documents_verified` (default false); verification booleans are strict. Ticket responses expose these fields and `quote_snapshot` (canonical JSON string).

- GET `/api/routes/{id}/resolve-stop?query=...`: resolved/ambiguous/unknown plus candidates.
- GET `/api/routes/{id}/fare-tables`: sources, versions, dates, explicit entries and concession instructions.
- GET `/api/ticket-requests/{id}/audit`: ordered mutation and transition history.
- GET `/api/ticket-requests/{id}/simulated-ticket`: frozen approved demo record; `valid_for_travel=false`.
- Route responses additionally list configured `service_types`.

## Integration requirements

Operational use needs verified operator-supplied fare and concession datasets, authenticated conductor identities, controlled/versioned configuration publishing, full migration management, retention/access controls for audit history, and authorized ETM/payment/printer adapters. This task implements none of those external connections. No automatic real ticket issuance occurs.
