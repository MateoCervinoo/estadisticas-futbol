# Backend

FastAPI backend for estadisticas-futbol.

Development:

1. Build the Docker image: `docker compose build backend`
2. Start the backend with compose: `docker compose up backend`

The container uses `wait-for-db.sh` to wait until Postgres is available before starting Uvicorn.
