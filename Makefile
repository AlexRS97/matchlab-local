.PHONY: setup api web test lint build train

setup:
	python -m pip install -c backend/constraints.txt -e "backend[dev,learning]"
	cd frontend && npm ci

api:
	python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

web:
	cd frontend && npm run dev

test:
	cd backend && python -m pytest

lint:
	python -m ruff check backend/app backend/tests backend/serve.py
	python -m mypy --config-file backend/pyproject.toml backend/app

build:
	cd frontend && npm run build

train:
	python -m app.learning --train
