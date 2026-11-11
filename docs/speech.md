# Gnani speech integration

## Contract verified in documentation

Official reference inspected 2026-11-11: https://docs.gnani.ai/api/STT/speech-to-text

The adapter uses only documented REST: POST https://api.vachana.ai/stt/v3, multipart `audio_file`, `model=prisma-v3.0`, `language_code`, `format=verbatim`, and the `X-API-Key-ID` header. The response must contain `success: true` and a string `transcript`. Provider confidence is not documented and is never invented. The returned request ID is preserved when present. Language hints include Kannada, Hindi, English, Kannada-English and Hindi-English. Hints do not guarantee recognition quality or language detection accuracy.

BOLBUS uses bounded recorded clips rather than a live WebSocket stream. Browser AudioWorklet captures Float32 mono samples, encodes actual PCM16 WAV at the AudioContext sample rate, and sends raw `audio/wav` to its own backend. The backend validates channels, bit depth, sample count, duration and size before constructing Gnani's multipart upload. It never relabels WebM as WAV. Recording stops at 29 seconds, below the documented 30-second limit, or when the conductor stops/cancels/leaves. Permission is requested only after Record is pressed. HTTPS or localhost is required for browser microphone access. AudioWorklet support is required; text fallback works without it.

## Configuration

In `backend/.env`, or server environment variables:

```dotenv
SPEECH_MODE=gnani
GNANI_API_KEY=your_private_key
```

Restart the backend. Do not place this key in frontend files or VITE variables, and do not commit .env. A configured key is not proof of valid permissions or credits. The first actual recording verifies account access. This implementation does not send synthetic test audio to a paid account automatically.

Default `SPEECH_MODE=disabled` keeps text extraction usable with recording unavailable. Explicit `SPEECH_MODE=fixture` exposes labeled sample transcript buttons; recording remains unavailable and the sample endpoint never calls Gnani. The samples include real Bengaluru place names, which will correctly require clarification on the fictional Central–Lake route. Configure real matching stops/aliases to resolve them; the parser never silently inserts those destinations into a route.

## API and workflow

- GET `/api/speech/status`: mode, availability, development fixture names and clip duration limit. No key is returned.
- POST `/api/speech/transcribe?route_id=1&language=kn-IN,en-IN`: raw PCM16 mono WAV, Content-Type audio/wav. Returns original transcript, source/provider, fixture flag, provider request ID when available, route ID and extracted items.
- POST `/api/speech/parse`: `{ "route_id": 1, "text": "One to BTM, two to Majestic" }`. Returns the same extraction schema, labeled manual text. Maximum 2,000 characters.
- POST `/api/speech/fixture/kn-mixed?route_id=1`: only enabled in explicit fixture mode. Always labeled development-fixture and `is_fixture=true`.

The deterministic parser supports common English/Hindi/Kannada quantity words and native decimal digits, common ticket/filler words, destination suffixes and multiple clauses separated by commas/and/mattu/ಮತ್ತು/और. It resolves each destination through the existing exact route name/alias resolver. Unknown, ambiguous, missing quantity and category fields are surfaced for review. Unsupported wording may require full manual correction; there is no claim of general language comprehension. Negation/corrections require re-entry rather than silently using the positive phrase. No LLM performs extraction.

Categories are proposed only for explicit supported keywords such as standard or Shakti. Unspecified categories remain blank until chosen. Mentioning Shakti never checks eligibility or documents. The review lets the conductor edit all stops, counts and categories, choose boarding/service and save one draft per clause. Creation UUIDs survive uncertain saves and navigation. Saved items reopen their existing record. Transcription/review are retained in session storage on this browser tab (not durable server audit); audio is not persisted. Clear tab storage on shared devices as appropriate.

Saving remains a draft; the existing route order, deterministic fare, payment, eligibility/document and explicit approval endpoints remain mandatory. Speech never issues or approves a ticket. Multi-item saves are individual operations, not an atomic bulk issue.

## Errors and privacy

Invalid format/duration or no recognized speech returns 422; oversize returns 413; account permissions/credits/key problems return 503; upstream rate limits return 429; timeout returns 504; malformed/truncated provider responses and upstream network/server failures return 502. Errors use local safe messages and do not relay provider bodies or keys. There are no automatic retries or silent fallback transcripts. The UI offers another recording and editable manual text after failures. Browser requests time out after 60 seconds; backend connect/read timeouts are 10/45 seconds.

This is a local simulator with no authenticated public API. Before deployment, add authenticated access, quotas, a controlled audio retention/privacy policy, cancellation propagation and operational monitoring. Gnani processes transmitted audio according to the account's provider terms. BOLBUS does not store audio on disk or in SQLite.

## Validation report

Mock/fixture coverage: documented multipart field/header serialization and success response; invalid/empty/truncated provider responses; 400/401/402/403/429/500/504; network/timeouts; malformed/truncated/oversize WAV; multilingual transcripts and code mixing; multiple destinations; unknown/ambiguous aliases; absent/conflicting quantities; explicit categories; no implicit request creation; fixture labeling/disabled live mode. Frontend coverage includes text fallback, category confirmation, correction re-extraction, microphone cleanup/permission denial (mocked capture), and exact WAV encoding. Existing manual-flow tests still run.

Real Gnani service: NOT TESTED. No Gnani credentials were available in the task environment. Browser physical microphone-to-Gnani transcription, account/model access, latency and noisy-bus/Kannada-English recognition accuracy remain unverified. Mocked HTTP success does not establish real recognition quality. After setting a valid key, use a real short recording on /voice and verify original transcription, edits, draft creation and the existing conductor approval flow. Do not treat mocked samples as a live E2E test.

Persisted batch review now extends this workflow: use **Save entire batch to pending queue**, then resume individual item checks from the pending queue. The original transcript is server-persisted for those batches. See [batch-ticketing.md](batch-ticketing.md) for retry keys, interruption recovery and partial failure behavior.
