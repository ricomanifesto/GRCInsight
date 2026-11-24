"""The local smoke wrapper sends synthetic credentials only to configured peers."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/integration/run_e2e.sh"


def run_wrapper(tmp_path, key="synthetic-api-key"):
    if not shutil.which("jq"):
        pytest.skip("jq is required by the smoke wrapper")
    binary = tmp_path / "bin"
    binary.mkdir()
    curl = binary / "curl"
    curl.write_text(
        "#!/usr/bin/env python3\n"
        "import json,os,sys\n"
        "args=sys.argv[1:]\n"
        "config=sys.stdin.read() if '--config' in args else ''\n"
        "with open(os.environ['CALL_LOG'],'a') as f: f.write(json.dumps({'args':args,'config':config})+'\\n')\n"
        "url=next((arg for arg in args if arg.startswith('http')), '')\n"
        "if 'generate' in url: print(json.dumps({'report_id':'fixture/report','status':'completed'}))\n"
        "elif 'articles' in url: print(json.dumps({'articles':[]}))\n"
        "else: print(json.dumps({'status':'completed'}))\n"
    )
    curl.chmod(0o700)
    log = tmp_path / "calls.jsonl"
    env = {
        **os.environ,
        "PATH": str(binary) + os.pathsep + os.environ["PATH"],
        "CALL_LOG": str(log),
        "API_URL": "https://api.example.test",
        "PYTHON_URL": "https://python.example.test",
        "FEED_URL": 'https://feed.example.test/rss?title="quoted"&second=1',
        "API_KEY": key,
    }
    result = subprocess.run(["bash", str(SCRIPT)], env=env, text=True, capture_output=True, check=False)
    calls = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    return result, calls, env


def test_e2e_wrapper_requires_key_before_requests(tmp_path):
    result, calls, _ = run_wrapper(tmp_path, key="")
    assert result.returncode != 0
    assert calls == []
    assert "API_KEY" in result.stderr


def test_e2e_wrapper_sends_keys_without_redirects_or_arguments_and_serializes_json(tmp_path):
    result, calls, env = run_wrapper(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert len(calls) == 4
    for call in calls:
        assert "synthetic-api-key" not in " ".join(call["args"])
        assert 'X-API-Key: synthetic-api-key' in call["config"]
        assert not any(arg == "--location" or (arg.startswith("-") and not arg.startswith("--") and "L" in arg) for arg in call["args"])
    generated = calls[1]
    payload_arg = next((flag for flag in ("--data", "--data-binary") if flag in generated["args"]), None)
    payload = json.loads(generated["args"][generated["args"].index(payload_arg) + 1])
    assert payload["feed_url"] == env["FEED_URL"]
    assert "model" not in payload["config"]
    assert "fixture%2Freport" in " ".join(calls[2]["args"])
    assert "synthetic-api-key" not in result.stdout + result.stderr


def test_e2e_generated_header_config_is_accepted_by_real_curl_without_a_request(tmp_path):
    curl = shutil.which("curl")
    if not curl:
        pytest.skip("curl is required for its local configuration parser")
    result, calls, _ = run_wrapper(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    # --version exercises curl's real config parser without contacting a peer.
    parsed = subprocess.run(
        [curl, "-q", "--config", "-", "--version"],
        input=calls[0]["config"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert parsed.returncode == 0, parsed.stderr
    assert "synthetic-api-key" not in parsed.stdout + parsed.stderr
