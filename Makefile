.PHONY: setup up down logs test lint migrate ingest demo dbt

setup:
	@test -f .env || cp .env.example .env
	docker compose build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker web

test:
	docker compose run --rm api pytest

lint:
	docker compose run --rm api ruff check .

migrate:
	docker compose run --rm migrate

ingest:
	docker compose exec api python -m football_api.cli ingest

demo:
	docker compose exec api python -m football_api.cli seed-demo

dbt:
	docker compose --profile analytics run --rm dbt build

