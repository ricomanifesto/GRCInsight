#!/usr/bin/env python3
"""Conservatively verify an existing Lambda ECR grant; never bootstrap access."""

import fnmatch
import json
import sys


def validate(value):
    policy = json.loads(value["policyText"])
    statements = policy["Statement"]
    if type(statements) is dict:
        statements = [statements]
    if type(statements) is not list or not statements:
        raise ValueError("Existing ECR retrieval access could not be verified")
    allowed = set()
    for statement in statements:
        if type(statement) is not dict or statement.get("Effect") == "Deny":
            raise ValueError("Existing ECR retrieval access could not be verified")
        principal = statement.get("Principal")
        service = principal.get("Service", []) if type(principal) is dict else []
        service = [service] if type(service) is str else service
        if type(service) is not list:
            raise ValueError("Existing ECR retrieval access could not be verified")
        if statement.get("Effect") != "Allow" or "lambda.amazonaws.com" not in service:
            continue
        if any(
            name in statement for name in ("Condition", "NotPrincipal", "NotAction", "NotResource")
        ) or statement.get("Resource") not in (None, "*", ["*"]):
            continue
        actions = statement.get("Action", [])
        actions = [actions] if type(actions) is str else actions
        if type(actions) is not list or any(type(action) is not str for action in actions):
            raise ValueError("Existing ECR retrieval access could not be verified")
        allowed.update(
            required
            for required in ("ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer")
            if any(fnmatch.fnmatchcase(required, action) for action in actions)
        )
    if len(allowed) != 2:
        raise ValueError("Existing ECR retrieval access could not be verified")


def main():
    try:
        raw = sys.stdin.buffer.read(262145)
        if len(raw) > 262144:
            raise ValueError()
        validate(json.loads(raw))
        print("Existing Lambda ECR retrieval access verified")
        return 0
    except Exception:
        print(
            "Existing ECR access unavailable; provision separately before release", file=sys.stderr
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
