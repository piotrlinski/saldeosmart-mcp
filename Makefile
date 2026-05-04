# SaldeoSMART MCP — common tasks.
#
#   make help        # list every target
#   make build       # build the Docker image
#   make run         # run the server in Docker (stdio)
#   make test        # run pytest locally (needs uv)
#   make lint        # ruff (check + format --check) + mypy locally (needs uv)
#   make format      # apply ruff format + ruff --fix locally (needs uv)
#   make inspector   # MCP Inspector against the Docker image
#   make clean       # remove the image
#
# Override the image tag or Dockerfile location via env vars:
#   IMAGE=saldeosmart-mcp:dev DOCKERFILE=docker/Dockerfile.dev make build

IMAGE       ?= saldeosmart-mcp:latest
DOCKERFILE  ?= docker/Dockerfile

# Tools
DOCKER ?= docker
UV     ?= uv

# Credentials passthrough for `make run` / `make inspector`. Export these in
# your shell first; the recipes refuse to run if they're missing.
ENV_FLAGS = -e SALDEO_USERNAME -e SALDEO_API_TOKEN -e SALDEO_BASE_URL

.DEFAULT_GOAL := help
.PHONY: help build run inspector test lint format sync clean \
        docs-sync docs-serve docs-build docs-lint docs-link-check \
        docs-coverage docs-all docs-clean

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} \
	      /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2 }' \
	      $(MAKEFILE_LIST)

build: ## Build the Docker image
	$(DOCKER) build -f $(DOCKERFILE) -t $(IMAGE) .

run: _check-creds ## Run the MCP server in Docker (stdio)
	$(DOCKER) run --rm -i $(ENV_FLAGS) $(IMAGE)

inspector: _check-creds ## Open MCP Inspector against the Docker image
	npx @modelcontextprotocol/inspector \
	    $(DOCKER) run --rm -i $(ENV_FLAGS) $(IMAGE)

sync: ## Install dev dependencies locally with uv
	$(UV) sync --extra dev

test: ## Run pytest locally (uv-managed venv)
	$(UV) run pytest tests/

lint: ## Run ruff (check + format --check) + mypy locally
	$(UV) run ruff check src tests
	$(UV) run ruff format --check src tests
	$(UV) run mypy src

format: ## Apply ruff format + ruff --fix locally
	$(UV) run ruff format src tests
	$(UV) run ruff check --fix src tests

clean: ## Remove the Docker image
	-$(DOCKER) image rm $(IMAGE)

# ---- Documentation ----------------------------------------------------------
# The docs site is MkDocs Material + mkdocstrings + mike for versioning.
# `make docs-sync` once, then iterate with `make docs-serve`.
# CI runs `docs-build` (strict), `docs-coverage`, `docs-lint`, `docs-link-check`.

docs-sync: ## Install docs dependencies (uv sync --extra docs)
	$(UV) sync --extra docs

docs-gen: ## Run every generator (tool catalog, error codes, API versions, config)
	$(UV) run python scripts/gen_tool_catalog.py
	$(UV) run python scripts/gen_error_codes.py
	$(UV) run python scripts/gen_api_versions.py
	$(UV) run python scripts/gen_configuration.py

docs-serve: docs-gen ## Live-reload docs locally at http://127.0.0.1:8000
	DISABLE_MKDOCS_2_WARNING=true $(UV) run mkdocs serve -a 127.0.0.1:8000

docs-build: docs-gen ## Build the static site (strict: fails on warnings)
	DISABLE_MKDOCS_2_WARNING=true $(UV) run mkdocs build --strict

docs-clean: ## Remove the built site
	rm -rf site

docs-coverage: docs-build ## Verify every @mcp.tool has a rendered page
	$(UV) run python scripts/check_tool_coverage.py site

docs-lint: ## markdownlint + codespell on docs and source prose
	$(UV) run markdownlint-cli2 'docs/**/*.md' '*.md' || true
	$(UV) run codespell --config .codespellrc docs/ src/ scripts/

docs-link-check: docs-build ## lychee link-check the built site
	lychee --config lychee.toml site/ || true

docs-all: docs-build docs-coverage docs-lint docs-link-check ## All docs gates

_check-creds:
	@if [ -z "$$SALDEO_USERNAME" ] || [ -z "$$SALDEO_API_TOKEN" ]; then \
	    echo "ERROR: export SALDEO_USERNAME and SALDEO_API_TOKEN first." >&2; \
	    exit 1; \
	fi
