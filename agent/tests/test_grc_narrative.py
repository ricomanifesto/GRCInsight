"""Report narrative is model-written analysis held to application-owned grounding rules."""

from copy import deepcopy
import json
from pathlib import Path
import re
import runpy
from typing import Any

import pytest

from core.report_evidence import REPORT_CONTRACT_VERSION
from core.report_plan import (
    REFERENCE_CONTROLS,
    ReportQualityError,
    parse_report_plan,
    render_report_plan,
    report_finding_groups,
    report_plan_response_format,
    validate_rendered_report,
)

FIXTURES = Path(__file__).parent / "fixtures"
V5 = json.loads((FIXTURES / "report-v5-2026-10-29/evidence-manifest.json").read_text())
SOURCES = V5["sources"]
EXCERPTS = {row["source_ids"][0]: row for row in V5["report_plan"]["control_implications"]}


def finding(source_id, control_id, priority, headline, significance):
    row = EXCERPTS[source_id]
    return {
        "control_id": control_id,
        "priority": priority,
        "source_ids": [source_id],
        "focus": row["focus"],
        "evidence_origin": row["evidence_origin"],
        "evidence_excerpt": row["evidence_excerpt"],
        "headline": headline,
        "significance": significance,
    }


PLAN: dict[str, Any] = {
    "regulatory_changes": [],
    "industry_impacts": [],
    "executive_brief": {
        "paragraphs": [
            {
                "text": (
                    "Two intrusions this period aimed at the records and keys that assurance "
                    "depends on. Attackers used a Broadcom VMware ESX flaw to reduce audit trail "
                    "visibility, and a Cisco Catalyst SD-WAN campaign planted malware built to copy "
                    "the keys that encrypt traffic between sites. Both weaken evidence that control "
                    "owners rely on, so logging integrity and key management deserve review ahead "
                    "of routine patch tracking."
                ),
                "source_ids": [3, 10],
            },
            {
                "text": (
                    "Exposed administrative surfaces are the second theme. Palo Alto Networks "
                    "reports active exploitation of management interfaces exposed to the internet, "
                    "and Cisco says a Secure Firewall Adaptive Security Appliance (ASA) Software "
                    "flaw has been exploited in the wild. Where these products are deployed, the "
                    "review question is whether management access is restricted and whether patch "
                    "exceptions have accountable owners."
                ),
                "source_ids": [12, 1],
            },
        ]
    },
    "control_implications": [
        finding(
            3,
            "monitoring",
            "high",
            "Broadcom VMware ESX flaw lets attackers reduce audit trail visibility",
            "Exploitation that reduces audit trail visibility weakens the logging evidence that "
            "control testing and incident reconstruction depend on. Owners of virtualization "
            "platforms should confirm whether ESX hosts are in scope and whether their audit "
            "records are protected from tampering.",
        ),
        finding(
            10,
            "data_protection",
            "high",
            "Cisco Catalyst SD-WAN intrusions target the keys that encrypt traffic between sites",
            "Malware that copies encryption keys undermines the assumption that encrypted links "
            "protect data in transit. Data protection and network owners should confirm whether "
            "Catalyst SD-WAN controllers are in scope and when keys were last rotated.",
        ),
        finding(
            12,
            "access_management",
            "medium",
            "Palo Alto Networks management interface faces active exploitation when exposed online",
            "Management interfaces reachable from the internet widen the privileged access surface "
            "that access reviews are meant to limit. Identity and access owners should confirm "
            "whether any Palo Alto Networks management interface is internet-facing and whether "
            "administrative access is restricted.",
        ),
        finding(
            1,
            "vulnerability_management",
            "medium",
            "Secure Firewall Adaptive Security Appliance (ASA) Software flaw is exploited in the wild",
            "An exploited flaw in perimeter firewalls tests whether patch timelines and exception "
            "approvals hold for internet-facing infrastructure. Owners of Cisco ASA and FTD "
            "deployments should confirm patch status and record any accepted exception.",
        ),
    ],
}


def section(body, title):
    return body.split(f"## {title}\n\n", 1)[1].split("\n\n## ", 1)[0]


def finding_blocks(body):
    return [block.strip() for block in section(body, "Evidence and Decisions").split("### ")[1:]]


