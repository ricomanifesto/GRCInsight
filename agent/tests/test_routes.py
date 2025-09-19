import asyncio
import json
from typing import Any, Dict, List

from fastapi.testclient import TestClient

# Import the FastAPI app
from main import app  # type: ignore


def test_health_basic_ok():
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert data.get("status") in {"healthy", "unhealthy"}


def test_analyze_with_fake_openai(monkeypatch):
    """Patch OpenAIService used in analysis route to avoid network calls."""
    from api.routes import analysis as analysis_route

    class FakeOpenAIService:
        def __init__(self):
            pass

        async def analyze_articles_for_grc(self, articles):  # type: ignore
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

    # Patch the route's OpenAIService symbol
    monkeypatch.setattr(analysis_route, "OpenAIService", FakeOpenAIService)

    client = TestClient(app)
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
        "config": {"model": "gpt-5", "max_tokens": 4000, "focus_areas": []},
    }

    resp = client.post("/api/v1/analyze", json=payload)
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

    client = TestClient(app)
    resp = client.get("/api/v1/workflow/status/rep123")
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
    client = TestClient(app)
    resp = client.get("/api/v1/workflow/status/does-not-exist")
    assert resp.status_code == 404


def test_health_deep_true_with_fake_openai(monkeypatch):
    from api.routes import health as health_route

    class FakeOpenAIService:
        def __init__(self):
            pass
        async def _invoke_with_fallbacks(self, messages):  # noqa: N802
            class Resp:
                content = "ok"
            return Resp()

    # Force deep path by setting HumanMessage sentinel
    monkeypatch.setattr(health_route, "HumanMessage", object())
    monkeypatch.setattr(health_route, "OpenAIService", FakeOpenAIService)

    client = TestClient(app)
    resp = client.get("/api/v1/health?deep=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["services"]["openai"]["status"] == "healthy"
