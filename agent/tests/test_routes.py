import asyncio
from typing import Any, cast

import httpx

# Import the FastAPI app
from main import app


def request(method, url, **kwargs):
    async def send():
        transport = httpx.ASGITransport(app=cast(Any, app))
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(send())


def test_health_basic_ok():
    resp = request("GET", "/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert data.get("status") in {"healthy", "unhealthy"}


def test_analyze_with_fake_model_service(monkeypatch):
    """Patch GRCModelService used in analysis route to avoid network calls."""
    from api.routes import analysis as analysis_route

    class FakeGRCModelService:
        def __init__(self):
            pass

        async def analyze_articles_for_grc(self, articles):
            # Return a deterministic, small payload similar to the real shape
            return {
                "grc_articles": [{"title": articles[0].title, "url": articles[0].url}],
                "summary": {"total_articles": len(articles), "grc_relevant_count": 1},
                "analysis": {
                    "regulations_mentioned": ["GDPR"],
                    "frameworks_referenced": ["ISO 27001"],
                    "industries_affected": ["Technology"],
                },
            }

    monkeypatch.setattr(analysis_route, "GRCModelService", FakeGRCModelService)

    payload = {
        "articles": [
            {
                "title": "Test",
                "url": "https://example.com/a",
                "content": "Compliance and governance news",
                "summary": "",
                "source": "TestFeed",
                "published": "2025-01-01T00:00:00Z",
            }
        ],
        "config": {
            "model": "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
            "max_tokens": 16000,
            "focus_areas": [],
        },
    }

    resp = request("POST", "/api/v1/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["summary"]["total_articles"] == 1
    assert data["summary"]["grc_articles"] == 1
    assert isinstance(data["results"], list) and len(data["results"]) == 1


def test_workflow_status_success(monkeypatch):
    from api.routes import workflow as wf_route

    class FakeTable:
        def __init__(self, item):
            self._item = item

        def get_item(self, Key):  # noqa: N802
            return {"Item": self._item}

    class FakeDynamo:
        def __init__(self, item):
            self._item = item

        def Table(self, name):  # noqa: N802
            return FakeTable(self._item)

    class FakeBoto3:
        def __init__(self, item):
            self._ddb = FakeDynamo(item)

        def resource(self, name):  # noqa: A003
            assert name == "dynamodb"
            return self._ddb

    item = {
        "report_id": "rep123",
        "status": "completed",
        "title": "T",
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z",
        "generated_at": "2025-01-01T00:00:00Z",
        "metadata": {},
    }

    # Patch boto3 resource in workflow route
    monkeypatch.setitem(wf_route.__dict__, "boto3", FakeBoto3(item))

    resp = request("GET", "/api/v1/workflow/status/rep123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_id"] == "rep123"
    assert data["status"] == "completed"


def test_workflow_status_not_found(monkeypatch):
    from api.routes import workflow as wf_route

    class FakeTable:
        def get_item(self, Key):  # noqa: N802
            return {}

    class FakeDynamo:
        def Table(self, name):  # noqa: N802
            return FakeTable()

    class FakeBoto3:
        def resource(self, name):  # noqa: A003
            return FakeDynamo()

    monkeypatch.setitem(wf_route.__dict__, "boto3", FakeBoto3())
    resp = request("GET", "/api/v1/workflow/status/does-not-exist")
    assert resp.status_code == 404


def test_health_deep_true_with_fake_model_service(monkeypatch):
    from api.routes import health as health_route

    class FakeGRCModelService:
        def __init__(self):
            class Model:
                provider_id = "openai"
                model_id = "gpt-5"

            self.model = Model()

        async def _invoke(self, **_kwargs):
            return "ok"

    monkeypatch.setattr(health_route, "GRCModelService", FakeGRCModelService)

    resp = request("GET", "/api/v1/health?deep=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["services"]["llm"]["status"] == "healthy"
    assert data["services"]["llm"]["provider"] == "openai"
