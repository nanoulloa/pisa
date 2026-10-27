# Pisa developer commands. Run `make` to list them.
.DEFAULT_GOAL := help

SCHEMA := packages/contracts/schema/pisa.schema.json
PY_MODELS := packages/contracts/python/src/pisa_contracts/models.py
PY_SCHEMA := packages/contracts/python/src/pisa_contracts/schema.py

.PHONY: help setup gen gen-check lint typecheck test e2e check dev-engine dev-web deploy-engine sync-secrets \
	eval-synthetic eval

help: ## List commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install Node and Python dependencies and the test browser
	npm install
	uv sync --all-packages --all-groups
	npx --workspace @pisa/web playwright install chromium

gen: ## Regenerate contract types, brand tokens CSS and logo SVGs
	npm run gen --workspace @pisa/contracts
	uv run datamodel-codegen \
		--input $(SCHEMA) --input-file-type jsonschema --output $(PY_MODELS) \
		--output-model-type pydantic_v2.BaseModel --target-python-version 3.12 \
		--enum-field-as-literal all --use-union-operator --use-standard-collections \
		--use-annotated --use-type-alias --field-constraints --use-field-description --use-schema-description \
		--extra-fields forbid --disable-timestamp --formatters ruff-format \
		--custom-file-header '# Generated from $(SCHEMA) by `make gen`. Do not edit by hand.'
	uv run python packages/contracts/python/embed_schema.py $(SCHEMA) $(PY_SCHEMA)
	uv run python scripts/embed_messages.py apps/web/messages services/engine/src/pisa_engine/whatsapp/messages.py
	uv run python brand/build_tokens.py
	uv run python brand/logo/generate.py

gen-check: gen ## Fail if generated types are out of date
	git diff --exit-code -- packages/contracts brand apps/web/src/app/icon.svg apps/web/public/brand \
		services/engine/src/pisa_engine/whatsapp/messages.py

lint: ## Lint and check formatting
	uv run ruff check .
	uv run ruff format --check .
	npm run lint --workspaces --if-present

typecheck: ## Strict type checks (mypy, tsc)
	uv run mypy services/engine scripts brand packages/contracts/python
	npm run typecheck --workspaces --if-present

test: ## Unit tests (never call paid APIs)
	uv run pytest
	npm run test --workspaces --if-present

e2e: ## Build the web app and run the browser tests against a local engine
	NEXT_PUBLIC_ENGINE_URL=http://localhost:8100 npm run build --workspace @pisa/web
	npm run e2e --workspace @pisa/web

check: gen-check lint typecheck test ## Everything CI runs, except the browser smoke test

dev-engine: ## Run the engine API on :8000
	uv run uvicorn pisa_engine.api:app --reload --port 8000

dev-web: ## Run the web app on :3000
	npm run dev --workspace @pisa/web

deploy-engine: ## Deploy the engine API to Modal (needs `uvx modal setup` and the "pisa-engine" secret)
	uv export --package pisa-engine --no-dev --no-hashes --no-emit-workspace --frozen \
		--output-file services/engine/requirements.modal.txt
	uv run modal deploy services/engine/modal_app.py

sync-secrets: ## Copy the engine's secrets from .env to Modal (prints key names, never values)
	uv run python scripts/sync_modal_secret.py

EVAL := uv run python -m pisa_engine.evaluation
SYNTHETIC := eval/raw/synthetic/manifest.json

eval-synthetic: ## Free eval on rendered clips with known physics; writes eval/reports/synthetic.md
	$(EVAL) synth
	PISA_SEGMENTER=fake PISA_PLANNER=fake $(EVAL) run --manifest $(SYNTHETIC) --name synthetic --force
	$(EVAL) score --manifest $(SYNTHETIC) --name synthetic

eval: ## Eval a labeled set: make eval MANIFEST=eval/raw/phone-v1/manifest.json NAME=phone-v1
	$(EVAL) run --manifest $(MANIFEST) --name $(NAME)
	$(EVAL) score --manifest $(MANIFEST) --name $(NAME)
	$(EVAL) calibrate --manifest $(MANIFEST) --name $(NAME)
