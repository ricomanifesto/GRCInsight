.PHONY: test-go test-agent e2e fmt-go

test-go:
	GO111MODULE=on go test ./...

test-agent:
	PYTHONPATH=agent pytest -q agent/tests

e2e:
	@bash scripts/integration/run_e2e.sh

fmt-go:
	go fmt ./...