def rendered(plan=PLAN):
    parsed = parse_report_plan(json.dumps(plan), SOURCES)
    return parsed, render_report_plan(parsed, SOURCES)


def test_current_contract_is_the_grounded_narrative_contract():
    assert REPORT_CONTRACT_VERSION == 6


def test_executive_summary_carries_the_model_analysis_with_application_citations():
    plan, body = rendered()
    summary = section(body, "Executive Summary")
    paragraphs = summary.split("\n\n")
    assert len(paragraphs) == 3
    assert paragraphs[0].startswith("Two intrusions this period aimed at the records")
    assert "logging integrity and key management" in paragraphs[0]
    assert SOURCES[2]["url"] in paragraphs[0] and SOURCES[9]["url"] in paragraphs[0]
    assert SOURCES[11]["url"] in paragraphs[1] and SOURCES[0]["url"] in paragraphs[1]
    assert paragraphs[2].startswith("Scope: 4 findings and 0 sourced regulatory changes from 12")
    assert "whether" in paragraphs[2]
    assert not re.search(r"(?m)^\s*(?:[-*]|\d+[.)])\s", summary)
    for retired in ("First, establish", "Make confirmed exposure the basis", "Use that assessment"):
        assert retired not in body
    assert re.findall(r"(?m)^## (.+)$", body) == [
        "Executive Summary",
        "Sourced Regulatory Changes",
        "Evidence and Decisions",
        "Source Highlights",
    ]
    validate_rendered_report(body, plan, SOURCES)


def test_every_finding_leads_with_its_subject_and_shares_one_structure():
    _plan, body = rendered()
    blocks = finding_blocks(body)
    assert len(blocks) == 4
    labels = []
    for block, row in zip(blocks, PLAN["control_implications"]):
        heading, rest = block.split("\n\n", 1)
        assert heading == row["headline"].replace("(", "&#40;").replace(")", "&#41;")
        lines = rest.split("\n\n")
        labels.append(re.findall(r"(?m)^\*\*([^*]+?):\*\* ", rest))
        assert len(labels[-1]) == len(lines)
        assert row["significance"].split(".")[0] in block
        assert block.count("“") == 1
    assert len({tuple(item) for item in labels}) == 1
    assert labels[0] == [
        "Review priority",
        "Why it matters",
        "Source evidence",
        "Evidence to request",
        "Decision trigger",
        "Reference controls",
    ]
    priorities = [block.split("**Review priority:** ", 1)[1].split(" ", 1)[0] for block in blocks]
    assert priorities == ["High", "High", "Medium", "Medium"]


@pytest.mark.parametrize(
    "tamper",
    [
        lambda body: body.replace("**Why it matters:** ", "Why it matters: ", 1),
        lambda body: body.replace("\n\n**Reference controls:** ", "\n\nReference: ", 1),
    ],
)
def test_tampered_finding_structure_is_refused_as_an_editorial_failure(tamper):
    plan, body = rendered()
    with pytest.raises(ReportQualityError, match="same fields in the same order"):
        validate_rendered_report(tamper(body), plan, SOURCES)


def test_findings_drop_repeated_inference_labels_for_one_scope_note():
    _plan, body = rendered()
    evidence = section(body, "Evidence and Decisions")
    assert evidence.count("(inference)") == 0
    assert evidence.count("Inferred review priority") == 0
    assert "Control decision" not in evidence
    note = evidence.split("\n\n", 1)[0]
    assert not note.startswith("### ")
    assert "analysis of the quoted evidence" in note


def test_reference_controls_are_application_owned_review_aids():
    assert set(REFERENCE_CONTROLS) == {
        "access_management",
        "vulnerability_management",
        "incident_response",
        "third_party_risk",
        "data_protection",
        "change_management",
        "monitoring",
        "governance",
    }
    assert "ISO/IEC 27001:2022 A.8.8" in REFERENCE_CONTROLS["vulnerability_management"]
    assert "NIST CSF 2.0 PR.AA" in REFERENCE_CONTROLS["access_management"]
    assert "NIST CSF 2.0 GV.SC" in REFERENCE_CONTROLS["third_party_risk"]
    _plan, body = rendered()
    monitoring = finding_blocks(body)[0]
    assert "**Reference controls:** " + REFERENCE_CONTROLS["monitoring"] in monitoring
    assert "not a compliance determination" in section(body, "Evidence and Decisions")


