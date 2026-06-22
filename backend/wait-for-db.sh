#!/usr/bin/env bash
set -euo pipefail

host="${POSTGRES_HOST:-db}"
user="${POSTGRES_USER:-postgres}"
max_attempts=30
attempt=0

echo "Waiting for postgres at ${host}..."
until PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" psql -h "$host" -U "$user" -d "${POSTGRES_DB:-estadisticas}" -c '\q' >/dev/null 2>&1; do
  attempt=$((attempt+1))
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Timed out waiting for Postgres"
    exit 1
  fi
  echo "Postgres is unavailable - sleeping"
  sleep 2
done

echo "Postgres is up - executing command"
exec "$@"
