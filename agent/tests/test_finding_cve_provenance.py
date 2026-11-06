"""Finding prose uses its own evidence, never another finding's CVE inventory."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from core.report_plan import render_report_plan
from test_report_evidence import stored_report
from test_report_substance import PLAN, SOURCE, publication_tools


def candidate(cve="CVE-2026-12345"):
    source = deepcopy(SOURCE)
    source.pop("digest_url")
    source["cves"] = ["CVE-2026-12345"]
    source["snippet"] += " The vendor tracks this flaw as CVE-2026-12345."
    segment = source["article_evidence"][0]
    segment["text"] = segment["raw_text"] = source["snippet"]
    plan = deepcopy(PLAN)
    row = plan["control_implications"][0]
    row["evidence_excerpt"] = source["snippet"]
    row["headline"] = f"{cve} requires Java support for exploitation"
    row["significance"] = f"Review affected assets for {cve} before assigning remediation."
    data = stored_report(render_report_plan(plan, [source]), plan)
    data["metadata"]["source_articles"] = [source]
    return data, source


def test_cve_in_finding_prose_uses_that_findings_exact_source():
    composer, checker, builder = publication_tools()
    data, _ = candidate()
    markdown = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    manifest = composer["evidence_manifest"](data, composer["source_articles"](data["metadata"]))
    checker["validate_evidence_manifest"](
        markdown,
        builder["report_fields"](markdown),
        json.dumps(manifest),
        require_current_contract=True,
    )
    assert "### CVE-2026-12345" in markdown
    assert checker["find_reader_surface_defect"](markdown, manifest=manifest) is None


def test_finding_cve_passes_complete_generated_site_gate(tmp_path):
    root = Path(__file__).resolve().parents[2]
    for relative in ("site", "scripts", "agent/core", "contracts", "publication"):
        shutil.copytree(root / relative, tmp_path / relative)
    data, _ = candidate()
    data["generated_at"] = "2030-01-01T00:00:00Z"
    report = tmp_path / "report.json"
    report.write_text(json.dumps(data))

    def run(script, *args):
        result = subprocess.run(
            [sys.executable, str(tmp_path / "scripts" / script), *args],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    run(
        "compose_site_report.py",
        "--input",
        str(report),
        "--feed-url",
        data["metadata"]["source_url"],
        "--model",
        data["metadata"]["requested_model"],
    )
    run(
        "publication_state.py",
        "record-published",
        "--manifest",
        "site/evidence-manifest.json",
        "--output",
        "site/publication-state.json",
        "--history",
        "site/publication-history.json",
        "--event-at",
        data["generated_at"],
    )
    run("build_site.py", "--archive-current")
    run("build_site.py", "--check")
    run("check_site_report.py", "--require-current-contract")
    run("check_site_renderer.py")


@pytest.mark.parametrize(
    "mutation",
    ["missing-manifest", "edited-body", "unsupported", "duplicate-url", "outside-finding"],
)
def test_reader_surface_only_accepts_exact_supported_finding_prose(mutation):
    composer, checker, _ = publication_tools()
    data, _ = candidate()
    markdown = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    manifest = composer["evidence_manifest"](data, composer["source_articles"](data["metadata"]))
    if mutation == "missing-manifest":
        manifest = None
    elif mutation == "edited-body":
        markdown = markdown.replace("### CVE-2026-12345", "### Altered CVE-2026-12345")
    elif mutation == "outside-finding":
        markdown = markdown.replace("# GRC", "# CVE-2026-12345 GRC", 1)
    else:
        if mutation == "duplicate-url":
            other = deepcopy(manifest["sources"][0])
            other["cves"] = ["CVE-2026-99999"]
            manifest["sources"].append(other)
        manifest["report_plan"]["control_implications"][0][
            "headline"
        ] = "CVE-2026-99999 requires Java support for exploitation"
        markdown = markdown.split("## Executive Summary", 1)[0] + render_report_plan(
            manifest["report_plan"], manifest["sources"], include_digest=True
        )
    assert (
        checker["find_reader_surface_defect"](markdown, manifest=manifest)
        == "CVE claim without an inline source link"
    )


@pytest.mark.parametrize("elsewhere", [False, "other-url", "same-url"])
def test_unsupported_finding_cve_is_rejected_even_if_another_source_has_it(elsewhere):
    composer, _, _ = publication_tools()
    data, source = candidate("CVE-2026-99999")
    if elsewhere:
        other = deepcopy(source)
        other.update(
            title="Other advisory", url="https://example.com/other", cves=["CVE-2026-99999"]
        )
        if elsewhere == "same-url":
            other["url"] = source["url"]
        data["metadata"]["source_articles"].append(other)
        data["content"] = render_report_plan(data["metadata"]["report_plan"], [source, other])
    with pytest.raises(SystemExit, match="CVE-2026-99999"):
        composer["compose_report"](
            data, "https://digest.example/feed.xml", "openrouter/example/model"
        )


def test_edited_finding_cannot_borrow_context_from_retained_plan():
    composer, _, _ = publication_tools()
    data, _ = candidate()
    data["content"] = data["content"].replace("### CVE-2026-12345", "### Altered CVE-2026-12345")
    with pytest.raises(SystemExit):
        composer["compose_report"](
            data, "https://digest.example/feed.xml", "openrouter/example/model"
        )


@pytest.mark.parametrize("duplicate_url", [False, True])
def test_publication_check_independently_rejects_an_unsupported_finding_cve(duplicate_url):
    composer, checker, builder = publication_tools()
    data, _ = candidate()
    markdown = composer["compose_report"](
        data, "https://digest.example/feed.xml", "openrouter/example/model"
    )
    manifest = composer["evidence_manifest"](data, composer["source_articles"](data["metadata"]))
    if duplicate_url:
        other = deepcopy(manifest["sources"][0])
        other.update(title="Other advisory", cves=["CVE-2026-99999"])
        manifest["sources"].append(other)
    manifest["report_plan"]["control_implications"][0][
        "headline"
    ] = "CVE-2026-99999 requires Java support for exploitation"
    prefix = markdown.split("## Executive Summary", 1)[0]
    markdown = prefix + render_report_plan(
        manifest["report_plan"], manifest["sources"], include_digest=True
    )
    with pytest.raises(SystemExit, match="CVE-2026-99999"):
        checker["validate_evidence_manifest"](
            markdown,
            builder["report_fields"](markdown),
            json.dumps(manifest),
            require_current_contract=True,
        )
