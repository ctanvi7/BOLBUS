# API contracts

Base `/api`. JSON only. Generated schemas: `/openapi.json`; interactive reference: `/docs`.

| Method | Path | Input | Behavior |
| --- | --- | --- | --- |
| GET | /health | none | Status, demo mode, speech unavailable |
| GET | /routes | none | Demo routes, ordered multilingual stops and fare rules with source disclosures |
| GET | /ticket-requests | optional state, limit=100 (1–200), offset=0 | Newest-first listing |
| GET | /ticket-requests/{id} | none | Request with version and issues |
| POST | /ticket-requests | TicketCreate | Save draft, 201; identical creation retry returns existing record |
| PUT | /ticket-requests/{id} | TicketFields + version | Replace editable fields; reset validation and checks |
| POST | /ticket-requests/{id}/validate | version | Recalculate state and quote |
| POST | /ticket-requests/{id}/verify | version, payment_collected, concession_verified | Save explicit checks after journey validation |
| POST | /ticket-requests/{id}/approve | version, confirmed=true, conductor_name | Explicit demo approval after revalidation |
| POST | /ticket-requests/{id}/cancel | version | Terminal cancellation |

TicketFields example:

```json
{"route_id":1,"origin_stop_id":1,"destination_stop_id":5,"passenger_count":2,"category":"standard","language":"en-IN"}
```

TicketCreate also requires `client_request_id`, a client-generated UUID for one creation intent. Stops may be null or omitted for partial drafts. Categories: `standard`, `demo-concession`. Languages: `en-IN`, `kn-IN`, `hi-IN`. Count defaults to 1, category to standard and language to en-IN. Stops must belong to the route. Unknown fields are rejected. Clients cannot set state, quote or approval through create/edit.

TicketOut includes the editable fields plus `id`, `client_request_id`, `state`, `version`, `total_paise`, `payment_collected`, `concession_verified`, `approved_by`, `approved_at`, `created_at` and `issues`. Quotes are null until validation or after editing; all quoted amounts are invented demo paise. Issues on drafts are suggestions and do not change state. Cancelled records retain the last quote.

Example approval:

```json
{"version":3,"confirmed":true,"conductor_name":"Demo conductor"}
```

Errors use FastAPI's `detail` envelope: 404 missing request; 422 malformed data, unknown route/category or foreign stop; 409 stale version, invalid transition, terminal record or key conflict; 503 database unavailable. Missing/reversed journeys validate successfully into `needs-clarification` with issues.

Creation retries compare the submitted fields with the current saved fields. If edited since creation, the original payload may conflict; read the register and use the saved ID. Approval retries accept only the immediately preceding version and same conductor name. No browser mutation is automatically retried. No authentication is implemented; use locally only.
