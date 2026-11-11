# Validation record

Foundation checked on Python 3.12 and Node 24:

- Pytest: 16 passing backend cases (state transitions, explicit approval, concessions, partial/reversed journeys, edit invalidation, stale versions, idempotent creation/approval, terminal immutability, malformed inputs, foreign-route stops, disclosures and missing resources).
- Vitest: 4 passing frontend cases (complete conductor flow, approval confirmation gating, failed-network draft retention, corrupt recovery and API conflict reporting).
- TypeScript and Vite production build: successful, including bundled Inter and Unicode fonts.
- FastAPI bootstrap starts successfully and creates demo schema/catalog.

A real Chromium smoke check was attempted but the execution environment denied the browser's Unix socket creation before it could open the app. Visual desktop/mobile verification and a browser-to-live-API smoke test remain unverified. Frontend flow tests use mocked HTTP responses; backend contract behavior is independently tested against isolated SQLite databases.

Non-blocking third-party warnings: Starlette TestClient's AnyIO alias deprecation and React Router v7 future flags. No runtime AI/speech integration has been tested or claimed.

## Python 3.12 compatibility review

A fresh virtual environment on Python 3.12.14 installed the unchanged six direct dependency pins in backend/requirements.txt successfully, including SQLAlchemy 2.0.36. `pip check` reported no broken requirements; all 16 backend tests passed. SQLAlchemy model import/initialization also passed when run from backend/. This verification ran on Linux; native Windows installation was not executed here.

Python 3.12 is the recommended runtime. Python 3.14.5 with SQLAlchemy 2.0.36 produced the user-reported typing.Union descriptor failure; that combination is not supported for this foundation. No dependency upgrades or business logic changes were needed. Transitive dependencies remain resolver-selected, not fully locked. The existing AnyIO alias deprecation warning is non-blocking.
