"""Deployment environment updates preserve unrelated state without secret argv."""

from copy import deepcopy
import json
import subprocess

import pytest

from scripts import update_lambda_environment as deploy

ACCOUNT = "123456789012"
ARN = f"arn:aws:lambda:us-east-1:{ACCOUNT}:function:grcinsight-python-function"
KEY = "synthetic-key-never-real"
REVISION = "12345678-1234-1234-1234-123456789abc"
NEW_REVISION = "22345678-1234-1234-1234-123456789abc"
OWNED = {"OPENROUTER_API_KEY": KEY, "LLM_MODEL": "openrouter/example/free:free"}


def snapshot():
    return {
        "FunctionArn": ARN,
        "FunctionName": "grcinsight-python-function",
        "Version": "$LATEST",
        "RevisionId": REVISION,
        "State": "Active",
        "LastUpdateStatus": "Successful",
        "Timeout": 900,
        "Role": "unchanged-role",
        "Environment": {"Variables": {"UNRELATED": "private-other", "OPENROUTER_API_KEY": "old"}},
    }


class Client:
    def __init__(self, failure=None):
        self.value = snapshot()
        self.calls = []
        self.failure = failure

    def get(self, arn, **_kwargs):
        self.calls.append(("get", arn))
        return deepcopy(self.value)

    def update(self, payload):
        self.calls.append(("update", deepcopy(payload)))
        if self.failure == "unknown":
            raise RuntimeError("private response " + KEY)
        self.value.update(RevisionId=NEW_REVISION, Environment=payload["Environment"])
        if self.failure == "unrelated":
            self.value["Timeout"] = 1
        if self.failure == "pending":
            self.value["LastUpdateStatus"] = "InProgress"
        return {
            name: self.value[name]
            for name in ("FunctionArn", "FunctionName", "Version", "RevisionId")
        }


def execute(client):
    return deploy.configure(client, ARN, OWNED, pause=lambda _seconds: None)


def test_merges_only_owned_fields_and_uses_one_revision_cas():
    client = Client()
    assert execute(client) == "verified"
    writes = [value for operation, value in client.calls if operation == "update"]
    assert writes == [
        {
            "FunctionName": ARN,
            "RevisionId": REVISION,
            "Environment": {"Variables": {"UNRELATED": "private-other", **OWNED}},
        }
    ]
    assert len([name for name, _value in client.calls if name == "get"]) == 2


@pytest.mark.parametrize("failure", ["unknown", "unrelated", "pending"])
def test_uncertain_mutation_and_failed_verification_never_replay(failure):
    client = Client(failure)
    with pytest.raises(deploy.EnvironmentUpdateError) as error:
        execute(client)
    assert len([name for name, _value in client.calls if name == "update"]) == 1
    assert KEY not in str(error.value) and "private" not in str(error.value)
    assert len([name for name, _value in client.calls if name == "get"]) <= 4


@pytest.mark.parametrize("change", ["identity", "revision", "env_error", "env_type", "updating"])
def test_bad_snapshot_refuses_before_mutation(change):
    client = Client()
    if change == "identity":
        client.value["FunctionArn"] = ARN + ":alias"
    elif change == "revision":
        client.value["RevisionId"] = "not-a-revision"
    elif change == "env_error":
        client.value["Environment"]["Error"] = {"Message": KEY}
    elif change == "env_type":
        client.value["Environment"]["Variables"] = None
    else:
        client.value["LastUpdateStatus"] = "InProgress"
    with pytest.raises(deploy.EnvironmentUpdateError):
        execute(client)
    assert not any(name == "update" for name, _value in client.calls)


def test_already_applied_environment_is_verified_without_second_mutation():
    client = Client()
    client.value["Environment"]["Variables"].update(OWNED)
    assert execute(client) == "unchanged"
    assert not any(name == "update" for name, _value in client.calls)


def test_aws_cli_uses_private_stdin_and_one_attempt_without_key_environment(monkeypatch):
    calls = []

    def invoke(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0, b"{}")

    monkeypatch.setattr(deploy.subprocess, "run", invoke)
    client = deploy.AwsCli(
        "/fixed/aws",
        "us-east-1",
        {
            "AWS_ACCESS_KEY_ID": "synthetic-access",
            "AWS_SECRET_ACCESS_KEY": "synthetic-secret",
            "OPENROUTER_API_KEY": KEY,
            "HTTPS_PROXY": "private-proxy",
            "AWS_PROFILE": "other",
        },
    )
    client.update(
        {"FunctionName": ARN, "RevisionId": REVISION, "Environment": {"Variables": OWNED}}
    )
    argv, kwargs = calls[0]
    assert KEY not in " ".join(argv)
    assert argv[1:3] == ["lambda", "update-function-configuration"]
    assert "--cli-input-json" not in argv
    assert argv[argv.index("--environment") + 1] == "file:///dev/stdin"
    assert argv[argv.index("--function-name") + 1] == ARN
    assert argv[argv.index("--revision-id") + 1] == REVISION
    assert json.loads(kwargs["input"])["Variables"] == OWNED
    assert kwargs["env"]["AWS_MAX_ATTEMPTS"] == "1"
    assert kwargs["env"]["AWS_CONFIG_FILE"] == "/dev/null"
    assert "OPENROUTER_API_KEY" not in kwargs["env"]
    assert "HTTPS_PROXY" not in kwargs["env"] and "AWS_PROFILE" not in kwargs["env"]
    assert kwargs["stderr"] == subprocess.DEVNULL and kwargs["timeout"] <= 10


def test_cli_failure_discards_raw_diagnostics_and_does_not_retry(monkeypatch):
    calls = []

    def invoke(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 1, KEY.encode())

    monkeypatch.setattr(deploy.subprocess, "run", invoke)
    client = deploy.AwsCli(
        "/fixed/aws",
        "us-east-1",
        {
            "AWS_ACCESS_KEY_ID": "synthetic",
            "AWS_SECRET_ACCESS_KEY": "synthetic",
        },
    )
    with pytest.raises(deploy.EnvironmentUpdateError) as error:
        client.update(
            {"FunctionName": ARN, "RevisionId": REVISION, "Environment": {"Variables": OWNED}}
        )
    assert len(calls) == 1 and KEY not in str(error.value)


@pytest.mark.parametrize(
    "overrides",
    [
        {},
        {
            "GRC_RELEVANCE_MODE": "enabled",
            "GRC_RELEVANCE_MIN_PROBABILITY": "0.8",
            "GRC_RELEVANCE_TIMEOUT_SECONDS": "3",
        },
    ],
)
def test_relevance_defaults_and_overrides_reach_merged_environment(overrides):
    environment = {"LLM_MODEL": "openrouter/test/model", "OPENROUTER_API_KEY": KEY, **overrides}
    owned = deploy.owned_environment("python", environment)
    client = Client()
    assert deploy.configure(client, ARN, owned, pause=lambda _seconds: None) == "verified"
    merged = client.value["Environment"]["Variables"]
    for name, default in (
        ("GRC_RELEVANCE_MODE", "off"),
        ("GRC_RELEVANCE_MIN_PROBABILITY", "0.95"),
        ("GRC_RELEVANCE_TIMEOUT_SECONDS", "4"),
    ):
        assert merged[name] == overrides.get(name, default)
    assert merged["UNRELATED"] == "private-other" and merged["OPENROUTER_API_KEY"] == KEY
