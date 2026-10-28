# SIM-TAMY — PRD appendix B. Needs GNU make + a POSIX shell (Git Bash / WSL on Windows).
# Targets marked "not implemented" fail on purpose until their ticket lands: no fake green.

API := apps/api
WEB := apps/web
VENV := $(API)/.venv
PY := $(VENV)/bin/python
ifeq ($(OS),Windows_NT)
PY := $(VENV)/Scripts/python
endif

.PHONY: help install up down migrate mock-api gen-api gen-content-schemas check-content-schemas lint test test-coverage test-e2e test-e2e-live test-e2e-demo validate-content leakcheck eval eval-pp001 eval-parents eval-v2 bench rescore stats cost-report purge-old seed-demo demo-reset prestage loadcheck demo

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

# Pydantic is authoritative; commit these editor schemas and verify drift in CI (T-012).
gen-content-schemas:
	cd $(API) && ../../$(PY) -m app.content.export_schemas

check-content-schemas:
	cd $(API) && ../../$(PY) -m app.content.export_schemas --check

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

test-e2e-live:
	cd $(WEB) && npm run test:e2e:live
# Stage golden path (solo + family co-op on two browser contexts) against a local API + PostgreSQL (DATABASE_URL), mock LLM.
test-e2e-demo:
	cd $(WEB) && npm run test:e2e:demo

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
# The PP-001 (draft) scenario through the same runner: eval/golden/pp001/T*.yaml.
eval-pp001:
	cd $(API) && CONTENT_DIR=../../content ../../$(PY) ../../eval/run_eval.py --golden-dir ../../eval/golden/pp001
# The courses for new dads and moms (eval/golden/parents/T*.yaml, one case per file).
eval-parents:
	cd $(API) && CONTENT_DIR=../../content ../../$(PY) ../../eval/run_eval.py --golden-dir ../../eval/golden/parents
# AI-01 labeled Thai sets (eval/v2/dev.yaml + heldout.yaml); mock by default, `make eval-v2 PROVIDER=env` for the configured LLM.
eval-v2:
	cd $(API) && PYTHONPATH=. CONTENT_DIR=../../content ../../$(PY) ../../eval/v2/run_eval_v2.py $(if $(PROVIDER),--provider $(PROVIDER))
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
	cd $(API) && ../../$(PY) -m app.purge_old
# 20 learners at once against a running API; add LOAD_ARGS='--output docs/results/<name>.md' to save the report.
loadcheck:
	@test -n "$(URL)" || { echo "usage: make loadcheck URL=http://localhost:8000 [LOAD_ARGS='--sessions 20']"; exit 2; }
	$(PY) scripts/loadcheck.py $(URL) $(LOAD_ARGS)
# A demo class (DEMO01) with five completed, synthetic sessions, played through the real API (needs DATABASE_URL).
seed-demo:
	cd $(API) && CONTENT_DIR=../../content ../../$(PY) -m app.seed_demo
# Wipes and re-seeds ONLY the DEMO01 class. Refuses unless you state DATABASE_URL is a demo database: make demo-reset DEMO_DB=1
demo-reset:
	@test "$(DEMO_DB)" = 1 || { echo "refusing: this deletes the DEMO01 class; confirm the database is a demo one with DEMO_DB=1"; exit 2; }
	cd $(API) && SIMTAMY_DEMO_DB=1 CONTENT_DIR=../../content ../../$(PY) -m app.seed_demo --reset
# Read-only pre-stage check (health, web, cases, family stories, replay, CORS): make prestage URL=<api> WEB=<web> [WAIT=120]
prestage:
	@test -n "$(URL)" -a -n "$(WEB_URL)" || { echo "usage: make prestage URL=<api-url> WEB_URL=<web-url> [WAIT=120]"; exit 2; }
	$(PY) scripts/prestage.py $(URL) $(WEB_URL) $(if $(WAIT),--wait $(WAIT))
demo:
	@sh scripts/demo.sh

.PHONY: build-course-replays
build-course-replays:
	cd $(API) && ../../$(PY) -m scripts.build_course_replays

.PHONY: build-validation-report
build-validation-report:
	cd $(API) && ../../$(PY) -m scripts.build_validation_report
