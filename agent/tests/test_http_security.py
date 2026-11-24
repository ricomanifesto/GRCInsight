"""Defensive boundary checks with synthetic credentials and offline service fakes."""

import asyncio
from datetime import datetime, timezone

import httpx
import pytest
from pydantic import ValidationError

import lambda_main
from config.settings import Settings
from main import app
from models.api import AnalysisRequest, ArticleInput, GRCAnalysisConfig, WorkflowResponse
from services import model_service, rss_service
from services.openrouter_client import OpenRouterClient, OpenRouterError

AUTH = {"X-API-Key": "synthetic-api-key"}


@pytest.fixture(autouse=True)
def isolated_http_budget(monkeypatch):
    from api import security

    monkeypatch.setattr(security, "work_budget", security.WorkBudget())


def request(target, method, path, **kwargs):
    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=target), base_url="http://testserver"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(send())


def article(**changes):
    return ArticleInput.model_validate(
        {
            "title": "Fictional compliance update",
            "url": "https://publisher.example/notice",
            "content": "A fictional control owner reviews an audit policy.",
            "published": datetime(2026, 11, 23, tzinfo=timezone.utc),
            **changes,
        }
    )


@pytest.mark.parametrize("target", [app, lambda_main.app])
@pytest.mark.parametrize(
    "method,path,body",
    [
        ("POST", "/api/v1/workflow/run", {"feed_url": "https://publisher.example/rss"}),
        ("POST", "/api/v1/analyze", {"articles": []}),
        ("POST", "/api/v1/rss/fetch?feed_url=https://publisher.example/rss", None),
        ("POST", "/api/v1/rss/enrich", []),
        ("POST", "/api/v1/extract/entities?text=fictional", None),
        ("GET", "/api/v1/workflow/status/fictional-report", None),
        ("GET", "/api/v1/health?deep=true", None),
    ],
)
def test_sensitive_http_routes_fail_closed(monkeypatch, target, method, path, body):
    def unavailable(*_args, **_kwargs):
        raise AssertionError("unauthorized request reached a service")

    monkeypatch.setenv("API_KEY", "synthetic-api-key")
    monkeypatch.setattr("api.routes.analysis.GRCModelService", unavailable)
    monkeypatch.setattr("api.routes.health.GRCModelService", unavailable)
    monkeypatch.setattr("api.routes.workflow.run_grc_analysis_endpoint", unavailable)
    monkeypatch.setattr("api.routes.workflow.boto3", None)
    monkeypatch.setattr("api.routes.rss.rss_service.fetch_feed", unavailable)
    monkeypatch.setattr("api.routes.rss.rss_service.enrich_articles", unavailable)
    for headers in ({}, {"X-API-Key": "different-synthetic-key"}):
        assert request(target, method, path, json=body, headers=headers).status_code == 403
    monkeypatch.setenv("API_KEY", "")
    assert request(target, method, path, json=body, headers=AUTH).status_code == 403


@pytest.mark.parametrize("target", [app, lambda_main.app])
@pytest.mark.parametrize(
    "path", ["/", "/api/v1/health", "/api/v1/health/live", "/api/v1/health/ready"]
)
def test_basic_health_is_public_and_has_no_paid_or_aws_work(monkeypatch, target, path):
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setenv("DDB_TABLE_NAME", "fictional-table")

    class NoAWS:
        def client(self, *_args, **_kwargs):
            raise AssertionError("public health reached AWS")

    monkeypatch.setattr("api.routes.health.boto3", NoAWS())
    response = request(target, "GET", path)
    assert response.status_code == 200
    assert "fictional-table" not in response.text


def test_authenticated_analysis_uses_requested_output_cap(monkeypatch):
    observed = []

    class FakeModel:
        def __init__(self, **kwargs):
            observed.append(kwargs)

        async def analyze_articles_for_grc(self, articles):
            return {"summary": {}, "analysis": {}}

    monkeypatch.setenv("API_KEY", "synthetic-api-key")
    monkeypatch.setattr("api.routes.analysis.GRCModelService", FakeModel)
    response = request(
        app,
        "POST",
        "/api/v1/analyze",
        headers=AUTH,
        json={"articles": [], "config": {"max_tokens": 256}},
    )
    assert response.status_code == 200
    assert observed[0]["max_tokens"] == 256


