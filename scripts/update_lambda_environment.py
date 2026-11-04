#!/usr/bin/env python3
"""Merge deployment-owned Lambda environment fields with one revision-checked write."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
import math
import os
import re
import shutil
import subprocess
import time
import uuid

FUNCTIONS = {"go": "grcinsight-go-function", "python": "grcinsight-python-function"}
VOLATILE = {
    "Environment",
    "RevisionId",
    "LastModified",
    "LastUpdateStatus",
    "LastUpdateStatusReason",
    "LastUpdateStatusReasonCode",
    "State",
    "StateReason",
    "StateReasonCode",
    "ResponseMetadata",
    "ConfigSha256",
}


class EnvironmentUpdateError(Exception):
    def __init__(self):
        super().__init__(
            "Lambda environment update unavailable or uncertain; inspect before rerunning"
        )


def identity(value, arn):
    if (
        type(value) is not dict
        or value.get("FunctionArn") != arn
        or value.get("FunctionName") != arn.rsplit(":", 1)[-1]
        or value.get("Version") != "$LATEST"
        or type(value.get("RevisionId")) is not str
    ):
        raise EnvironmentUpdateError()
    try:
        if str(uuid.UUID(value["RevisionId"])) != value["RevisionId"]:
            raise ValueError()
    except ValueError:
        raise EnvironmentUpdateError() from None


def variables(value):
    # AWS omits Environment for a newly created function with no variables.
    environment = value.get("Environment", {"Variables": {}})
    if type(environment) is not dict or "Error" in environment:
        raise EnvironmentUpdateError()
    result = environment.get("Variables")
    if type(result) is not dict or any(
        type(k) is not str or type(v) is not str for k, v in result.items()
    ):
        raise EnvironmentUpdateError()
    return result


def configure(client, arn, owned, *, pause=time.sleep, now=time.monotonic):
    if (
        not re.fullmatch(
            r"arn:aws:lambda:us-east-1:\d{12}:function:grcinsight-(go|python)-function", arn
        )
        or type(owned) is not dict
        or not owned
        or any(type(k) is not str or type(v) is not str for k, v in owned.items())
    ):
        raise EnvironmentUpdateError()
    before = client.get(arn)
    identity(before, arn)
    if before.get("State") != "Active" or before.get("LastUpdateStatus") != "Successful":
        raise EnvironmentUpdateError()
    original = variables(before)
    merged = {**original, **owned}
    if merged == original:
        return "unchanged"
    payload = {
        "FunctionName": arn,
        "RevisionId": before["RevisionId"],
        "Environment": {"Variables": merged},
    }
    try:
        ack = client.update(payload)
        identity(ack, arn)
        revision = ack["RevisionId"]
        if revision == before["RevisionId"]:
            raise EnvironmentUpdateError()
    except BaseException:
        # No application retry, rollback, or second mutation after an unknown write.
        raise EnvironmentUpdateError() from None
    end = now() + 30
    for attempt in range(3):
        remaining = end - now()
        if remaining <= 0:
            raise EnvironmentUpdateError()
        after = client.get(arn, timeout=min(10, remaining))
        identity(after, arn)
        if after["RevisionId"] != revision or after.get("LastUpdateStatus") == "Failed":
            raise EnvironmentUpdateError()
        if after.get("LastUpdateStatus") == "InProgress":
            if attempt < 2:
                pause(min(10, max(0, end - now())))
            continue
        if (
            after.get("State") != "Active"
            or after.get("LastUpdateStatus") != "Successful"
            or variables(after) != merged
            or {k: v for k, v in before.items() if k not in VOLATILE}
            != {k: v for k, v in after.items() if k not in VOLATILE}
        ):
            raise EnvironmentUpdateError()
        return "verified"
    raise EnvironmentUpdateError()


class AwsCli:
    """Existing CLI only; secret-bearing JSON travels through a private stdin pipe."""

    def __init__(self, executable, region, environment):
        if (
            region != "us-east-1"
            or not executable
            or not all(
                environment.get(name) for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")
            )
        ):
            raise EnvironmentUpdateError()
        self.executable, self.region = executable, region
        self.environment = {
            "PATH": os.defpath,
            "AWS_ACCESS_KEY_ID": environment["AWS_ACCESS_KEY_ID"],
            "AWS_SECRET_ACCESS_KEY": environment["AWS_SECRET_ACCESS_KEY"],
            "AWS_MAX_ATTEMPTS": "1",
            "AWS_RETRY_MODE": "standard",
            "AWS_CONFIG_FILE": "/dev/null",
            "AWS_SHARED_CREDENTIALS_FILE": "/dev/null",
            "AWS_EC2_METADATA_DISABLED": "true",
            "AWS_PAGER": "",
            "AWS_CLI_AUTO_PROMPT": "off",
        }
        if environment.get("AWS_SESSION_TOKEN"):
            self.environment["AWS_SESSION_TOKEN"] = environment["AWS_SESSION_TOKEN"]

    def _call(self, operation, payload, timeout=10):
        argv = [
            self.executable,
            "lambda",
            operation,
            "--region",
            self.region,
            "--cli-connect-timeout",
            "2",
            "--cli-read-timeout",
            "5",
            "--cli-input-json",
            "file:///dev/stdin",
            "--output",
            "json",
            "--no-cli-pager",
        ]
        if operation == "update-function-configuration":
            argv += [
                "--query",
                "{FunctionArn:FunctionArn,FunctionName:FunctionName,Version:Version,RevisionId:RevisionId}",
            ]
        try:
            result = subprocess.run(
                argv,
                input=json.dumps(payload, allow_nan=False).encode(),
                env=self.environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            )
            if result.returncode != 0 or len(result.stdout) > 262144:
                raise ValueError()
            value = json.loads(result.stdout)
            if type(value) is not dict:
                raise ValueError()
            return value
        except BaseException:
            raise EnvironmentUpdateError() from None

    def get(self, arn, *, timeout=10):
        return self._call(
            "get-function-configuration", {"FunctionName": arn, "Qualifier": "$LATEST"}, timeout
        )

    def update(self, payload):
        return self._call("update-function-configuration", payload)


def owned_environment(kind, env):
    if kind == "go":
        values = {
            "GO_ENV": "production",
            "GIN_MODE": "release",
            "PYTHON_LAMBDA_FUNCTION_NAME": FUNCTIONS["python"],
            "PYTHON_INVOKE_ASYNC": "true",
            "DDB_TABLE_NAME": "grcinsight-reports",
            "ARTICLES_TABLE_NAME": "grcinsight-articles",
            "SERVER_ALLOWED_ORIGINS": "https://ricomanifesto.github.io",
        }
        if env.get("GITHUB_SHA"):
            values["SERVICE_VERSION"] = env["GITHUB_SHA"]
        return values
    model, key = env.get("LLM_MODEL", ""), env.get("OPENROUTER_API_KEY", "")
    mode = env.get("GRC_RELEVANCE_MODE", "off")
    probability = env.get("GRC_RELEVANCE_MIN_PROBABILITY", "0.95")
    timeout = env.get("GRC_RELEVANCE_TIMEOUT_SECONDS", "4")
    try:
        if (
            not model.startswith("openrouter/")
            or not key
            or mode not in {"off", "shadow", "enabled"}
            or not math.isfinite(float(probability))
            or not 0.5 <= float(probability) <= 1
            or not math.isfinite(float(timeout))
            or not 0 < float(timeout) <= 10
        ):
            raise ValueError()
    except (TypeError, ValueError):
        raise EnvironmentUpdateError() from None
    return {
        "LLM_MODEL": model,
        "OPENROUTER_API_KEY": key,
        "GRC_RELEVANCE_MODE": mode,
        "GRC_RELEVANCE_MIN_PROBABILITY": probability,
        "GRC_RELEVANCE_TIMEOUT_SECONDS": timeout,
        "LOG_LEVEL": "INFO",
        "DDB_TABLE_NAME": "grcinsight-reports",
        "ARTICLES_TABLE_NAME": "grcinsight-articles",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--function-kind", choices=FUNCTIONS, required=True)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"\d{12}", args.account_id):
            raise EnvironmentUpdateError()
        arn = f"arn:aws:lambda:{args.region}:{args.account_id}:function:{FUNCTIONS[args.function_kind]}"
        owned = owned_environment(args.function_kind, os.environ)
        client = AwsCli(shutil.which("aws"), args.region, os.environ)
        print(
            "Lambda environment update starting; inspect any uncertain result before rerunning",
            flush=True,
        )
        result = configure(client, arn, deepcopy(owned))
        print("Lambda environment " + result)
        return 0
    except (Exception, KeyboardInterrupt):
        print("Lambda environment update unavailable or uncertain; no automatic retry", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
