"""Execute the real workflow retrieval shell against offline boundary fakes."""

import json
import os
from pathlib import Path
import subprocess
import textwrap

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/lambda-report-generation.yml"


def step(name):
    block = WORKFLOW.read_text().split(f"    - name: {name}\n", 1)[1].split("\n    - name:", 1)[0]
    return block, textwrap.dedent(block.split("      run: |\n", 1)[1])


@pytest.mark.parametrize(
    "status,mode,identity,http_status,transport,terminal",
    [
        ("completed", "model", "report-test", 200, 0, True),
        ("failed", "model", "report-test", 200, 0, True),
        ("completed", "unknown", "report-test", 200, 0, True),
        ("processing", "model", "report-test", 200, 0, False),
        ("completed", "model", "other-report", 200, 0, False),
        ("completed", "model", "report-test", 503, 0, False),
        ("completed", "model", "report-test", 200, 1, False),
        ("completed", "model", None, 200, 0, False),
        ("malformed", "model", "report-test", 200, 0, False),
        ("function-error", "model", "report-test", 200, 0, False),
    ],
)
def test_terminal_observation_survives_composition_failure(
    tmp_path, status, mode, identity, http_status, transport, terminal
):
    _, shell = step("Retrieve generated report")
    shell = shell.replace("${{ steps.handle.outputs.REPORT_ID }}", "report-test")
    data = {
        "id": identity,
        "status": status,
        "content": "unsupported report",
        "metadata": {
            "analysis_mode": mode,
            "requested_model": "test/model",
            "resolved_model": "test/model",
            "source_home_url": "https://digest.example/",
            "source_issue_date": "2026-11-06",
            "source_issue_url": "https://digest.example/archive/2026-11-06/",
        },
    }
    response = {"statusCode": http_status, "body": json.dumps(data)}
    if status == "malformed":
        response["body"] = "{invalid"
    if status == "function-error":
        data["status"] = "completed"
        response.update(FunctionError="Unhandled", body=json.dumps(data))
    (tmp_path / "response.json").write_text(json.dumps(response))
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for name, code in {
        "aws": f"#!/bin/sh\ncp response.json report-response.json\nexit {transport}\n",
        "python3": '#!/bin/sh\necho "composition refused" >&2\nexit 1\n',
    }.items():
        executable = fake_bin / name
        executable.write_text(code)
        executable.chmod(0o755)
    output = tmp_path / "output"
    output.touch()
    result = subprocess.run(
        ["bash", "-e", "-o", "pipefail", "-c", shell],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "GITHUB_OUTPUT": str(output),
            "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
            "MAX_ATTEMPTS": "1",
            "SLEEP_SECONDS": "0",
            "GO_FUNCTION_NAME": "fake",
            "AWS_REGION": "fake",
            "LLM_MODEL": "test/model",
            "FEED_URL": "https://digest.example/feed.xml",
        },
    )
    assert result.returncode != 0
    assert ("terminal=true" in output.read_text()) is terminal
    assert "publishable=true" not in output.read_text()


def test_completion_runs_for_terminal_observation_despite_step_failure():
    block, shell = step("Record generation outcome")
    assert "always()" in block
    assert "steps.get-report.outputs.terminal == 'true'" in block
    assert "OUTCOME=not-published" in shell


@pytest.mark.parametrize(
    "published,retained,expected",
    [
        ("", "", "not-published"),
        ("true", "", "published"),
        ("", "true", "retained"),
    ],
)
def test_completion_records_publication_outcome_separately(tmp_path, published, retained, expected):
    _, shell = step("Record generation outcome")
    node = tmp_path / "node"
    node.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > completion-args\n')
    node.chmod(0o755)
    subprocess.run(
        ["bash", "-e", "-c", shell],
        cwd=tmp_path,
        check=True,
        env={
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "PUBLISHED": published,
            "RETAINED": retained,
            "ADMISSION_KEY": "original-key",
            "BINDING": "feed-bytes",
            "GITHUB_RUN_ID": "retry-run",
        },
    )
    args = (tmp_path / "completion-args").read_text().splitlines()
    assert args == [
        "publication/cli.js",
        "complete",
        "--key",
        "original-key",
        "--run-id",
        "retry-run",
        "--outcome",
        expected,
        "--binding",
        "feed-bytes",
    ]
