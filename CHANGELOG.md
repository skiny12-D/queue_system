# Changelog

## [Unreleased]

- Migrated FastAPI startup handling from `@app.on_event("startup")` to the recommended `lifespan` handler.
- Started the queue proximity watcher within the FastAPI lifespan lifecycle.
- Added `# comnetraio` marker comments across key files for easier navigation.
- Added `.env.example`, `.gitignore`, and README instructions for environment configuration and local execution.
- Implemented QR code generation, digital alerts, SMTP/Twilio notification support, and proximity alert logic.