def test_request_bounds_reject_volume_and_unowned_model():
    with pytest.raises(ValidationError):
        AnalysisRequest(articles=[article()] * 51)
    with pytest.raises(ValidationError):
        AnalysisRequest(articles=[article(content="x" * 100_001)])
    with pytest.raises(ValidationError):
        AnalysisRequest(articles=[article(content="x" * 100_000)] * 11)
    with pytest.raises(ValidationError):
        GRCAnalysisConfig(model="openrouter/fictional/unowned-model")


@pytest.mark.parametrize("model", [None, ""])
def test_missing_or_blank_model_selects_the_server_model(monkeypatch, model):
    monkeypatch.setattr(model_service.settings, "llm_model", "openrouter/fictional/server-model")
    config = GRCAnalysisConfig(**({} if model is None else {"model": model}))
    assert config.model == "openrouter/fictional/server-model"
    observed = []

    async def workflow(_feed, config, **_kwargs):
        observed.append(config.model)
        return WorkflowResponse(status="completed")

    monkeypatch.setattr("core.workflow.run_grc_analysis_endpoint", workflow)
    response = lambda_main.handler(
        {
            "feed_url": "https://publisher.example/rss",
            "config": {} if model is None else {"model": model},
        },
        object(),
    )
    assert response["statusCode"] == 200
    assert observed == ["openrouter/fictional/server-model"]


def test_internal_analysis_checks_volume_before_model_call(monkeypatch):
    monkeypatch.setattr(model_service.settings, "openrouter_api_key", "synthetic")
    service = model_service.GRCModelService()

    async def unavailable(**_kwargs):
        raise AssertionError("oversized internal analysis reached model client")

    monkeypatch.setattr(service, "_invoke", unavailable)
    with pytest.raises(ValueError, match="articles"):
        asyncio.run(service.analyze_articles_for_grc([article()] * 51))


def test_cors_defaults_are_explicit_and_never_allow_browser_credentials():
    origins = Settings.model_fields["cors_allowed_origins"].default
    assert origins and "*" not in origins
    with pytest.raises(ValidationError):
        Settings(cors_allowed_origins=["*"])
    for target in (app, lambda_main.app):
        response = request(
            target,
            "OPTIONS",
            "/api/v1/analyze",
            headers={
                "Origin": "https://fictional-unlisted.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-API-Key",
            },
        )
        assert "access-control-allow-origin" not in response.headers
        assert "access-control-allow-credentials" not in response.headers


def test_http_work_budget_refuses_before_a_second_call_and_releases(monkeypatch):
    from api import security

    monkeypatch.setenv("API_KEY", "synthetic-api-key")
    budget = security.WorkBudget(max_calls=1, max_active=1, window_seconds=60, clock=lambda: 1.0)
    monkeypatch.setattr(security, "work_budget", budget)
    calls = []

    async def workflow(*_args, **_kwargs):
        calls.append(1)
        return WorkflowResponse(status="completed")

    monkeypatch.setattr("api.routes.workflow.run_grc_analysis_endpoint", workflow)
    body = {"feed_url": "https://publisher.example/rss"}
    assert request(app, "POST", "/api/v1/workflow/run", json=body, headers=AUTH).status_code == 200
    assert budget.active == 0
    response = request(app, "POST", "/api/v1/workflow/run", json=body, headers=AUTH)
    assert response.status_code == 429 and calls == [1]


def test_http_work_budget_limits_concurrency_and_recovers_after_window():
    from api.security import WorkBudget
    from fastapi import HTTPException

    now = [0.0]
    budget = WorkBudget(max_calls=2, max_active=1, window_seconds=60, clock=lambda: now[0])
    budget.acquire()
    with pytest.raises(HTTPException) as refused:
        budget.acquire()
    assert refused.value.status_code == 429
    budget.release()
    budget.acquire()
    budget.release()
    with pytest.raises(HTTPException):
        budget.acquire()
    now[0] = 60.0
    budget.acquire()
    budget.release()
    assert budget.active == 0


