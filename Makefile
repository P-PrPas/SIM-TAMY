# SIM-TAMY — PRD appendix B. Needs GNU make + a POSIX shell (Git Bash / WSL on Windows).
# Targets marked "not implemented" fail on purpose until their ticket lands: no fake green.

API := apps/api
WEB := apps/web
VENV := $(API)/.venv
PY := $(VENV)/bin/python
ifeq ($(OS),Windows_NT)
PY := $(VENV)/Scripts/python
endif

.PHONY: help install up down migrate lint test validate-content eval bench rescore stats cost-report purge-old demo

help:
	@grep -E '^[a-z-]+:' Makefile | cut -d: -f1 | tr '\n' ' '; echo

install: ## local dev deps (api venv + web node_modules)
	python -m venv $(VENV)
	$(PY) -m pip install -e "$(API)[dev]"
	cd $(WEB) && npm ci

up:
	docker compose up --build -d

down:
	docker compose down

migrate:
	docker compose run --rm api alembic upgrade head

lint:
	cd $(API) && ../../$(PY) -m ruff check . && ../../$(PY) -m ruff format --check . && ../../$(PY) -m mypy app
	cd $(WEB) && npm run lint && npm run typecheck

test:
	cd $(API) && ../../$(PY) -m pytest
	cd $(WEB) && npm test

# STRICT=1 will also require `source` on clinical items (T-010).
validate-content:
	cd $(API) && CONTENT_DIR=../../content ../../$(PY) -m app.content.validator_cli $(if $(STRICT),--strict)

eval:
	@echo "not implemented: Golden Test Suite (T-070)"; exit 1
bench:
	@echo "not implemented: model bench (T-005)"; exit 1
rescore:
	@echo "not implemented: rescore SESSION=$(SESSION) (T-062)"; exit 1
stats:
	@echo "not implemented: latency stats (T-044)"; exit 1
cost-report:
	@echo "not implemented: LLM cost report (T-044)"; exit 1
purge-old:
	@echo "not implemented: retention purge"; exit 1
demo:
	@echo "not implemented: demo mode (T-073)"; exit 1
