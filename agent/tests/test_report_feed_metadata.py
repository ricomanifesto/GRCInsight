import asyncio
from copy import deepcopy

import pytest

from core import workflow
from models.api import GRCAnalysisConfig
from services import model_service
from services.model_service import GRCModelService
from services.openrouter_client import OpenRouterGeneration
from test_report_workflow_contract import complete_report_body
from test_virtual_event_policy import MARKERS, article, feed_entries

MODEL_REPORT = complete_report_body(
    "Model-backed regulatory analysis.", "- [Security guidance](https://example.com/security)"
)


def clean_analysis():
    return {
        "summary": {"total_articles": 1, "grc_relevant_count": 1},
        "analysis": {"regulations_mentioned": ["NIST"]},
        "source_evidence": [{"title": "Security guidance", "url": "https://example.com/security"}],
    }


def report_service(monkeypatch):
    service = GRCModelService.__new__(GRCModelService)
    prompts = []

    async def invoke(**kwargs):
        prompts.append(kwargs["user_prompt"])
        return OpenRouterGeneration(text=MODEL_REPORT, resolved_model="provider/test-model")

    monkeypatch.setattr(service, "_invoke", invoke)
    return service, prompts


@pytest.mark.parametrize("field", ["description", "unused_channel_metadata"])
@pytest.mark.parametrize("marker", MARKERS)
def test_unused_channel_metadata_does_not_block_model_report(monkeypatch, field, marker):
    service, prompts = report_service(monkeypatch)
    feed = {"title": "Security Feed", field: {"blurb": f"{marker} Channel promotion"}}
    before = deepcopy(feed)

    result = asyncio.run(service.generate_grc_report(clean_analysis(), feed))

    assert result.content == MODEL_REPORT
    assert result.resolved_model == "provider/test-model"
    assert len(prompts) == 1
    assert "Source: Security Feed" in prompts[0]
    assert "Channel promotion" not in prompts[0]
    assert marker not in prompts[0]
    assert feed == before


@pytest.mark.parametrize("marker", MARKERS)
def test_report_bound_title_is_rejected_before_invocation(monkeypatch, marker):
    service, prompts = report_service(monkeypatch)
    feed = {"title": f"{marker} Channel promotion", "description": "Ordinary channel blurb"}
    before = deepcopy(feed)

    result = asyncio.run(service.generate_grc_report(clean_analysis(), feed))

    assert prompts == []
    assert result.content.startswith("# GRC Intelligence Report - Error")
    assert result.resolved_model == ""
    assert feed == before


def test_content_gate_and_prompt_share_exact_feed_projection(monkeypatch):
    service, prompts = report_service(monkeypatch)
    original_gate = model_service.contains_virtual_event
    original_prompt = service._create_report_prompt
    checked = []
    prompted = []

    def capture_gate(value):
        checked.append(value)
        return original_gate(value)

    def capture_prompt(analysis_data, metadata):
        prompted.append(metadata)
        return original_prompt(analysis_data, metadata)

    monkeypatch.setattr(model_service, "contains_virtual_event", capture_gate)
    monkeypatch.setattr(service, "_create_report_prompt", capture_prompt)
    feed = {"title": "Security Feed", "description": "Unused blurb", "nested": {"unused": []}}
    before = deepcopy(feed)

    result = asyncio.run(service.generate_grc_report(clean_analysis(), feed))

    assert result.content == MODEL_REPORT
    assert len(prompts) == 1
    assert prompted == [{"title": "Security Feed"}]
    assert any(value is prompted[0] for value in checked)
    assert prompted[0] is not feed
    assert feed == before


@pytest.mark.parametrize(
    ("feed", "expected_title"),
    [({}, "Unknown Feed"), ({"title": ""}, ""), ({"title": None}, "None"), ({"title": 123}, "123")],
)
def test_feed_projection_preserves_prompt_title_semantics(monkeypatch, feed, expected_title):
    service, prompts = report_service(monkeypatch)
    result = asyncio.run(service.generate_grc_report(clean_analysis(), feed))
    assert result.content == MODEL_REPORT
    assert len(prompts) == 1
    assert f"\nSource: {expected_title}\n" in prompts[0]


def test_tagged_unused_channel_description_keeps_workflow_model_backed(monkeypatch):
    feed = feed_entries([article()])
    feed["description"] = "[Virtual Event] Channel promotion"
    before = deepcopy(feed)
    prompts = []

    async def fetch(_url):
        return feed

    async def enrich(articles):
        return articles

    class Model(GRCModelService):
        def __init__(self, **_kwargs):
            pass

        async def analyze_articles_for_grc(self, articles):
            assert len(articles) == 1
            return clean_analysis()

        async def _invoke(self, **kwargs):
            prompts.append(kwargs["user_prompt"])
            return OpenRouterGeneration(text=MODEL_REPORT, resolved_model="provider/test-model")

    monkeypatch.setattr(workflow.rss_service, "fetch_feed", fetch)
    monkeypatch.setattr(workflow.rss_service, "enrich_articles", enrich)
    monkeypatch.setattr(workflow, "GRCModelService", Model)
    result = asyncio.run(
        workflow.run_grc_analysis_endpoint("https://digest.example/feed.xml", GRCAnalysisConfig())
    )

    assert result.status == "completed"
    assert result.metadata is not None and result.report is not None
    assert result.metadata.analysis_mode == "model"
    assert result.metadata.fallback_reason is None
    assert result.metadata.resolved_model == "provider/test-model"
    assert result.metadata.article_count == 1
    assert result.report.content == MODEL_REPORT
    assert len(prompts) == 1
    assert "Channel promotion" not in prompts[0]
    assert feed == before