@pytest.mark.parametrize("target", [app, lambda_main.app])
def test_request_bytes_are_bounded_without_content_length(monkeypatch, target):
    monkeypatch.setenv("API_KEY", "synthetic-api-key")

    async def chunks():
        for _ in range(3):
            yield b" " * 1_000_000

    response = request(
        target,
        "POST",
        "/api/v1/analyze",
        content=chunks(),
        headers={**AUTH, "Content-Type": "application/json"},
    )
    assert response.status_code == 413


def test_feed_count_and_enrichment_requests_are_bounded(monkeypatch):
    calls = []

    async def fetch(url, **_kwargs):
        calls.append(url)
        return "Publisher page", False

    monkeypatch.setattr(rss_service, "fetch_public_text", fetch)
    articles = [article(url=f"https://publisher.example/{i}", content="") for i in range(51)]
    with pytest.raises(ValueError, match="article"):
        asyncio.run(rss_service.RSSService().enrich_articles(articles))
    assert calls == []
    body = (
        "<rss><channel><title>Fictional</title>"
        + "".join(
            f"<item><title>Notice {i}</title><link>https://publisher.example/{i}</link></item>"
            for i in range(55)
        )
        + "</channel></rss>"
    )

    async def feed(*_args, **_kwargs):
        return body, False

    monkeypatch.setattr(rss_service, "fetch_public_text", feed)
    result = asyncio.run(rss_service.RSSService().fetch_feed("https://publisher.example/rss"))
    assert result["entry_count"] == 50


def test_enrichment_has_an_aggregate_deadline(monkeypatch):
    calls = []
    now = [0.0]

    async def fetch(url, **kwargs):
        calls.append(kwargs["timeout"])
        now[0] += 16.0
        return "Fictional page", False

    monkeypatch.setattr(rss_service, "fetch_public_text", fetch)
    monkeypatch.setattr(rss_service.time, "monotonic", lambda: now[0])
    result = asyncio.run(
        rss_service.RSSService().enrich_articles(
            [article(content="", url=f"https://publisher.example/{i}") for i in range(5)]
        )
    )
    assert len(calls) == 2 and calls == [10.0, 10.0]
    assert result[2].content == ""


@pytest.mark.parametrize(
    "error",
    [
        {"code": ["fictional"], "metadata": {"error_type": {"fictional": True}}},
        {"code": "fictional\nprovider", "metadata": {"error_type": "x" * 200}},
        {"code": True},
    ],
)
def test_provider_errors_are_typed_bounded_and_application_owned(error):
    client = OpenRouterClient(api_key="synthetic", max_tokens=256)
    failure = client._provider_error(error)
    assert isinstance(failure, OpenRouterError)
    assert str(failure) == "OpenRouter generation failed: unknown"
    assert not failure.retryable


def test_provider_retry_codes_remain_usable():
    client = OpenRouterClient(api_key="synthetic", max_tokens=256)
    assert client._provider_error({"code": 429}).retryable
    assert client._provider_error({"metadata": {"error_type": "provider_overloaded"}}).retryable


def test_model_failure_does_not_reflect_provider_text(monkeypatch):
    monkeypatch.setattr(model_service.settings, "openrouter_api_key", "synthetic")
    service = model_service.GRCModelService()

    async def fail(**_kwargs):
        raise RuntimeError("fictional-private-provider-diagnostic")

    monkeypatch.setattr(service, "_invoke", fail)
    result = asyncio.run(service.analyze_articles_for_grc([article()]))
    generated = asyncio.run(service.generate_grc_report({}, {}))
    assert result["error"] == "Model analysis unavailable"
    assert "fictional-private-provider-diagnostic" not in generated.content
    assert generated.failure_reason == "Model report generation unavailable"