def test_review_map_follows_narrative_order_then_priority():
    plan, _body = rendered()
    order = [group[0]["source_ids"][0] for group in report_finding_groups(plan)]
    assert order == [3, 10, 12, 1]


def headline_of(plan, index=0):
    return plan["control_implications"][index]


@pytest.mark.parametrize(
    ("field", "mutate"),
    [
        (
            "executive_brief.paragraphs[0]",
            lambda p: p["executive_brief"]["paragraphs"][0].update(
                text=p["executive_brief"]["paragraphs"][0]["text"]
                + " Owners have 30 days to respond."
            ),
        ),
        (
            "executive_brief.paragraphs[1]",
            lambda p: p["executive_brief"]["paragraphs"][1].update(
                text=p["executive_brief"]["paragraphs"][1]["text"]
                + " The flaw is tracked as CVE-2026-76418."
            ),
        ),
        (
            "executive_brief.paragraphs[1]",
            lambda p: p["executive_brief"]["paragraphs"][1].update(
                text=p["executive_brief"]["paragraphs"][1]["text"]
                + " It carries a high CVSS rating."
            ),
        ),
        (
            "executive_brief.paragraphs[0]",
            lambda p: p["executive_brief"]["paragraphs"][0].update(
                text=p["executive_brief"]["paragraphs"][0]["text"]
                + " Your organization is exposed."
            ),
        ),
        (
            "executive_brief.paragraphs[0]",
            lambda p: p["executive_brief"]["paragraphs"][0].update(
                text=p["executive_brief"]["paragraphs"][0]["text"]
                + " Affected firms must notify regulators."
            ),
        ),
        (
            "executive_brief.paragraphs[0]",
            lambda p: p["executive_brief"]["paragraphs"][0].update(
                text=p["executive_brief"]["paragraphs"][0]["text"]
                + " The campaign also reached Microsoft tenants."
            ),
        ),
        (
            "executive_brief.paragraphs[0]",
            lambda p: p["executive_brief"]["paragraphs"][0].update(
                text=p["executive_brief"]["paragraphs"][0]["text"]
                + " See the [advisory](https://example.com)."
            ),
        ),
        (
            "executive_brief.paragraphs[0]",
            lambda p: p["executive_brief"]["paragraphs"][0].update(source_ids=[3, 5]),
        ),
        (
            "executive_brief.paragraphs[0]",
            lambda p: p["executive_brief"]["paragraphs"][0].update(source_ids=[]),
        ),
        (
            "executive_brief.paragraphs[0]",
            lambda p: p["executive_brief"]["paragraphs"][0].update(
                text="Too short to be analysis."
            ),
        ),
        ("executive_brief", lambda p: p["executive_brief"].update(paragraphs=[])),
        (
            "executive_brief",
            lambda p: p["executive_brief"].update(
                paragraphs=p["executive_brief"]["paragraphs"] * 2
            ),
        ),
        (
            "control_implications[0].headline",
            lambda p: headline_of(p).update(
                headline="Audit trail visibility is reduced by a Broadcom VMware ESX flaw"
            ),
        ),
        (
            "control_implications[0].headline",
            lambda p: headline_of(p).update(
                headline="Broadcom VMware ESX flaw lets attackers reduce audit trail visibility."
            ),
        ),
        (
            "control_implications[0].headline",
            lambda p: headline_of(p).update(
                headline="Broadcom VMware ESX flaw is exploited by Microsoft partners"
            ),
        ),
        (
            "control_implications[0].headline",
            lambda p: headline_of(p).update(
                headline="Broadcom VMware ESX Microsoft tenants lose audit trail visibility"
            ),
        ),
        (
            "control_implications[0].significance",
            lambda p: headline_of(p).update(
                significance="Exploitation weakens logging evidence. "
                + EXCERPTS[3]["evidence_excerpt"]
            ),
        ),
        (
            "control_implications[0].significance",
            lambda p: headline_of(p).update(
                significance="Audit records matter for the 2025 audit cycle and for control owners reviewing logging evidence."
            ),
        ),
        (
            "control_implications[0].significance",
            lambda p: headline_of(p).update(significance="Short."),
        ),
        (
            "control_implications[3].significance",
            lambda p: headline_of(p, 3).update(
                significance="The firewall update bundles 41 changes, so owners should confirm patch status and record any accepted exception."
            ),
        ),
    ],
)
def test_ungrounded_narrative_fails_closed_without_echoing_model_text(field, mutate):
    plan = deepcopy(PLAN)
    mutate(plan)
    with pytest.raises(ReportQualityError) as error:
        parse_report_plan(json.dumps(plan), SOURCES)
    message = str(error.value)
    assert message.startswith(field + ":") or message.startswith(field + " ")
    for leaked in ("Microsoft", "CVE-2026", "30 days", "notify regulators", "example.com", "2025"):
        assert leaked not in message


