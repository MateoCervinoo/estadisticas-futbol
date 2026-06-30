.PHONY: run migrate downgrade reset-db migrate_db seed_db load_results sync_data reset_db

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

migrate_db:
	python scripts/db_tasks.py migrate_db

downgrade:
	alembic downgrade -1

seed_db:
	python scripts/db_tasks.py seed_db

load_results:
	python scripts/db_tasks.py load_results

sync_data:
	python scripts/db_tasks.py sync_data

reset-db:
	@if [ "$(CONFIRM)" != "reset" ]; then \
		echo "Uso: make reset-db CONFIRM=reset"; \
		exit 1; \
	fi
	docker compose -f ../docker-compose.yml down -v
	docker compose -f ../docker-compose.yml up --build -d db
	docker compose -f ../docker-compose.yml run --rm backend python scripts/db_tasks.py migrate_db

reset_db: reset-db