def test_http_errors_hide_internal_failure_detail(monkeypatch):
    monkeypatch.setenv("API_KEY", "synthetic-api-key")

    async def fail(*_args, **_kwargs):
        raise RuntimeError("fictional-private-service-diagnostic")

    monkeypatch.setattr("api.routes.workflow.run_grc_analysis_endpoint", fail)
    monkeypatch.setattr("api.routes.rss.rss_service.fetch_feed", fail)
    monkeypatch.setattr("api.routes.rss.rss_service.enrich_articles", fail)
    for path, body in [
        ("/api/v1/workflow/run", {"feed_url": "https://publisher.example/rss"}),
        ("/api/v1/rss/fetch?feed_url=https://publisher.example/rss", None),
        ("/api/v1/rss/enrich", []),
    ]:
        response = request(app, "POST", path, headers=AUTH, json=body)
        assert "fictional-private-service-diagnostic" not in response.text


@pytest.mark.parametrize("stage", ["init", "analysis", "raise"])
def test_analysis_errors_are_application_owned(monkeypatch, stage):
    monkeypatch.setenv("API_KEY", "synthetic-api-key")

    class FakeModel:
        def __init__(self, **_kwargs):
            if stage == "init":
                raise ValueError("fictional-internal-model-diagnostic")

        async def analyze_articles_for_grc(self, _articles):
            if stage == "raise":
                raise RuntimeError("fictional-internal-model-diagnostic")
            return {"error": "fictional-internal-model-diagnostic"}

    monkeypatch.setattr("api.routes.analysis.GRCModelService", FakeModel)
    response = request(app, "POST", "/api/v1/analyze", json={"articles": []}, headers=AUTH)
    assert response.json()["status"] == "failed"
    assert response.json()["error"]["details"] is None
    assert "fictional-internal-model-diagnostic" not in response.text


def test_deep_health_and_status_hide_internal_errors(monkeypatch):
    monkeypatch.setenv("API_KEY", "synthetic-api-key")
    monkeypatch.setenv("DDB_TABLE_NAME", "fictional-private-table")

    class FakeModel:
        class model:
            provider_id = "openrouter"
            model_id = "fictional/model"

        async def _invoke(self, **_kwargs):
            raise RuntimeError("fictional-internal-provider-diagnostic")

    class FakeAWS:
        def client(self, *_args, **_kwargs):
            raise RuntimeError("fictional-internal-database-diagnostic")

        resource = client

    monkeypatch.setattr("api.routes.health.GRCModelService", FakeModel)
    monkeypatch.setattr("api.routes.health.boto3", FakeAWS())
    monkeypatch.setattr("api.routes.workflow.boto3", FakeAWS())
    health = request(app, "GET", "/api/v1/health?deep=true", headers=AUTH)
    status = request(app, "GET", "/api/v1/workflow/status/fictional-report", headers=AUTH)
    assert health.status_code == 200 and health.json()["status"] == "unhealthy"
    assert status.status_code == 500 and status.json() == {"detail": "Status lookup failed"}
    assert "fictional-internal" not in health.text + status.text
    assert "fictional-private-table" not in health.text


def test_internal_workflow_failure_and_direct_lambda_errors_are_generic(monkeypatch):
    from core import workflow

    async def fail(*_args, **_kwargs):
        raise RuntimeError("fictional-internal-workflow-diagnostic")

    monkeypatch.setattr(workflow.rss_service, "fetch_feed", fail)
    result = asyncio.run(
        workflow.run_grc_analysis_endpoint("https://publisher.example/rss", GRCAnalysisConfig())
    )
    assert result.status == "failed" and result.error is not None
    assert result.error.details is None
    assert result.error.code == "WORKFLOW_EXECUTION_ERROR"
    monkeypatch.setattr(workflow, "run_grc_analysis_endpoint", fail)
    monkeypatch.setenv("API_KEY", "")
    response = lambda_main.handler({"feed_url": "https://publisher.example/rss"}, object())
    assert response == {
        "statusCode": 500,
        "body": {"error": "Workflow execution failed", "status": "failed"},
    }
