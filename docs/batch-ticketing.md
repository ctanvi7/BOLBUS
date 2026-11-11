# Interruption-aware batch ticketing

## Workflow

From Voice entry, record using the existing Gnani adapter or enter text. `Two Silk Board, one Jayanagar, three Majestic.` produces three independent clauses. Stops must exist on the configured route; the synthetic default route does not silently acquire Bengaluru destinations. Quantity words in English, Kannada, Hindi and code-mixed requests use the existing deterministic parser. Categories not explicitly stated still need a conductor choice.

Select **Save entire batch to pending queue**. The server preserves the original transcription, route and source label in `ticket_batches` and each independent draft in `batch_items`. Source is client-supplied provenance, not authenticated proof of a provider call. You can save unresolved items without guessing destinations, quantities or categories. A newly extracted utterance gets a fresh batch creation intent, so a second passenger saying the same sentence can be a different batch; retries of one intent reuse its key.

Open **Pending requests → Saved batches → Resume** after navigation or refresh. Review boarding, destination, quantity, category and service separately for each item. Possible destinations are at most three route-specific suggestions, clearly separate from exact resolution; no fuzzy suggestion is automatically selected. Select explicitly, then save the reviewed details.

**Prepare this item** and **Prepare saved items** create/link individual ticket requests and run the existing deterministic fare validator. They never verify eligibility/payment or approve tickets. Each linked ticket displays its own state, issues and quote. Resume its individual verification/approval screen, then use **Resume batch** to return. Cancellation before preparation marks just that item cancelled; after preparation use the linked ticket's cancellation action. Terminal ticket states remain immutable.

## Recovery and correctness

- SQLite is authoritative for saved batch drafts, original transcript and linked ticket states. Startup adds new batch tables without deleting old records. Batches reappear after browser or backend restart.
- Unsaved batch edits are written to browser local storage per item with their base server version. Returning or refreshing restores those fields. The UI requires saving or reconciling them before preparation. Unavailable storage is reported; such edits require explicit server saves before leaving.
- Individual ticket review fields, conductor name and unchecked/saved-versus-unsaved payment/document check edits also have local recovery. These are only UI values; server verification still requires its explicit action. **Approval consent is never restored or automatically submitted.**
- A version mismatch blocks applying retained edits. The server's version guard rejects stale writes. The user compares retained detail or reloads/discards it deliberately. No background approval or silent confirmation replay occurs.
- Batch creation UUIDs are unique and compare immutable creation payloads. An uncertain save with changed payload is rejected until the conductor checks the queue or starts a new extraction. Successful speech batches reopen their existing batch ID. Saving individual speech drafts and saving that same extraction as a batch are mutually exclusive in the UI.
- Preparing an item uses a stable deterministic creation UUID and a unique persisted ticket link. Concurrent/repeated prepare calls return the same ticket even after that ticket is edited or approved. Prepared batch draft fields are locked; future changes go through the existing ticket engine and reset fare-relevant confirmations.
- Preparation uses one SQLite write reservation and per-item savepoints. Expected validation failures preserve successful items and store an error on the failed item. The response lists each success/error; the conductor can correct and retry only unfinished items. A catastrophic database/commit failure rolls back the transaction, and stable keys permit safe retry after checking server state.
- The existing serialized/idempotent approval and unique simulated-ticket constraint remain authoritative. Mixed regular/concession batches cannot inherit another item's confirmations.

## APIs

- POST `/api/batches`: `client_batch_id` UUID, route_id, original_transcription, optional source (`manual-text`, `gnani`, `development-fixture`), optional one draft per parsed clause. Repeated identical creation returns the existing batch, even after its items change. Maximum 30 items and 2,000 transcript characters.
- GET `/api/batches`: batches newest first, with current linked ticket states.
- GET `/api/batches/{id}`: original transcription plus independent items, drafts, versions, issues and alternatives.
- PUT `/api/batches/{id}/items/{item_id}`: `{version, draft}`. Draft has nullable boarding/destination IDs, destination_text, nullable quantity/category, service_type and language. Saving increments item version.
- POST `/api/batches/{id}/prepare`: `{ "versions": { "item-id": 2 } }`; only listed items are attempted. Returns per-item results, updated batch and processing_ms. No approval endpoint exists for the entire batch.
- POST `/api/batches/{id}/items/{item_id}/cancel`: `{version}`; only unprepared items. Prepared items use existing ticket cancellation.
- TicketOut additionally includes nullable `batch_id` for navigation.

## Validation and latency

Backend tests cover the requested three-destination example, code mixing, unknown stop suggestions requiring selection, reload/database reopening, stale edits, batch creation retries, cancellation, partial preparation failure, mixed concession/regular processing and concurrent prepare/approve calls without duplicate simulated tickets. Frontend tests remount the app against persisted mock server/local-storage state to simulate refresh and interrupted navigation, verify stale-recovery handling, ensure suggestions are not selected automatically, and ensure restored verification UI never restores approval consent. These do not claim real physical browser refresh or live microphone/Gnani E2E testing.

Run `python scripts/benchmark_batches.py` with backend dependencies installed. A local 20-batch run (three synthetic items each) measured server preparation median **21.69 ms**, maximum **35.84 ms**, and TestClient request roundtrip median **29.53 ms**. These are local synthetic timings, not production guarantees. processing_ms includes item preparation/result construction before transaction commit; it excludes STT, browser rendering, real network latency and commit time. Provider STT latency remains unverified without a live credentialed test.

## Limits

Saved work is server-backed; unsaved recovery is device/browser-local and can be lost if storage is cleared. Existing speech review before queueing is session-local. No speech recognizer detects human interruptions automatically; recovery means navigation/refresh recovery and an explicit pending queue. The parser is a conservative grammar; unusual syntax, corrections or missing clause separators require clarification. No speaker identity, inferred eligibility, biometric capture, official BMTC integration or automatic bulk approval is added. The simulator still requires authentication, controlled retention, pagination/large-history performance work and operational monitoring before public use.
