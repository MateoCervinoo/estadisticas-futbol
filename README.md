# estadisticas-futbol (monorepo)

Overview

This repository is a monorepo for a World Cup 2026 statistics project. It contains:

- backend: FastAPI + SQLModel (Python)
- frontend: Next.js (App Router) + Tailwind CSS
- db: PostgreSQL (persistent volume)

Requirements

- Docker and Docker Compose installed on Linux (CachyOS)

Quick start

1. Build and start all services in detached mode:

   docker compose up --build -d

2. Check containers status:

   docker compose ps

3. Backend health check (should return {"status":"ok"}):

   curl http://localhost:8000/health

4. Open frontend at http://localhost:3000

Notes

- Database data is stored in a named Docker volume `estadisticas_postgres_data` so it persists between restarts.
- The backend includes a `wait-for-db.sh` script used by the Dockerfile to wait until Postgres accepts connections before launching Uvicorn.
