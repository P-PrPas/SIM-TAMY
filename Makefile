# SIM-TAMY — PRD appendix B. Needs GNU make + a POSIX shell (Git Bash / WSL on Windows).
# Targets marked "not implemented" fail on purpose until their ticket lands: no fake green.

API := apps/api
WEB := apps/web
VENV := $(API)/.venv
PY := $(VENV)/bin/python
ifeq ($(OS),Windows_NT)
PY := $(VENV)/Scripts/python
endif

.PHONY: help install up down migrate mock-api gen-api lint test test-coverage test-e2e validate-content leakcheck eval bench rescore stats cost-report purge-old demo

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

# Prism serves docs/openapi.yaml on :4010 so the web app can be built before the backend exists.
mock-api:
	npx --yes @stoplight/prism-cli mock -p 4010 -h 127.0.0.1 docs/openapi.yaml

gen-api:
	cd $(WEB) && npm run gen:api

lint:
	cd $(API) && ../../$(PY) -m ruff check . && ../../$(PY) -m ruff format --check . && ../../$(PY) -m mypy app
	cd $(WEB) && npm run lint && npm run typecheck

test:
	cd $(API) && ../../$(PY) -m pytest --cov=app && ../../$(PY) -m coverage report --include='app/engine/*' --fail-under=85
	cd $(WEB) && npm test

test-coverage:
	cd $(WEB) && npm run test:coverage

test-e2e:
	cd $(WEB) && npm run test:e2e

# STRICT=1 will also require `source` on clinical items (T-010).
validate-content:
	cd $(API) && CONTENT_DIR=../../content ../../$(PY) -m app.content.validator_cli $(if $(STRICT),--strict)

# Fails if a play-time schema in docs/openapi.yaml can carry hidden facts, risk state, actions or scores.
leakcheck:
	$(PY) scripts/leakcheck.py

# Plays eval/golden/T*.yaml through the real API on a throwaway Postgres (DATABASE_URL). Mock LLM by default;
# `make eval PROVIDER=env` uses the configured LLM and reports what it measures.
eval:
	cd $(API) && CONTENT_DIR=../../content ../../$(PY) ../../eval/run_eval.py $(if $(PROVIDER),--provider $(PROVIDER))
bench:
	cd $(API) && ../../$(PY) ../../eval/model_bench.py $(BENCH_ARGS)
# Rebuilds the score from the Event Log and diffs it with the stored report (needs DATABASE_URL).
rescore:
	@test -n "$(SESSION)" || { echo "usage: make rescore SESSION=<id>"; exit 2; }
	cd $(API) && CONTENT_DIR=../../content ../../$(PY) -m app.rescore $(SESSION)
# Measured from llm_calls / events (needs DATABASE_URL). Prices are never assumed:
# `make cost-report COST_ARGS='--price openai_like:MODEL=INPUT_USD_PER_M,OUTPUT_USD_PER_M'`.
stats:
	cd $(API) && ../../$(PY) -m app.stats stats
cost-report:
	cd $(API) && ../../$(PY) -m app.stats cost-report $(COST_ARGS)
purge-old:
	@echo "not implemented: retention purge"; exit 1
demo:
	@sh scripts/demo.sh
