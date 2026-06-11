# Changelog

## [Unreleased]

- Migrated FastAPI startup handling from `@app.on_event("startup")` to the recommended `lifespan` handler.
- Started the queue proximity watcher within the FastAPI lifespan lifecycle.
- Added `# comnetraio` marker comments across key files for easier navigation.
- Added `.env.example`, `.gitignore`, and README instructions for environment configuration and local execution.
- Implemented QR code generation, digital alerts, SMTP/Twilio notification support, and proximity alert logic.
 - Fixed frontend/backend integration: dynamic API/WS host, WS message payload handling, and search fixes.
 - Added `httpx` to dependencies to support FastAPI `TestClient`.
 - Relaxed `SenhaOutput.pessoa` typing to avoid response validation errors.
 - Added persistence test `tests/test_persistence.py` and multiple API tests.
 - Ensured atomic writes for `GestorFila` state persistence and improved error handling.
