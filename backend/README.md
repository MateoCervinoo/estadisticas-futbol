# Backend

FastAPI backend for estadisticas-futbol.

Development:

1. Build the Docker image: `docker compose build backend`
2. Start the backend with compose: `docker compose up backend`

Docker Compose runs Uvicorn with `--reload` for local development. The image default command is production-oriented and runs without reload. The API applies Alembic migrations during its FastAPI lifespan startup and fails fast if they cannot be applied.

Required/minimum environment variables:

- `DATABASE_URL`: SQLAlchemy URL for the application database.
- `PYTHONUNBUFFERED`: recommended as `1` in containers.
- `BACKEND_CORS_ORIGINS`: comma-separated allowed origins. Defaults to `http://localhost:3000`.
- `API_FOOTBALL_KEY`: required only for sync jobs that call the external API.
- `CSV_DATA_PATH`: optional CSV path used by data load/sync jobs.
- `RUN_STARTUP_SYNC`: worker-only escape hatch for startup sync. Keep `false` for the API container.

Health endpoints:

- `/health`: process is responding.
- `/health/db`: database connectivity check.
- `/health/model`: prediction model availability; may return `degraded` when fallback parameters are in use.
