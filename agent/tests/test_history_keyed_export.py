"""Bounded export of one report by key, for downstream consumers such as the newsletter."""

from __future__ import annotations

import json

import pytest

from history import fixture as fx
from history.export import (
    KeyedReadBoundExceeded,
    ReportNotFound,
    export_all,
    export_report,
)


class KeyOnly:
    """Wraps a table, counts GetItem calls and refuses any Scan."""

    def __init__(self, table):
        self.table = table
        self.name = table.name
        self.key_name = table.key_name
        self.gets: list[str] = []

    def get(self, key):
        self.gets.append(key)
        return self.table.get(key)

    def scan_page(self, *_args, **_kwargs):
        raise AssertionError("keyed export must never scan")


@pytest.fixture
def scenario():
    reports, articles, _ = fx.build_scenarios()
    return KeyOnly(reports), KeyOnly(articles)


def records(doc, stream):
    return [r for page in doc[stream] for r in page["records"]]


def test_exports_one_report_with_bounded_key_reads(scenario):
    reports, articles = scenario
    doc = export_report(reports, articles, "report_s2")
    n = len(reports.table.items["report_s2"]["article_revision_ids"])
    keyed = doc["reports"][0]["coverage"]["keyed_read"]
    assert keyed == {
        "report_id": "report_s2",
        "get_item_calls": 1 + 2 * n,
        "missing_keys": 0,
        "missing_key_ids": [],
    }
    assert len(reports.gets) + len(articles.gets) == 1 + 2 * n
    arts = records(doc, "articles")
    kinds = [r["record_type"] for r in arts]
    assert kinds.count("source_article_revision") == n
    assert kinds.count("report_article_appearance") == n
    (report,) = records(doc, "reports")
    assert report["outcome"] == "model_completed" and report["conclusion_status"] == "verified"
    assert report["publication"] == {"status": "not_established_by_store"}


def test_records_are_the_paged_exporters_records(scenario):
    """One representation owner: keyed records equal the paged exporter's, digest for digest."""
    reports, articles = scenario
    doc = export_report(reports, articles, "report_s2")
    paged = {
        r["record_id"]: r
        for stream, table in (("reports", reports.table), ("articles", articles.table))
        for page in export_all(table, stream=stream, limit=200)
        for r in page["records"]
    }
    for record in records(doc, "reports") + records(doc, "articles"):
        assert record == paged[record["record_id"]]
        assert record["record_revision"] != record["source_revision"]


def test_corrupt_revision_is_exported_and_counted(scenario):
    reports, articles = scenario
    doc = export_report(reports, articles, "report_s1")
    corrupt = [
        r for r in records(doc, "articles") if (r.get("integrity") or {}).get("status") == "corrupt"
    ]
    assert len(corrupt) == 1 and corrupt[0]["url"].endswith("/bravo")
    assert doc["articles"][0]["coverage"]["integrity_problems"] == 1


def test_missing_keys_are_listed_not_fatal(scenario):
    reports, articles = scenario
    first = reports.table.items["report_s2"]["article_revision_ids"][0]
    del articles.table.items[first]
    doc = export_report(reports, articles, "report_s2")
    keyed = doc["reports"][0]["coverage"]["keyed_read"]
    assert keyed["missing_keys"] == 1 and keyed["missing_key_ids"] == [first]


@pytest.mark.parametrize(
    "report_id,outcome",
    [
        ("report_s3", "refused_fallback"),
        ("report_s4", "failed"),
        ("report_20251001_090000_123", "legacy_completed_unverified"),
    ],
)
def test_non_intelligence_and_legacy_outcomes_are_preserved(scenario, report_id, outcome):
    reports, articles = scenario
    doc = export_report(reports, articles, report_id)
    (report,) = records(doc, "reports")
    assert report["outcome"] == outcome
    if outcome != "legacy_completed_unverified":
        assert "generated_conclusions" not in report
    else:
        assert report["provenance_class"] == "legacy_unknown"


def test_unknown_report_is_an_error(scenario):
    reports, articles = scenario
    with pytest.raises(ReportNotFound):
        export_report(reports, articles, "no-such-report")


def test_oversized_report_is_refused_before_reading_articles(scenario):
    reports, articles = scenario
    with pytest.raises(KeyedReadBoundExceeded):
        export_report(reports, articles, "report_s2", max_revisions=1)
    assert articles.gets == []


def test_keyed_export_is_deterministic(scenario):
    reports, articles = scenario
    first = json.dumps(export_report(reports, articles, "report_s2"), sort_keys=True)
    second = json.dumps(export_report(reports, articles, "report_s2"), sort_keys=True)
    assert first == second


def test_cli_writes_the_document_and_prints_a_content_free_summary(
    scenario, tmp_path, monkeypatch, capsys
):
    import history.__main__ as cli

    reports, articles = scenario
    monkeypatch.setattr(cli, "_keyed_tables", lambda *a, **k: (reports, articles))
    out = tmp_path / "keyed.json"
    code = cli.main(["export-report", "--report-id", "report_s2", "--out", str(out)])
    assert code == 0
    doc = json.loads(out.read_text())
    assert records(doc, "reports")[0]["report_id"] == "report_s2"
    summary = json.loads(capsys.readouterr().out)
    assert summary["outcome"] == "model_completed" and summary["missing_keys"] == 0
    assert "content_markdown" not in json.dumps(summary)
    assert cli.main(["export-report", "--report-id", "nope", "--out", str(out)]) == 2


def test_fixture_includes_byte_stable_keyed_exports(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    fx.write_fixture(a)
    fx.write_fixture(b)
    for report_id in fx.KEYED_FIXTURE_REPORTS:
        name = f"keyed/{report_id}.json"
        assert (a / name).read_bytes() == (b / name).read_bytes()
        doc = json.loads((a / name).read_text())
        assert doc["reports"][0]["records"][0]["report_id"] == report_id
