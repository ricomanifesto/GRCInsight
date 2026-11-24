"""Warm Lambda invocation sequences with fake workflows and database reads."""

import asyncio
import json
from types import SimpleNamespace

import pytest

import lambda_main
from api.routes import workflow
from core.runtime import get_model_deadline, get_report_id
from models.api import WorkflowResponse


@pytest.fixture
def isolated_loop_policy():
    original = asyncio.get_event_loop_policy()
    policy = asyncio.DefaultEventLoopPolicy()
    asyncio.set_event_loop_policy(policy)
    asyncio.set_event_loop(None)
    try:
        yield policy
    finally:
        try:
            current = policy.get_event_loop()
        except RuntimeError:
            current = None
        if current is not None and not current.is_closed():
            current.close()
        asyncio.set_event_loop_policy(original)


def api_event(path="/"):
    return {
        "resource": "/{proxy+}",
        "httpMethod": "GET",
        "path": path,
        "headers": {"X-API-Key": "synthetic-loop-test-key"},
        "requestContext": {"stage": "test", "identity": {"sourceIp": "127.0.0.1"}},
        "body": None,
        "isBase64Encoded": False,
    }


def test_direct_report_then_protected_status_can_repeat_in_one_process(
    monkeypatch, isolated_loop_policy
):
    monkeypatch.setenv("API_KEY", "synthetic-loop-test-key")
    rows = {}
    observed_report_ids = []
    queried_report_ids = []
    workflow_loops = []
    status_loops = []

    async def generate(_feed_url, _config, **_kwargs):
        workflow_loops.append(asyncio.get_running_loop())
        observed_report_ids.append(get_report_id())
        await asyncio.sleep(0)
        return WorkflowResponse(status="completed")

    def commit(report_id, _event, _context, _result):
        rows[report_id] = {"report_id": report_id, "status": "completed"}
        return {"statusCode": 200, "body": {"decision": "committed"}}

    class Table:
        def get_item(self, Key):
            status_loops.append(asyncio.get_running_loop())
            queried_report_ids.append(Key["report_id"])
            return {"Item": rows[Key["report_id"]]}

    monkeypatch.setattr("core.workflow.run_grc_analysis_endpoint", generate)
    monkeypatch.setattr(lambda_main, "_commit_report", commit)
    monkeypatch.setattr(
        workflow,
        "boto3",
        SimpleNamespace(resource=lambda _service: SimpleNamespace(Table=lambda _name: Table())),
    )
    for index in range(3):
        report_id = f"report_20261123_230000_{index:03d}"
        direct = lambda_main.handler(
            {
                "feed_url": "https://feed.example.test/rss",
                "report_id": report_id,
                "job_id": f"fictional-job-{index}",
            },
            object(),
        )
        assert direct["statusCode"] == 200
        assert workflow_loops[-1].is_closed()
        status = lambda_main.handler(api_event(f"/api/v1/workflow/status/{report_id}"), object())
        assert status["statusCode"] == 200
        assert status_loops[-1].is_closed()
        assert json.loads(status["body"])["status"] == "completed"
        assert get_report_id() is None and get_model_deadline() is None
        with pytest.raises(RuntimeError, match="no current event loop"):
            isolated_loop_policy.get_event_loop()
    assert (
        observed_report_ids
        == queried_report_ids
        == [f"report_20261123_230000_{i:03d}" for i in range(3)]
    )


@pytest.mark.parametrize("has_caller_loop", [False, True])
@pytest.mark.parametrize("adapter_fails", [False, True])
def test_api_invocation_closes_its_loop_and_restores_caller_state(
    monkeypatch, isolated_loop_policy, has_caller_loop, adapter_fails
):
    caller = asyncio.new_event_loop() if has_caller_loop else None
    asyncio.set_event_loop(caller)
    observed = []

    def adapter(_event, _context):
        observed.append(asyncio.get_event_loop())
        assert get_model_deadline() == 123456.0
        if adapter_fails:
            raise ValueError("fictional adapter failure")
        return {"statusCode": 200}

    monkeypatch.setattr(lambda_main, "mangum_handler", adapter)
    monkeypatch.setattr(lambda_main, "_lambda_model_deadline", lambda _context: 123456.0)
    if adapter_fails:
        with pytest.raises(ValueError, match="fictional adapter failure"):
            lambda_main.handler(api_event(), object())
    else:
        assert lambda_main.handler(api_event(), object())["statusCode"] == 200
    assert observed[0] is not caller and observed[0].is_closed()
    if caller is None:
        with pytest.raises(RuntimeError, match="no current event loop"):
            isolated_loop_policy.get_event_loop()
    else:
        assert isolated_loop_policy.get_event_loop() is caller and not caller.is_closed()
    assert get_model_deadline() is None


def test_cold_api_first_keeps_one_policy_owned_ambient_loop(monkeypatch, isolated_loop_policy):
    cold_policy = asyncio.DefaultEventLoopPolicy()
    asyncio.set_event_loop_policy(cold_policy)
    owned = []
    ambient = None

    def adapter(_event, _context):
        owned.append(asyncio.get_event_loop())
        return {"statusCode": 200}

    monkeypatch.setattr(lambda_main, "mangum_handler", adapter)
    try:
        assert lambda_main.handler(api_event(), object())["statusCode"] == 200
        ambient = cold_policy.get_event_loop()
        assert owned[-1].is_closed() and not ambient.is_closed()
        assert lambda_main.handler(api_event(), object())["statusCode"] == 200
        assert owned[-1].is_closed() and cold_policy.get_event_loop() is ambient
    finally:
        if ambient is None:
            ambient = cold_policy.get_event_loop()
        ambient.close()
        asyncio.set_event_loop(None)
        asyncio.set_event_loop_policy(isolated_loop_policy)


def test_api_reentry_does_not_change_an_already_running_caller_loop(
    monkeypatch, isolated_loop_policy
):
    def unexpected(*_args):
        raise AssertionError("adapter must not be entered from a running caller loop")

    monkeypatch.setattr(lambda_main, "mangum_handler", unexpected)

    async def caller():
        loop = asyncio.get_running_loop()
        with pytest.raises(RuntimeError, match="running event loop"):
            lambda_main.handler(api_event(), object())
        assert asyncio.get_running_loop() is loop
        assert get_model_deadline() is None

    asyncio.run(caller())
