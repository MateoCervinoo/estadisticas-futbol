from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

if not (BACKEND_ROOT / "app").exists():
    # In Docker the backend is mounted directly at /app, so /app/app exists.
    BACKEND_ROOT = Path("/app")
    PROJECT_ROOT = BACKEND_ROOT
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import init_db
from app.data_manager import ingest_historical_to_db, seed_equipos_if_empty
from app.sync import sync_fixtures_and_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_tasks")


def migrate_db() -> None:
    init_db()
    logger.info("DB migrada a head")


def seed_db() -> None:
    init_db()
    seed_equipos_if_empty()
    logger.info("Seed básico completado")


def load_results(since_year: int) -> None:
    init_db()
    ingest_historical_to_db(since_year=since_year)
    logger.info("Carga histórica completada desde results.csv")


def sync_data() -> None:
    init_db()
    summary = sync_fixtures_and_metrics()
    compact_summary = {}
    for key, value in summary.items():
        if isinstance(value, list):
            compact_summary[f"{key}_count"] = len(value)
            compact_summary[f"{key}_sample"] = value[:10]
        else:
            compact_summary[key] = value
    print(json.dumps(compact_summary, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description="Tareas operativas de DB y datos")
    parser.add_argument(
        "task",
        choices=("migrate_db", "seed_db", "load_results", "sync_data"),
        help="Tarea a ejecutar",
    )
    parser.add_argument("--since-year", type=int, default=2018, help="Año inicial para load_results")
    args = parser.parse_args()

    if args.task == "migrate_db":
        migrate_db()
    elif args.task == "seed_db":
        seed_db()
    elif args.task == "load_results":
        load_results(args.since_year)
    elif args.task == "sync_data":
        sync_data()


if __name__ == "__main__":
    main()
