.PHONY: test-go test-agent lint-agent format-agent type-agent check-agent check-site check e2e fmt-go

GOCACHE_DIR ?= $(CURDIR)/.cache/go-build
GOMODCACHE_DIR ?= $(CURDIR)/.cache/go-mod
UV_CACHE_DIR ?= $(CURDIR)/.cache/uv
PYTHON ?= python3

test-go:
	GO111MODULE=on GOCACHE=$(GOCACHE_DIR) GOMODCACHE=$(GOMODCACHE_DIR) go test ./...

test-agent:
	cd agent && UV_CACHE_DIR=$(UV_CACHE_DIR) uv run pytest -q

lint-agent:
	cd agent && UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff check .

format-agent:
	cd agent && UV_CACHE_DIR=$(UV_CACHE_DIR) uv run black --check .

type-agent:
	cd agent && UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ty check .

check-agent: test-agent lint-agent format-agent type-agent

check-site:
	$(PYTHON) scripts/check_site_report.py
	$(PYTHON) scripts/check_site_renderer.py

check: test-go check-agent check-site

e2e:
	@bash scripts/integration/run_e2e.sh

fmt-go:
	go fmt ./...
