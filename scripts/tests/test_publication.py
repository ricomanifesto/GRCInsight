"""Production publication: public-site configuration, site URL boundary, the
generation admission path, the publisher workflow and the Lambda trigger."""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
SITE_CONFIG = json.loads((ROOT / "publication" / "site.json").read_text())
LEGAL_STATES = (
    {"mode": "disabled", "proof": "off"},
    {"mode": "prepare", "proof": "off"},
    {"mode": "prepare", "proof": "on"},
    {"mode": "active", "proof": "on"},
)
PRODUCTION = {
    "SentryDigest": "https://sentrydigest.ricomanifesto.com/",
    "SentryInsight": "https://sentryinsight.ricomanifesto.com/",
    "GRCInsight": "https://grcinsight.ricomanifesto.com/",
}


def _legacy(site: str) -> str:
    return f"https://ricomanifesto.github.io/{site}/"


def _emitted(site: str) -> str:
    origins = SITE_CONFIG["origins"][site]
    return origins[origins["emitted"]]


def _workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text()


def _paths_filter(workflow: str) -> list[str]:
    block = re.search(r"push:\n\s+branches: \[ main \]\n\s+paths:\n((?:\s+- '[^']+'\n)+)", workflow)
    assert block, "deploy-lambda push trigger has no paths filter"
    return re.findall(r"- '([^']+)'", block.group(1))


def _matches(pattern: str, path: str) -> bool:
    regex = re.escape(pattern).replace(r"\*\*", ".*").replace(r"\*", "[^/]*")
    return re.fullmatch(regex, path) is not None


def test_publication_configuration_is_a_legal_activation_state():
    # Any legal state passes the ordinary gates; the shipped initial state is
    # verified separately as a candidate fact.
    config = SITE_CONFIG
    assert config["site"] == "GRCInsight"
    assert config["publication"] in LEGAL_STATES
    for site, production in PRODUCTION.items():
        assert config["origins"][site]["legacy"] == _legacy(site)
        assert config["origins"][site]["production"] == production
        assert config["origins"][site]["emitted"] in ("legacy", "production")
    assert config["payload_builder"] == ["python3", "-B", "scripts/build_static_artifact.py"]
    assert "consumers" not in config


def test_site_urls_come_from_the_emitted_origin():
    import build_site
    import check_site_report
    from public_site import accepted_origins, emitted_origin

    assert emitted_origin("GRCInsight") == _emitted("GRCInsight")
    assert build_site.PUBLIC_SITE_URL == _emitted("GRCInsight")
    assert check_site_report.PUBLIC_SITE_URL == _emitted("GRCInsight")
    assert accepted_origins("SentryDigest") == (
        "https://ricomanifesto.github.io/SentryDigest/",
        "https://sentrydigest.ricomanifesto.com/",
    )


def test_evidence_feed_home_accepts_both_configured_digest_origins():
    import check_site_report
    from public_site import accepted_origins

    # Evidence feed homes keep the existing public-URL validation, which
    # already accepts either configured SentryDigest origin.
    for url in accepted_origins("SentryDigest"):
        assert check_site_report.canonical_public_url(url, "feed home") == url
    assert not hasattr(check_site_report, "check_feed_home_url")


@pytest.mark.parametrize("publication", LEGAL_STATES)
@pytest.mark.parametrize("emitted", ["legacy", "production"])
def test_every_legal_state_and_emission_keeps_report_history_valid(tmp_path, publication, emitted):
    config = json.loads(json.dumps(SITE_CONFIG))
    config["publication"] = publication
    for origins in config["origins"].values():
        origins["emitted"] = emitted
    config_path = tmp_path / "site.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n")
    script = f"""
import json, sys
from pathlib import Path
sys.path.insert(0, "scripts")
import public_site
public_site.SITE_CONFIG_PATH = Path({str(config_path)!r})
import build_site
import check_site_report
check_site_report.validate_archive_history(Path("site/archive"), Path("site/archive/index.html").read_text())
feed_homes = [check_site_report.canonical_public_url(url, "feed home") for url in public_site.accepted_origins("SentryDigest")]
print(json.dumps({{"build": build_site.PUBLIC_SITE_URL, "check": check_site_report.PUBLIC_SITE_URL, "feed_homes": feed_homes}}))
"""
    result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    observed = json.loads(result.stdout)
    expected = PRODUCTION["GRCInsight"] if emitted == "production" else _legacy("GRCInsight")
    assert observed["build"] == observed["check"] == expected
    # Archived reports keep the origins they were written with and still
    # validate; evidence feed homes from either Digest origin stay accepted.
    assert observed["feed_homes"] == [_legacy("SentryDigest"), PRODUCTION["SentryDigest"]]


def test_builder_gate_snapshot_includes_the_public_site_configuration():
    import build_static_artifact

    assert "publication/" in build_static_artifact.GATE_SOURCE_PREFIXES


@pytest.mark.skipif(shutil.which("node") is None, reason="node is required")
def test_shared_publication_kit():
    tests = sorted(str(path) for path in (ROOT / "publication" / "test").glob("*.test.js"))
    result = subprocess.run(
        ["node", "--test", "--test-concurrency=1", *tests], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-2000:]


def test_only_sentrydigest_releases_can_start_event_driven_generation():
    workflow = _workflow("lambda-report-generation.yml")
    assert re.search(r"on:\n  repository_dispatch:\n    types: \[sentrydigest-updated\]\n", workflow)
    assert "readmit:" in workflow
    admit = workflow.index("- name: Admit generation")
    assert admit < workflow.index("- name: Configure AWS credentials")
    assert admit < workflow.index("- name: Invoke Lambda report generation")
    assert re.search(
        r"- name: Configure AWS credentials\n\s+if: steps\.admission\.outputs\.decision == 'admitted'"
        r" \|\| steps\.admission\.outputs\.decision == 'reattach'",
        workflow,
    )


