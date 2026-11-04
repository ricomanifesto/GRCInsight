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
        }
    ],
}


def test_expected_existing_retrieval_allow_is_verified_without_mutating_policy():
    value = deepcopy(POLICY)
    check.validate({"policyText": json.dumps(value)})
    assert value == POLICY


@pytest.mark.parametrize(
    "change", ["missing", "wrong_principal", "missing_action", "condition", "deny", "resource"]
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
        check.validate({"policyText": json.dumps(value)})
