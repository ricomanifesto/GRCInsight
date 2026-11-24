"""Normal releases verify existing ECR access without changing permissions."""

from copy import deepcopy
import json
from typing import Any

import pytest

from scripts import check_ecr_retrieval_policy as check

POLICY: dict[str, Any] = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
            "Condition": {
                "StringEquals": {"aws:SourceAccount": "123456789012"},
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:grcinsight-go-function"
                },
            },
        }
    ],
}


def test_expected_existing_retrieval_allow_is_verified_without_mutating_policy():
    value = deepcopy(POLICY)
    check.validate(
        {"policyText": json.dumps(value)},
        "123456789012",
        "us-east-1",
        "grcinsight-go-function",
    )
    assert value == POLICY


@pytest.mark.parametrize(
    "change",
    ["missing", "wrong_principal", "missing_action", "condition", "deny", "resource"],
)
def test_unknown_or_blocked_access_fails_closed(change):
    value = deepcopy(POLICY)
    statement = value["Statement"][0]
    if change == "missing":
        value["Statement"] = []
    elif change == "wrong_principal":
        statement["Principal"] = {"AWS": "unrelated"}
    elif change == "missing_action":
        statement["Action"] = ["ecr:BatchGetImage"]
    elif change == "condition":
        statement["Condition"] = {"unknown": "condition"}
    elif change == "resource":
        statement["Resource"] = "unrelated-resource"
    else:
        value["Statement"].append({"Effect": "Deny", "Principal": "*", "Action": "*"})
    with pytest.raises(ValueError):
        check.validate(
            {"policyText": json.dumps(value)},
            "123456789012",
            "us-east-1",
            "grcinsight-go-function",
        )


def test_extra_unrestricted_lambda_allow_is_not_hidden_by_a_narrow_grant():
    value = deepcopy(POLICY)
    broad = deepcopy(value["Statement"][0])
    del broad["Condition"]
    value["Statement"].append(broad)
    with pytest.raises(ValueError):
        check.validate(
            {"policyText": json.dumps(value)},
            "123456789012",
            "us-east-1",
            "grcinsight-go-function",
        )


@pytest.mark.parametrize(
    "change", ["wrong_account", "wildcard_function", "wrong_region"]
)
def test_scope_must_match_release_functions(change):
    value = deepcopy(POLICY)
    condition = value["Statement"][0]["Condition"]
    if change == "wrong_account":
        condition["StringEquals"]["aws:SourceAccount"] = "999999999999"
    else:
        condition["ArnLike"]["aws:SourceArn"] = [
            (
                "arn:aws:lambda:eu-west-1:123456789012:function:grcinsight-go-function"
                if change == "wrong_region"
                else "arn:aws:lambda:us-east-1:123456789012:function:*"
            )
        ]
    with pytest.raises(ValueError):
        check.validate(
            {"policyText": json.dumps(value)},
            "123456789012",
            "us-east-1",
            "grcinsight-go-function",
        )


@pytest.mark.parametrize("principal", ["*", {"AWS": "*"}])
def test_public_allow_is_rejected_even_alongside_narrow_lambda_grant(principal):
    value = deepcopy(POLICY)
    value["Statement"].append(
        {"Effect": "Allow", "Principal": principal, "Action": "ecr:BatchGetImage"}
    )
    with pytest.raises(ValueError):
        check.validate(
            {"policyText": json.dumps(value)},
            "123456789012",
            "us-east-1",
            "grcinsight-go-function",
        )


def test_split_narrow_grants_and_unrelated_deny_are_preserved():
    value = deepcopy(POLICY)
    first = value["Statement"][0]
    first["Action"] = "ecr:BatchGetImage"
    second = deepcopy(first)
    second["Action"] = "ecr:GetDownloadUrlForLayer"
    value["Statement"].append(second)
    value["Statement"].append(
        {"Effect": "Deny", "Principal": "*", "Action": "ecr:DeleteRepository"}
    )
    before = deepcopy(value)
    check.validate(
        {"policyText": json.dumps(value)},
        "123456789012",
        "us-east-1",
        "grcinsight-go-function",
    )
    assert value == before
