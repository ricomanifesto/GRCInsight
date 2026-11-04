"""Manual deployment refuses unsupported auth before running any cloud command."""

from pathlib import Path
import shlex
import sqlite3
import subprocess
import sys

import pytest

from scripts import update_lambda_environment as deploy

ROOT = Path(__file__).resolve().parents[2]
KEY = "synthetic-openrouter-not-real"


def shell_environment(tmp_path, *, fail_auth=False):
    binary = tmp_path / "bin"
    binary.mkdir()
    (binary / "python3").symlink_to(sys.executable)
    calls = tmp_path / "calls"
    aws = binary / "aws"
    aws.write_text(
        '#!/bin/sh\nprintf "aws %s\\n" "$*" >> '
        + shlex.quote(str(calls))
        + "\n"
        + 'printf "%s\\n" "$AWS_CLI_HISTORY_FILE" >> '
        + shlex.quote(str(calls.with_suffix(".history")))
        + "\n"
        + ("exit 1\n" if fail_auth else "")
        + 'case "$1 $2" in "sts get-caller-identity") printf \'{"Account":"123456789012"}\\n\';; esac\n'
    )
    aws.chmod(0o755)
    docker = binary / "docker"
    docker.write_text('#!/bin/sh\nprintf "docker\\n" >> "$CALLS"\n')
    docker.chmod(0o755)
    return calls, {
        "PATH": str(binary),
        "CALLS": str(calls),
        "HOME": str(tmp_path),
        "AWS_REGION": "us-east-1",
        "AWS_EC2_METADATA_DISABLED": "true",
        "AWS_CONFIG_FILE": str(tmp_path / "config"),
        "AWS_SHARED_CREDENTIALS_FILE": str(tmp_path / "credentials"),
        "OPENROUTER_API_KEY": KEY,
        "LLM_MODEL": "openrouter/vendor/model:free",
    }


