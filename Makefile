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
.PHONY: help build run inspector test lint format sync clean

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

_check-creds:
	@if [ -z "$$SALDEO_USERNAME" ] || [ -z "$$SALDEO_API_TOKEN" ]; then \
	    echo "ERROR: export SALDEO_USERNAME and SALDEO_API_TOKEN first." >&2; \
	    exit 1; \
	fi
