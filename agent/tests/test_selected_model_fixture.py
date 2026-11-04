"""The fixed fictional pack has a positive host-grounded control selection."""

from copy import deepcopy
import json
from pathlib import Path
import runpy

import pytest

from core.report_plan import parse_report_plan, report_plan_response_format

RUNNER = runpy.run_path(
    str(Path(__file__).resolve().parents[2] / "scripts/rehearse_selected_model_offline.py")
)


def test_frozen_fixture_has_positive_supplier_finding_and_regulatory_abstention():
    case = RUNNER["validate_case"]()
    assert case["calibration_plan"]["control_implications"][0]["source_ids"] == [2]
    assert case["calibration_plan"]["regulatory_changes"] == []


def test_all_empty_selection_is_not_a_successful_fixture_oracle():
    case = RUNNER["load_case"]()
    plan = deepcopy(case["calibration_plan"])
    plan["control_implications"] = []
    with pytest.raises(ValueError):
        parse_report_plan(json.dumps(plan), case["analysis_data"]["source_evidence"])


def test_fictional_notice_cannot_be_promoted_to_primary_regulatory_evidence():
    case = RUNNER["load_case"]()
    plan = deepcopy(case["calibration_plan"])
    plan["regulatory_changes"] = [
        {
            "source_id": 1,
            "change": "annual access reviews",
            "jurisdiction": "Unknown",
            "evidence_excerpt": case["analysis_data"]["source_evidence"][0]["snippet"],
        }
    ]
    with pytest.raises(ValueError):
        parse_report_plan(json.dumps(plan), case["analysis_data"]["source_evidence"])


def test_report_schema_is_fresh_and_catalog_bound():
    first = report_plan_response_format()
    first["json_schema"]["schema"]["properties"].clear()
    second = report_plan_response_format()["json_schema"]["schema"]
    assert len(second["properties"]) == 4
    assert second["properties"]["industry_impacts"]["maxItems"] == 0