def test_admitted_events_send_the_snapshot_and_record_the_paid_call():
    workflow = _workflow("lambda-report-generation.yml")
    assert "ADMITTED_FEED_URL: ${{ steps.admission.outputs.feed_url }}" in workflow
    assert re.search(r'if \[ -n "\$ADMITTED_FEED_URL" \]; then\n\s+FEED_URL="\$ADMITTED_FEED_URL"', workflow)
    start = workflow.index("- name: Record generation start")
    invoke = workflow.index("- name: Invoke Lambda report generation")
    handle = workflow.index("- name: Record report handle")
    retrieve = workflow.index("- name: Retrieve generated report")
    assert start < invoke < handle < retrieve
    assert re.search(
        r"- name: Invoke Lambda report generation\n\s+id: lambda-invoke\n\s+if: steps\.admission\.outputs\.decision == 'admitted'",
        workflow,
    )
    assert '--handle "$REPORT_ID"' in workflow
    assert "REPORT_ID: ${{ steps.lambda-invoke.outputs.REPORT_ID || steps.admission.outputs.reattach_handle }}" in workflow
    assert "node publication/cli.js complete" in workflow


def test_retained_and_published_commits_reach_the_publisher():
    workflow = _workflow("lambda-report-generation.yml")
    assert re.search(r"outputs:\n\s+head_sha: \$\{\{ steps\.head\.outputs\.head_sha \}\}", workflow)
    # The pushed remote head, not the run-start commit or an unpushed local one.
    assert 'git fetch --quiet origin "$GITHUB_REF_NAME"\n        echo "head_sha=$(git rev-parse FETCH_HEAD)" >> "$GITHUB_OUTPUT"' in workflow
    assert re.search(
        r"  publish:\n    needs: generate-report\n    if: always\(\)\n    permissions:\n      contents: write\n"
        r"    uses: \./\.github/workflows/publish-production\.yml\n    with:\n      invocation: publish\n"
        r"      source_sha: \$\{\{ needs\.generate-report\.outputs\.head_sha \|\| github\.sha \}\}",
        workflow,
    )
    assert "deploy-site.yml" not in workflow
    assert "Dispatch Pages deployment" not in workflow
    assert "cancel-in-progress: true" in workflow


def test_publisher_workflow_is_explicit_and_serialized():
    workflow = _workflow("publish-production.yml")
    assert re.search(r"^on:\n  workflow_call:", workflow, re.M)
    assert "  workflow_dispatch:" in workflow
    assert not re.search(r"^  (push|schedule|repository_dispatch):", workflow, re.M)
    assert re.search(r"^permissions:\n  contents: write\n", workflow, re.M)
    assert "group: publish-production\n  cancel-in-progress: false" in workflow
    assert re.search(r"- name: Run repository gate\n\s+if: inputs\.invocation == 'publish'\n\s+run: make check-site", workflow)
    assert "secrets." not in workflow and "actions: write" not in workflow


def test_lambda_deploys_only_for_backend_inputs():
    workflow = _workflow("deploy-lambda.yml")
    patterns = _paths_filter(workflow)
    assert "workflow_dispatch:" in workflow

    def triggers(path: str) -> bool:
        return any(_matches(pattern, path) for pattern in patterns)

    for path in ["cmd/lambda/main.go", "internal/api/handlers/static.go", "go.mod", "go.sum", "Dockerfile.lambda",
                 "agent/core/report_plan.py", "agent/Dockerfile.lambda", "agent/uv.lock", "configs/config.yaml"]:
        assert triggers(path), path
    migration = [
        ".github/workflows/deploy-lambda.yml", ".github/workflows/lambda-report-generation.yml",
        ".github/workflows/publish-production.yml", "Makefile", "README.md", "publication/site.json",
        "publication/cli.js", "publication/kit/publisher.js", "publication/adapter/build.js",
        "scripts/build_site.py", "scripts/check_site_report.py", "scripts/public_site.py",
        "scripts/build_static_artifact.py", "scripts/serve_static_artifact.py", "scripts/tests/test_publication.py",
        "site/index.html", "site/archive/index.html", "docs/DEVELOPER.md",
    ]
    for path in migration:
        assert not triggers(path), path
    candidate = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    changed = [line[3:] for line in candidate]
    assert not [path for path in changed if triggers(path)]


def test_reader_links_use_emitted_origins_without_rewriting_evidence():
    import build_site
    from public_site import emitted_origin

    markdown = '## Sources\n' + '\n'.join(
        f'[Source {site}](https://ricomanifesto.github.io/{site}/archive/2026-11-06/?view=full#item-1)'
        for site in PRODUCTION
    )
    original = markdown
    html = build_site.render_report(markdown)
    for site in PRODUCTION:
        assert f'href="{emitted_origin(site)}archive/2026-11-06/?view=full#item-1"' in html
    assert markdown == original


def test_reader_links_do_not_rewrite_unrelated_hosts_or_prefixes():
    import build_site

    urls = [
        'https://ricomanifesto.github.io/SentryDigest-other/archive/',
        'https://example.com/SentryDigest/#source',
        'https://ricomanifesto.github.io.evil.example/SentryDigest/',
    ]
    html = build_site.render_report('## Sources\n' + '\n'.join(f'[Source]({url})' for url in urls))
    for url in urls:
        assert f'href="{url}"' in html
