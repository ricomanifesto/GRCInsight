"""The report catalog is authored once and every reader agrees with it."""

import json
from pathlib import Path
import re

from core import entities, report_evidence, report_plan
from core.report_catalog import CATALOG, CATALOG_PATH, SCHEMA_PATH, report_plan_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
RENDERER_JS = REPO_ROOT / "site" / "static" / "renderer.js"


def rebuilt_catalog() -> dict:
    """Rebuild the catalog from the constants the application actually uses."""
    controls = {}
    for key, (label, implication, action) in report_plan.CONTROLS.items():
        owner, question, evidence = report_plan.CONTROL_REVIEWS[key]
        step, decision, trigger = report_plan.CONTROL_DECISIONS[key]
        controls[key] = {
            "label": label,
            "implication": implication,
            "action": action,
            "review": {"owner": owner, "question": question, "evidence": evidence},
            "decision": {"step": step, "implication": decision, "trigger": trigger},
            "reference_controls": report_plan.REFERENCE_CONTROLS[key],
        }
    frames = {
        name: {
            "controls": (
                "all"
                if name == "separate"
                else [key for key in report_plan.CONTROLS if key in spec["controls"]]
            ),
            "judgment": spec["judgment"],
            "purpose": spec["purpose"],
        }
        for name, spec in report_plan.DECISION_FRAMES.items()
    }
    return {
        "contract_version": report_evidence.REPORT_CONTRACT_VERSION,
        "priorities": report_plan.PRIORITIES,
        "sectors": report_plan.SECTORS,
        "controls": controls,
        "decision_frames": frames,
        "finding_labels": list(report_plan.FINDING_LABELS),
        "evidence_note": report_plan.EVIDENCE_NOTE,
        "risk_category_keywords": {
            category: list(keywords)
            for category, keywords in entities.RISK_CATEGORY_KEYWORDS.items()
        },
        "regulatory_publishers": list(report_evidence.REGULATORY_PUBLISHERS),
    }


def test_catalog_round_trips_byte_for_byte_through_the_application_constants():
    text = json.dumps(rebuilt_catalog(), indent=2, ensure_ascii=False) + "\n"
    assert text == CATALOG_PATH.read_text(encoding="utf-8")
    assert report_plan.DECISION_FRAMES["separate"]["controls"] == set(report_plan.CONTROLS)


def test_provider_schema_enumerates_exactly_the_catalog():
    schema = report_plan_schema()
    finding = schema["properties"]["control_implications"]["items"]["properties"]
    sector = schema["properties"]["industry_impacts"]["items"]["properties"]
    assert finding["control_id"]["enum"] == list(CATALOG["controls"])
    assert finding["priority"]["enum"] == list(CATALOG["priorities"])
    assert sector["sector_id"]["enum"] == list(CATALOG["sectors"])
    assert report_plan.report_plan_response_format()["json_schema"]["schema"] == schema
    assert SCHEMA_PATH.read_text(encoding="utf-8") == json.dumps(schema, indent=2) + "\n"


def test_contract_files_ship_with_the_core_modules_that_read_them():
    # The Python Lambda image copies agent/, and publication checks copy agent/core.
    core_dir = REPO_ROOT / "agent" / "core"
    assert CATALOG_PATH.is_relative_to(core_dir)
    assert SCHEMA_PATH.is_relative_to(core_dir)


def renderer_list(name: str) -> list[str]:
    match = re.search(rf"const {name} = \[(.*?)\];", RENDERER_JS.read_text(), re.S)
    assert match, name
    return re.findall(r"'([^']*)'", match.group(1))


def test_browser_renderer_labels_match_the_catalog():
    assert renderer_list("CONTROL_AREAS") == [
        entry["label"] for entry in CATALOG["controls"].values()
    ]
    assert renderer_list("PRIORITY_LEVELS") == list(CATALOG["priorities"].values())
    assert renderer_list("FINDING_FIELDS") == CATALOG["finding_labels"]
