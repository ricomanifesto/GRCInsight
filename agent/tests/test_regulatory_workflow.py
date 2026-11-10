"""The daily Federal Register read runs apart from report generation and publication."""

from __future__ import annotations

from pathlib import Path
import re

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "regulatory-register.yml"
REPORT_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "lambda-report-generation.yml"


def source() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_it_runs_daily_at_twelve_twenty_and_by_hand():
    text = source()
    assert "cron: '20 12 * * *'" in text
    assert re.search(r"^  workflow_dispatch:\s*$", text, re.M)
    assert "repository_dispatch" not in text and "pull_request" not in text


def test_it_has_only_contents_write_and_its_own_concurrency_group():
    text = source()
    permissions = re.search(r"^permissions:\n((?:  .+\n)+)", text, re.M)
    assert permissions and permissions.group(1).strip() == "contents: write"
    group = re.search(r"^  group: (.+)$", text, re.M)
    assert group and group.group(1).strip() == "grcinsight-regulatory-register"
    report_group = re.search(r"^  group: (.+)$", REPORT_WORKFLOW.read_text(), re.M)
    assert report_group and report_group.group(1) != group.group(1)
    assert "cancel-in-progress: false" in text


def test_it_uses_no_secret_cloud_account_or_publication_call():
    text = source()
    for forbidden in (
        "secrets.",
        "aws",
        "AWS",
        "publish-production",
        "workflow_call",
        "gh workflow",
        "uses: ./",
        "id-token",
    ):
        assert forbidden not in text, forbidden


def test_it_bounds_the_job_and_the_read():
    text = source()
    assert re.search(r"^    timeout-minutes: 5$", text, re.M)
    read = text.split("- name: Read the Federal Register")[1].split("- name:")[0]
    assert "timeout-minutes: 2" in read
    assert "python3 scripts/regulatory_register.py refresh" in read


def test_it_commits_only_the_register_and_the_current_page_after_the_site_gate():
    text = source()
    publish = text.split("- name: Rebuild, check and commit")[1]
    assert 'ALLOWED="site/index.html site/regulatory-register.json"' in publish
    assert publish.index("python3 scripts/build_site.py") < publish.index("make check-site")
    assert publish.index("make check-site") < publish.index("git commit")
    assert "git add site/index.html site/regulatory-register.json" in publish
    assert "git add -A" not in publish and "git add ." not in publish
    assert "Unexpected changed path" in publish
    assert publish.index("Unexpected changed path") < publish.index("git commit")


def test_a_refused_push_resets_restores_and_retries_three_times_then_stops_quietly():
    publish = source().split("- name: Rebuild, check and commit")[1]
    assert "max_attempts=3" in publish
    assert "git reset --hard origin/main" in publish
    assert 'cp "$RUNNER_TEMP/regulatory-register.json" site/regulatory-register.json' in publish
    loop = publish.split("max_attempts=3", 1)[1]
    assert 'echo "Push refused $max_attempts times; stopping' in loop
    assert loop.index("Push refused") < loop.index("exit 0")
    assert "--force" not in publish


def test_it_stops_when_the_read_left_the_file_unchanged():
    publish = source().split("- name: Rebuild, check and commit")[1]
    assert "git status --porcelain -- site/regulatory-register.json" in publish
    unchanged = publish.index("Register unchanged")
    assert unchanged < publish.index("python3 scripts/build_site.py")
