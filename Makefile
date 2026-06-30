.PHONY: up migrate reset-db seed load-results sync train test-backend build-frontend

up:
	docker compose up --build

migrate:
	docker compose run --rm backend alembic upgrade head

reset-db:
	$(MAKE) -C backend reset-db CONFIRM=reset

seed:
	docker compose run --rm backend python scripts/db_tasks.py seed_db

load-results:
	docker compose run --rm backend python scripts/db_tasks.py load_results

sync:
	docker compose run --rm backend python scripts/db_tasks.py sync_data

train:
	python -m entrenador.05_train_model

test-backend:
	cd backend && python -m pytest

build-frontend:
	cd frontend && npm run build
