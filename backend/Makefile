.PHONY: run migrate downgrade reset-db

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	alembic upgrade head

downgrade:
	alembic downgrade -1

reset-db:
	@if [ "$(CONFIRM)" != "reset" ]; then \
		echo "Uso: make reset-db CONFIRM=reset"; \
		exit 1; \
	fi
	docker compose -f ../docker-compose.yml down -v
	docker compose -f ../docker-compose.yml up --build -d db
	docker compose -f ../docker-compose.yml run --rm backend alembic upgrade head