@pytest.mark.parametrize("case", ["partial_pair", "wrong_region", "unsupported_role_env"])
def test_manual_preflight_refuses_before_any_aws_or_docker_command(tmp_path, case):
    calls, environment = shell_environment(tmp_path)
    (tmp_path / "credentials").write_text(
        "[default]\naws_access_key_id=synthetic\naws_secret_access_key=synthetic\n"
    )
    if case == "partial_pair":
        environment["AWS_ACCESS_KEY_ID"] = "synthetic"
    elif case == "wrong_region":
        environment.update(
            AWS_ACCESS_KEY_ID="synthetic", AWS_SECRET_ACCESS_KEY="synthetic", AWS_REGION="eu-west-1"
        )
    else:
        environment["AWS_ROLE_ARN"] = "unsupported-environment-role"
    result = subprocess.run(
        ["/bin/bash", "scripts/deploy-lambda.sh"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode != 0
    assert not calls.exists(), calls.read_text() if calls.exists() else ""
    assert "preflight" in (result.stdout + result.stderr).lower()
    assert KEY not in result.stdout + result.stderr


def test_manual_preflight_delegates_existing_configured_auth_without_reading_keys(
    monkeypatch, capsys
):
    monkeypatch.setattr(
        sys,
        "argv",
        ["environment", "--function-kind", "python", "--preflight-only", "--manual-cli-auth"],
    )
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    for name, value in {
        "OPENROUTER_API_KEY": KEY,
        "LLM_MODEL": "openrouter/vendor/model:free",
        "HOME": "/synthetic/home",
        "AWS_PROFILE": "selected",
        "AWS_CONFIG_FILE": "/synthetic/config",
        "AWS_SHARED_CREDENTIALS_FILE": "/synthetic/credentials",
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(deploy.shutil, "which", lambda _name: "/fixed/aws")

    calls = []

    def invoke(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, b'{"Account":"123456789012"}')

    monkeypatch.setattr(deploy.subprocess, "run", invoke)
    assert deploy.main() == 0
    output = capsys.readouterr()
    assert output.out.strip() == "123456789012" and len(calls) == 1
    argv, kwargs = calls[0]
    assert argv[1:3] == ["sts", "get-caller-identity"]
    assert argv[argv.index("--endpoint-url") + 1] == "https://sts.us-east-1.amazonaws.com"
    assert kwargs["env"]["AWS_PROFILE"] == "selected"
    assert kwargs["env"]["AWS_CONFIG_FILE"] == "/synthetic/config"
    assert "OPENROUTER_API_KEY" not in kwargs["env"] and "AWS_ACCESS_KEY_ID" not in kwargs["env"]
    assert KEY not in output.out + output.err


def test_invalid_effective_auth_stops_before_any_mutation(tmp_path):
    calls, environment = shell_environment(tmp_path, fail_auth=True)
    result = subprocess.run(
        ["/bin/bash", "scripts/deploy-lambda.sh"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode != 0
    assert len(calls.read_text().splitlines()) == 1
    assert calls.read_text().startswith("aws sts get-caller-identity ")
    assert "ecr" not in calls.read_text() and "docker" not in calls.read_text()
    assert KEY not in result.stdout + result.stderr


def test_manual_config_endpoint_overrides_cannot_receive_private_json(monkeypatch):
    calls = []

    def invoke(argv, **kwargs):
        calls.append((argv, kwargs))
        body = b'{"Account":"123456789012"}' if argv[1] == "sts" else b"{}"
        return subprocess.CompletedProcess(argv, 0, body)

    monkeypatch.setattr(deploy.subprocess, "run", invoke)
    client = deploy.AwsCli(
        "/fixed/aws",
        "us-east-1",
        {
            "HOME": "/synthetic/home",
            "AWS_PROFILE": "selected",
            "AWS_DEFAULT_PROFILE": "default",
            "AWS_CONFIG_FILE": "/synthetic/config-with-endpoint-overrides",
            "AWS_SHARED_CREDENTIALS_FILE": "/synthetic/credentials",
            "AWS_ENDPOINT_URL": "https://untrusted.example.test",
            "AWS_ENDPOINT_URL_LAMBDA": "https://untrusted.example.test",
            "HTTPS_PROXY": "untrusted-proxy",
            "AWS_DEBUG": "1",
            "OPENROUTER_API_KEY": KEY,
        },
        manual_cli_auth=True,
    )
    assert client.account_id() == "123456789012"
    client.update({"Environment": {"Variables": {"OPENROUTER_API_KEY": KEY}}})
    argv, kwargs = calls[1]
    assert calls[0][1]["env"] == kwargs["env"]
    assert (
        calls[0][0][calls[0][0].index("--endpoint-url") + 1]
        == "https://sts.us-east-1.amazonaws.com"
    )
    assert argv[argv.index("--endpoint-url") + 1] == "https://lambda.us-east-1.amazonaws.com"
    assert kwargs["env"]["AWS_CONFIG_FILE"] == "/synthetic/config-with-endpoint-overrides"
    assert kwargs["env"]["AWS_CLI_HISTORY_FILE"] == "/dev"
    assert not any(
        name in kwargs["env"]
        for name in (
            "AWS_ENDPOINT_URL",
            "AWS_ENDPOINT_URL_LAMBDA",
            "HTTPS_PROXY",
            "AWS_DEBUG",
            "OPENROUTER_API_KEY",
        )
    )
    assert KEY not in " ".join(argv)


def test_default_ci_mode_does_not_fall_through_to_configured_credentials():
    with pytest.raises(deploy.EnvironmentUpdateError):
        deploy.AwsCli("/fixed/aws", "us-east-1", {"HOME": "/synthetic", "AWS_PROFILE": "selected"})


def test_history_override_cannot_persist_sqlite_records():
    with pytest.raises(sqlite3.OperationalError):
        sqlite3.connect("/dev")


def test_manual_script_protects_history_for_helper_and_direct_aws_children(tmp_path):
    calls, environment = shell_environment(tmp_path)
    environment["AWS_CLI_HISTORY_FILE"] = "/synthetic/operator-history.db"
    # Deliberately stop the fake bootstrap after read-only STS/ECR checks; no
    # real command runs, while both helper and direct CLI inheritance are seen.
    subprocess.run(
        ["/bin/bash", "scripts/deploy-lambda.sh"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=5,
    )
    history_paths = calls.with_suffix(".history").read_text().splitlines()
    assert len(history_paths) >= 2
    assert set(history_paths) == {"/dev"}
