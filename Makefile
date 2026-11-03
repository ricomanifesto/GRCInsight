.PHONY: test-go test-agent lint-agent format-agent type-agent check-agent check-go-format check-site static-artifact test-static-artifact check e2e fmt-go

GOCACHE_DIR ?= $(CURDIR)/.cache/go-build
GOMODCACHE_DIR ?= $(CURDIR)/.cache/go-mod
UV_CACHE_DIR ?= $(CURDIR)/.cache/uv
PYTHON ?= python3
PYTEST_DISABLE_PLUGIN_AUTOLOAD ?= 1

test-go:
	GO111MODULE=on GOCACHE=$(GOCACHE_DIR) GOMODCACHE=$(GOMODCACHE_DIR) go test ./...

test-agent:
	cd agent && UV_CACHE_DIR=$(UV_CACHE_DIR) PYTEST_DISABLE_PLUGIN_AUTOLOAD=$(PYTEST_DISABLE_PLUGIN_AUTOLOAD) uv run pytest -q

lint-agent:
	cd agent && UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ruff check .

format-agent:
	cd agent && UV_CACHE_DIR=$(UV_CACHE_DIR) uv run black --check .

type-agent:
	cd agent && UV_CACHE_DIR=$(UV_CACHE_DIR) uv run ty check .

check-agent: test-agent lint-agent format-agent type-agent

check-go-format:
	@unformatted="$$(gofmt -l $$(git ls-files '*.go'))"; \
	if [ -n "$$unformatted" ]; then \
		echo "Go files need formatting:"; \
		echo "$$unformatted"; \
		exit 1; \
	fi

check-site:
	$(PYTHON) scripts/build_site.py --check
	$(PYTHON) scripts/check_site_report.py
	$(PYTHON) scripts/check_site_renderer.py

static-artifact:
	@test -n "$(REVISION)" && test -n "$(ARTIFACT_STORE)" && test -n "$(ARTIFACT_RECEIPTS)" || \
		{ echo "Set REVISION, ARTIFACT_STORE and ARTIFACT_RECEIPTS"; exit 2; }
	$(PYTHON) scripts/build_static_artifact.py --revision "$(REVISION)" \
		--output "$(ARTIFACT_STORE)" --receipts "$(ARTIFACT_RECEIPTS)"

test-static-artifact:
	$(PYTHON) -m pytest scripts/tests -q -p no:cacheprovider

check: check-go-format test-go check-agent check-site

e2e:
	@bash scripts/integration/run_e2e.sh

fmt-go:
	go fmt ./...
