.PHONY: setup backend frontend test build
setup:
	python -m venv .venv
	.venv/bin/pip install -r backend/requirements.txt
	npm ci --prefix frontend
backend:
	cd backend && ../.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1
frontend:
	npm run dev --prefix frontend
test:
	.venv/bin/python -m pytest
	npm test --prefix frontend
build:
	npm run build --prefix frontend
