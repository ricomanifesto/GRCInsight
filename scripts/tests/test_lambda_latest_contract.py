"""Native request/response contract for unqualified unpublished Lambda settings."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest

from scripts import update_lambda_environment as deploy

GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures" / "lambda_latest_configurations.json").read_text()
)


class NativeCli:
    """Model AWS's ARN form from the actual native CLI request, not host assumptions."""

    def __init__(self, kind, *, phase=None, changes=None):
        self.golden = GOLDEN[kind]
        self.calls = []
        self.written = False
        self.phase = phase
        self.changes = changes or {}

    def run(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        operation = argv[2]
        assert argv[argv.index("--endpoint-url") + 1] == "https://lambda.us-east-1.amazonaws.com"
        assert argv[argv.index("--function-name") + 1] == self.golden["before"]["FunctionArn"]
        assert "--cli-input-json" not in argv
        if operation == "update-function-configuration":
            assert not self.written
            assert argv[argv.index("--revision-id") + 1] == self.golden["before"]["RevisionId"]
            assert argv[argv.index("--environment") + 1] == "file:///dev/stdin"
            assert json.loads(kwargs["input"]) == self.golden["after"]["Environment"]
            self.written = True
            phase = "ack"
        else:
            assert operation == "get-function-configuration"
            assert kwargs["input"] is None and kwargs["stdin"] == subprocess.DEVNULL
            phase = "after" if self.written else "before"
        response = deepcopy(self.golden[phase])
        if "--qualifier" in argv:
            response["FunctionArn"] += ":" + argv[argv.index("--qualifier") + 1]
        if self.phase == phase:
            response.update(self.changes)
        return subprocess.CompletedProcess(argv, 0, json.dumps(response).encode())


def client(monkeypatch, native):
    monkeypatch.setattr(deploy.subprocess, "run", native.run)
    return deploy.AwsCli(
        "/fixed/aws",
        "us-east-1",
        {"AWS_ACCESS_KEY_ID": "synthetic", "AWS_SECRET_ACCESS_KEY": "synthetic"},
    )


@pytest.mark.parametrize("kind", ["go", "python"])
def test_canonical_unqualified_read_ack_and_poll_share_one_latest_target(monkeypatch, kind):
    native = NativeCli(kind)
    adapter = client(monkeypatch, native)
    before, after = native.golden["before"], native.golden["after"]
    assert deploy.configure(adapter, before["FunctionArn"], {"LOG_LEVEL": "INFO"}) == "verified"
    assert [argv[2] for argv, _kwargs in native.calls] == [
        "get-function-configuration",
        "update-function-configuration",
        "get-function-configuration",
    ]
    assert all("--qualifier" not in argv for argv, _kwargs in native.calls)
    assert before["RevisionId"] != after["RevisionId"]
    assert before["Environment"]["Variables"]["UNRELATED_SETTING"] == (
        after["Environment"]["Variables"]["UNRELATED_SETTING"]
    )


@pytest.mark.parametrize("phase", ["before", "ack", "after"])
@pytest.mark.parametrize(
    "changes",
    [
        {"FunctionArn": GOLDEN["go"]["before"]["FunctionArn"] + ":$LATEST"},
        {"FunctionArn": GOLDEN["go"]["before"]["FunctionArn"] + ":production"},
        {"FunctionArn": GOLDEN["go"]["before"]["FunctionArn"] + ":7"},
        {
            "FunctionArn": GOLDEN["go"]["before"]["FunctionArn"].replace(
                "123456789012", "999999999999"
            )
        },
        {"FunctionArn": GOLDEN["go"]["before"]["FunctionArn"].replace("us-east-1", "us-west-2")},
        {"FunctionArn": GOLDEN["python"]["before"]["FunctionArn"]},
        {"FunctionName": "grcinsight-python-function"},
        {"Version": "7"},
        {"Version": "production"},
        {"RevisionId": None},
    ],
)
def test_noncanonical_snapshot_ack_or_poll_never_relaxes_identity(monkeypatch, phase, changes):
    native = NativeCli("go", phase=phase, changes=changes)
    adapter = client(monkeypatch, native)
    with pytest.raises(deploy.EnvironmentUpdateError):
        deploy.configure(adapter, native.golden["before"]["FunctionArn"], {"LOG_LEVEL": "INFO"})
    writes = [argv for argv, _kwargs in native.calls if argv[2] == "update-function-configuration"]
    assert len(writes) == (0 if phase == "before" else 1)


@pytest.mark.parametrize("suffix", [":$LATEST", ":7", ":production"])
def test_qualified_requested_targets_refuse_before_native_cli(monkeypatch, suffix):
    native = NativeCli("go")
    adapter = client(monkeypatch, native)
    with pytest.raises(deploy.EnvironmentUpdateError):
        deploy.configure(
            adapter, native.golden["before"]["FunctionArn"] + suffix, {"LOG_LEVEL": "INFO"}
        )
    assert not native.calls
