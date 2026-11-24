#!/usr/bin/env python3
"""Verify existing function-scoped Lambda ECR retrieval; never change policies."""

import argparse
import fnmatch
import json
import re
import sys

PULL_ACTIONS = {"ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"}


def strings(value):
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, list) or not all(
        isinstance(item, str) for item in values
    ):
        raise ValueError("Malformed ECR policy")
    return values


def validate(value, account_id, region, function_name):
    if (
        not re.fullmatch(r"[0-9]{12}", account_id)
        or region != "us-east-1"
        or function_name not in {"grcinsight-go-function", "grcinsight-python-function"}
    ):
        raise ValueError("Unexpected release identity")
    expected = f"arn:aws:lambda:{region}:{account_id}:function:{function_name}"
    statements = json.loads(value["policyText"])["Statement"]
    statements = [statements] if isinstance(statements, dict) else statements
    if not isinstance(statements, list) or not statements:
        raise ValueError("Existing ECR retrieval access could not be verified")
    allowed = set()
    for statement in statements:
        actions = strings(statement.get("Action", []))
        relevant = {
            action
            for action in PULL_ACTIONS
            if any(
                fnmatch.fnmatchcase(action.lower(), pattern.lower())
                for pattern in actions
            )
        }
        if "NotAction" in statement:
            raise ValueError("Cannot verify inverted ECR actions")
        if not relevant:
            continue
        principal = statement.get("Principal")
        principal = principal if isinstance(principal, dict) else {"AWS": principal}
        services = strings(principal.get("Service", []))
        public = "*" in strings(principal.get("AWS", []))
        lambda_service = "lambda.amazonaws.com" in services
        if "NotPrincipal" in statement:
            raise ValueError("Cannot verify inverted ECR principal")
        if statement.get("Effect") == "Deny":
            if public or lambda_service:
                raise ValueError("Lambda image retrieval may be denied")
            continue
        if statement.get("Effect") != "Allow":
            raise ValueError("Unknown ECR policy effect")
        if public:
            raise ValueError("Public image retrieval grant")
        if not lambda_service:
            continue
        if "NotResource" in statement or statement.get("Resource") not in (
            None,
            "*",
            ["*"],
        ):
            raise ValueError("Unexpected Lambda retrieval resource")
        condition = statement.get("Condition", {})
        source_arns = condition.get("ArnLike", condition.get("ArnEquals", {}))
        source_arns = strings(source_arns.get("aws:SourceArn", []))
        if not source_arns or any(arn != expected for arn in source_arns):
            raise ValueError("Lambda retrieval must name only this function")
        account_condition = condition.get("StringEquals", {})
        if account_condition not in ({}, {"aws:SourceAccount": account_id}):
            raise ValueError("Unexpected source account")
        if set(condition) - {"ArnLike", "ArnEquals", "StringEquals"}:
            raise ValueError("Unknown retrieval conditions")
        if "ArnLike" in condition and "ArnEquals" in condition:
            raise ValueError("Ambiguous source restrictions")
        if set(condition.get("ArnLike", condition.get("ArnEquals", {}))) != {
            "aws:SourceArn"
        }:
            raise ValueError("Unknown source restrictions")
        allowed.update(relevant)
    if allowed != PULL_ACTIONS:
        raise ValueError("Existing ECR retrieval access could not be verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--function-name", required=True)
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(262145)
        if len(raw) > 262144:
            raise ValueError()
        validate(json.loads(raw), args.account_id, args.region, args.function_name)
        print("Existing Lambda ECR retrieval access verified")
        return 0
    except Exception:
        print(
            "Existing ECR access unavailable; reconcile separately before release",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