def test_obligation_language_is_permitted_only_when_its_source_uses_it():
    plan = deepcopy(PLAN)
    sources = deepcopy(SOURCES)
    paragraph = plan["executive_brief"]["paragraphs"][0]
    paragraph["text"] += " Operators must review logging coverage."
    with pytest.raises(ReportQualityError, match="obligation"):
        parse_report_plan(json.dumps(plan), sources)
    sources[2]["snippet"] += " Operators must review logging coverage."
    parse_report_plan(json.dumps(plan), sources)


def test_identical_syndicated_findings_still_share_one_entry():
    plan = deepcopy(PLAN)
    sources = deepcopy(SOURCES)
    duplicate = deepcopy(sources[2])
    duplicate["url"] = "https://example.com/syndicated-esx"
    sources[4] = duplicate  # an unselected source slot keeps the list within twelve
    twin = deepcopy(plan["control_implications"][0])
    twin["source_ids"] = [5]
    plan["control_implications"].append(twin)
    body = render_report_plan(parse_report_plan(json.dumps(plan), sources), sources)
    assert len(finding_blocks(body)) == 4
    assert (
        body.count(EXCERPTS[3]["evidence_excerpt"].replace("(", "&#40;").replace(")", "&#41;")) == 1
    )
    assert "https://example.com/syndicated-esx" in finding_blocks(body)[0]


def test_historical_v5_publication_still_validates_exactly():
    fixture = FIXTURES / "report-v5-2026-10-29"
    markdown = (fixture / "report.md").read_text()
    body = markdown[markdown.index("## Executive Summary") :].strip()
    assert (
        render_report_plan(V5["report_plan"], SOURCES, include_digest=True, contract_version=5)
        == body
    )
    validate_rendered_report(
        body, V5["report_plan"], SOURCES, include_digest=True, contract_version=5
    )
    checker = runpy.run_path(
        str(Path(__file__).resolve().parents[2] / "scripts/check_site_report.py")
    )
    builder = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/build_site.py"))
    checker["validate_evidence_manifest"](
        markdown, builder["report_fields"](markdown), json.dumps(V5)
    )
    assert builder["review_map_rows"](markdown, V5)
    with pytest.raises(ValueError):
        parse_report_plan(json.dumps(V5["report_plan"]), SOURCES)


def test_response_format_requests_bounded_narrative_fields():
    schema = report_plan_response_format()["json_schema"]["schema"]
    finding_schema = schema["properties"]["control_implications"]["items"]
    assert {"headline", "significance"} <= set(finding_schema["required"])
    brief = schema["properties"]["executive_brief"]
    assert brief["required"] == ["paragraphs"]
    paragraph = brief["properties"]["paragraphs"]
    assert paragraph["minItems"] == 1 and paragraph["maxItems"] == 2
    assert paragraph["items"]["additionalProperties"] is False


def test_generator_requests_grounded_narrative_for_control_owners():
    from services.model_service import GRCModelService

    service = GRCModelService.__new__(GRCModelService)
    system = service._get_report_system_prompt()
    assert "compliance, risk, audit and control owners" in system
    assert "not how an exploit works" in system
    prompt = service._create_report_prompt({"source_evidence": SOURCES[:2]}, {})
    for requirement in (
        "executive_brief",
        "paragraphs",
        "one or two",
        "headline",
        "significance",
        "begins with the exact focus text",
        "Do not write CVE identifiers or CVSS scores",
        "Never address the reader as you",
        "Every figure, acronym and capitalized name",
        "industry_impacts must be empty",
        "Do not default every finding to high",
    ):
        assert requirement in prompt
    assert "decision_frame" not in prompt
