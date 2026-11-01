import json

import httpx
import pytest

from runtime_adapter import client as client_mod
from runtime_adapter.client import (
    IdempotencyConflict,
    InvalidRuntimeRequest,
    LeaseFenced,
    RunNotFound,
    RuntimeClient,
    RuntimeDraining,
    RuntimeUnavailable,
)

RUN_ID = "0b6f4b0e-6f0e-4b8a-9a43-0c2a1f5d7e11"


def runtime_with(handler):
    requests = []

    def record(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return handler(request)

    return RuntimeClient("http://127.0.0.1:18080", transport=httpx.MockTransport(record)), requests


def error(status, code, **extra):
    return httpx.Response(status, json={"code": code, "message": "x", **extra})


def test_client_requires_a_numeric_loopback_runtime_url():
    for url in (
        "http://localhost:8080",
        "https://runtime.example.com",
        "http://10.0.0.5:8080",
        "http://127.0.0.1",
        "http://127.0.0.1:8080/prefix",
    ):
        with pytest.raises(ValueError):
            RuntimeClient(url)
    RuntimeClient("http://[::1]:8080").close()


def test_submit_sends_exact_contract_fields_and_reports_creation():
    responses = iter(
        (httpx.Response(201, json={"run_id": RUN_ID}), httpx.Response(200, json={"run_id": RUN_ID}))
    )
    runtime, requests = runtime_with(lambda request: next(responses))
    kwargs = dict(
        product="grcinsight",
        workflow_name="generate_report",
        workflow_version="grc-report-runtime-v1",
        idempotency_key="weekly-2026-11-01",
        input_ref={"schema": "s", "report_id": "r", "input_digest": "d"},
        max_attempts=3,
    )
    first = runtime.submit(**kwargs)
    second = runtime.submit(**kwargs)
    assert (first.created, second.created) == (True, False)
    assert requests[0].method == "POST" and requests[0].url.path == "/v1/runs"
    assert json.loads(requests[0].content) == kwargs
    runtime.close()


def test_status_codes_map_to_distinct_adapter_errors():
    cases = [
        (error(409, "idempotency_conflict", existing_run_id=RUN_ID), IdempotencyConflict),
        (error(409, "lease_fenced"), LeaseFenced),
        (error(404, "run_not_found"), RunNotFound),
        (error(400, "invalid_request"), InvalidRuntimeRequest),
        (error(503, "runtime_draining"), RuntimeDraining),
        (error(500, "internal_error"), RuntimeUnavailable),
        (httpx.Response(200, text="not json"), RuntimeUnavailable),
    ]
    for response, expected in cases:
        runtime, _ = runtime_with(lambda request, response=response: response)
        with pytest.raises(expected) as raised:
            runtime.heartbeat(RUN_ID, lease_owner="w", lease_version=1, lease_seconds=5)
        if expected is IdempotencyConflict:
            assert raised.value.existing_run_id == RUN_ID
        runtime.close()


def test_connection_failures_are_runtime_unavailable():
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    runtime, _ = runtime_with(refuse)
    with pytest.raises(RuntimeUnavailable):
        runtime.get_run(RUN_ID)
    assert runtime.ready() is False
    runtime.close()


def test_claim_returns_none_when_nothing_is_eligible_and_sends_scope():
    runtime, requests = runtime_with(lambda request: httpx.Response(204))
    assert (
        runtime.claim(
            product="grcinsight",
            workflow_name="generate_report",
            workflow_version="grc-report-runtime-v1",
            lease_owner="worker-1",
            lease_seconds=15,
        )
        is None
    )
    assert json.loads(requests[0].content) == {
        "product": "grcinsight",
        "workflow_name": "generate_report",
        "workflow_version": "grc-report-runtime-v1",
        "lease_owner": "worker-1",
        "lease_duration_seconds": 15,
    }
    runtime.close()


def test_lease_mutations_send_only_documented_fields():
    runtime, requests = runtime_with(lambda request: httpx.Response(200, json={"run_id": RUN_ID}))
    runtime.complete(RUN_ID, lease_owner="w", lease_version=2, output_ref={"schema": "s"})
    runtime.fail(
        RUN_ID, lease_owner="w", lease_version=2, error_code="invalid_input", error_summary="x"
    )
    runtime.heartbeat(RUN_ID, lease_owner="w", lease_version=2, lease_seconds=9)
    assert [request.url.path for request in requests] == [
        f"/v1/runs/{RUN_ID}/complete",
        f"/v1/runs/{RUN_ID}/fail",
        f"/v1/runs/{RUN_ID}/heartbeat",
    ]
    assert json.loads(requests[0].content) == {
        "lease_owner": "w",
        "lease_version": 2,
        "output_ref": {"schema": "s"},
    }
    assert json.loads(requests[1].content) == {
        "lease_owner": "w",
        "lease_version": 2,
        "error_code": "invalid_input",
        "error_summary": "x",
    }
    assert json.loads(requests[2].content) == {
        "lease_owner": "w",
        "lease_version": 2,
        "lease_duration_seconds": 9,
    }
    runtime.close()


def test_run_ids_are_validated_before_building_paths():
    runtime, requests = runtime_with(lambda request: httpx.Response(200, json={}))
    with pytest.raises(ValueError):
        runtime.get_run("../v1/worker/claims")
    assert requests == []
    runtime.close()


def test_client_does_not_read_proxy_environment():
    assert client_mod.CLIENT_TRUSTS_ENVIRONMENT is False


class ClosableTransport(httpx.BaseTransport):
    """A transport with real close semantics: it refuses requests once closed."""

    def __init__(self):
        self.closed = False
        self.close_calls = 0
        self.requests = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if self.closed:
            raise RuntimeError("transport used after close")
        self.requests += 1
        return httpx.Response(200, json={"run_id": RUN_ID})

    def close(self) -> None:
        self.close_calls += 1
        self.closed = True


@pytest.mark.parametrize("first", ["clone", "parent"])
def test_borrowed_transport_stays_caller_owned_in_either_close_order(first):
    transport = ClosableTransport()
    parent = RuntimeClient("http://127.0.0.1:18080", transport=transport)
    clone = parent.clone()
    closed_first, survivor = (clone, parent) if first == "clone" else (parent, clone)

    closed_first.close()
    closed_first.close()
    assert survivor.get_run(RUN_ID) == {"run_id": RUN_ID}
    survivor.close()
    survivor.close()

    assert (transport.closed, transport.close_calls) == (False, 0)
    transport.close()


@pytest.mark.parametrize("first", ["clone", "parent"])
def test_owned_transports_are_separate_and_closed_exactly_once(first):
    created: list[ClosableTransport] = []

    def factory() -> ClosableTransport:
        created.append(ClosableTransport())
        return created[-1]

    parent = client_mod.RuntimeClient("http://127.0.0.1:18080", transport_factory=factory)
    clone = parent.clone()
    assert len(created) == 2 and created[0] is not created[1]
    closed_first, survivor = (clone, parent) if first == "clone" else (parent, clone)

    closed_first.close()
    closed_first.close()
    assert survivor.get_run(RUN_ID) == {"run_id": RUN_ID}
    survivor.close()
    survivor.close()

    assert [transport.close_calls for transport in created] == [1, 1]


def test_requests_after_close_are_refused_without_touching_the_transport():
    transport = ClosableTransport()
    runtime = RuntimeClient("http://127.0.0.1:18080", transport=transport)
    runtime.close()
    with pytest.raises(client_mod.ClientClosed):
        runtime.get_run(RUN_ID)
    with pytest.raises(client_mod.ClientClosed):
        runtime.clone()
    assert transport.requests == 0
    assert runtime.ready() is False


def test_borrowed_and_owned_transports_are_exclusive():
    with pytest.raises(ValueError):
        client_mod.RuntimeClient(
            "http://127.0.0.1:18080",
            transport=ClosableTransport(),
            transport_factory=ClosableTransport,
        )


def test_default_owned_transports_and_clones_never_read_the_environment(monkeypatch, tmp_path):
    keylog = tmp_path / "tls-keys.log"
    not_a_ca = tmp_path / "not-a-ca.pem"
    not_a_ca.write_text("not a certificate\n")
    monkeypatch.setenv("SSLKEYLOGFILE", str(keylog))
    monkeypatch.setenv("SSL_CERT_FILE", str(not_a_ca))
    monkeypatch.setenv("SSL_CERT_DIR", str(tmp_path))
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:9")
    monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:9")

    runtime = RuntimeClient("http://127.0.0.1:18080")
    clone = runtime.clone()
    clone.close()
    runtime.close()

    assert not keylog.exists(), "an owned transport must not honour SSLKEYLOGFILE"
