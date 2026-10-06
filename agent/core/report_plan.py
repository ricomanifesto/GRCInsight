"""Bounded model selections and application-owned report prose.

Keep this module dependency-free: publication verifies the same rendering offline.
Only quoted regulatory evidence may contain model-selected free text, and it is
confined to the sourced table and checked against retained primary-source text.
"""

from copy import deepcopy
import json
from typing import Any
from urllib.parse import quote

from core.regulatory_dates import document_effective_date
from core.report_evidence import NO_REGULATORY_CHANGES, validate_regulatory_evidence

# Labels, implications and actions are authored here, never supplied by a model.
CONTROLS = {
    "access_management": (
        "Access management",
        "Assess whether access reviews and privileged-session controls address the reported exposure.",
        "Review privileged access, authentication coverage and account revocation evidence.",
    ),
    "vulnerability_management": (
        "Vulnerability management",
        "Assess whether asset visibility and remediation controls address the reported exposure.",
        "Identify affected assets and verify remediation or compensating controls with their owners.",
    ),
    "incident_response": (
        "Incident response",
        "Assess whether incident procedures support containment and evidence preservation.",
        "Review response ownership, containment procedures and incident evidence retention.",
    ),
    "third_party_risk": (
        "Third-party risk",
        "Assess dependencies on suppliers and the assurance available for their controls.",
        "Review relevant supplier dependencies, assurance evidence and escalation contacts.",
    ),
    "data_protection": (
        "Data protection",
        "Assess whether data handling and protection controls address the reported exposure.",
        "Review sensitive-data access, retention and protection controls with accountable owners.",
    ),
    "change_management": (
        "Change management",
        "Assess whether change approval and validation controls address the reported exposure.",
        "Review change approvals, validation evidence and recovery procedures.",
    ),
    "monitoring": (
        "Monitoring and detection",
        "Assess whether monitoring coverage can identify the reported activity.",
        "Review relevant telemetry, detection coverage and alert ownership.",
    ),
    "governance": (
        "Governance and accountability",
        "Assess whether ownership and assurance practices support the relevant risk decisions.",
        "Confirm control ownership and collect evidence for the relevant risk decisions.",
    ),
}
SECTORS = {
    "financial_services": "Financial services",
    "healthcare": "Healthcare",
    "public_sector": "Public sector",
    "technology": "Technology",
    "critical_infrastructure": "Critical infrastructure",
    "cross_sector": "Cross-sector organizations",
}
PRIORITIES = {"high": "High", "medium": "Medium", "low": "Low"}


def _object(value: Any, keys: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("report plan has missing or unsupported fields")
    return value


def _list(value: Any, maximum: int) -> list[Any]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError("report plan contains an invalid selection list")
    return value


def _source_id(value: Any, sources: list[dict[str, Any]]) -> int:
    if type(value) is not int or not 1 <= value <= len(sources):
        raise ValueError("report plan references an unavailable source")
    return value


def _source_ids(value: Any, sources: list[dict[str, Any]]) -> None:
    ids = [_source_id(item, sources) for item in _list(value, 12)]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("report plan source selections must be nonempty and unique")


def _choice(value: Any, choices: dict) -> None:
    if not isinstance(value, str) or value not in choices:
        raise ValueError("report plan contains an unsupported selection")


def _validate_plan(value: Any, sources: list[dict[str, Any]]) -> dict[str, Any]:
    plan = _object(value, {"regulatory_changes", "control_implications", "industry_impacts"})
    if not 1 <= len(sources) <= 12:
        raise ValueError("report plan requires one to twelve retained sources")
    seen = set()
    for row in _list(plan["regulatory_changes"], 12):
        row = _object(row, {"source_id", "change", "jurisdiction", "evidence_excerpt"})
        source_id = _source_id(row["source_id"], sources)
        if source_id in seen:
            raise ValueError("report plan repeats a regulatory source")
        seen.add(source_id)
        for name, maximum in (("change", 400), ("jurisdiction", 120), ("evidence_excerpt", 1600)):
            text = row[name]
            if (
                not isinstance(text, str)
                or not text.strip()
                or len(text) > maximum
                or any(character in text for character in "\r\n|")
            ):
                raise ValueError("report plan regulatory fields must be bounded table cells")
    for collection, identity, catalog, keys in (
        ("control_implications", "control_id", CONTROLS, {"control_id", "priority", "source_ids"}),
        ("industry_impacts", "sector_id", SECTORS, {"sector_id", "source_ids"}),
    ):
        seen = set()
        for row in _list(plan[collection], len(catalog)):
            row = _object(row, keys)
            _choice(row[identity], catalog)
            if row[identity] in seen:
                raise ValueError("report plan repeats a catalog selection")
            seen.add(row[identity])
            _source_ids(row["source_ids"], sources)
            if collection == "control_implications":
                _choice(row["priority"], PRIORITIES)
    return plan


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("report plan contains duplicate JSON fields")
        result[key] = value
    return result


def parse_report_plan(text: str, sources: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(text, str) or len(text) > 65536:
        raise ValueError("report plan must be a bounded JSON object")
    plan = _validate_plan(json.loads(text, object_pairs_hook=_unique_fields), sources)
    render_report_plan(plan, sources)
    return deepcopy(plan)


def _link(source: dict[str, Any]) -> str:
    label = str(source["title"])
    for character in ("\\", "[", "]", "(", ")", "|"):
        label = label.replace(character, "\\" + character)
    destination = quote(str(source["url"]), safe=":/?#[]@!$&*+,;=%")
    return f"[{label}]({destination})"


def render_report_plan(
    value: Any, sources: list[dict[str, Any]], *, include_digest: bool = False
) -> str:
    plan = _validate_plan(value, sources)

    def citations(ids: list[int]) -> str:
        return "; ".join(_link(sources[index - 1]) for index in ids)

    controls = plan["control_implications"]
    priorities = "; ".join(
        f"{CONTROLS[row['control_id']][0]} ({PRIORITIES[row['priority']]})" for row in controls
    )
    executive = (
        "This report separates sourced regulatory changes from inferred control and governance implications. "
        "Use the primary evidence to assess applicability to your organization.\n\n"
        + (
            f"Inferred review priorities: {priorities}."
            if priorities
            else "No control mappings were selected from the supplied evidence."
        )
    )
    regulatory = NO_REGULATORY_CHANGES
    if plan["regulatory_changes"]:
        rows = [
            "| Change | Jurisdiction | Document effective date | Source | Evidence excerpt |",
            "|---|---|---|---|---|",
        ]
        for row in plan["regulatory_changes"]:
            source = sources[row["source_id"] - 1]
            date = document_effective_date(source) or "Unknown"
            rows.append(
                f"| {row['change']} | {row['jurisdiction']} | {date} | {_link(source)} | {row['evidence_excerpt']} |"
            )
        regulatory = "\n".join(rows)
    implications = [
        f"- **{CONTROLS[row['control_id']][0]} — Inference:** {CONTROLS[row['control_id']][1]} {citations(row['source_ids'])}"
        for row in controls
    ]
    industries = [
        f"- **{SECTORS[row['sector_id']]} — Inferred relevance:** Review your exposure to the cited developments before assigning sector-specific impact. {citations(row['source_ids'])}"
        for row in plan["industry_impacts"]
    ]
    risks = [
        f"- **{CONTROLS[row['control_id']][0]} — Inferred priority: {PRIORITIES[row['priority']]}.** This is a review priority, not a measured severity or a finding of legal applicability. {citations(row['source_ids'])}"
        for row in controls
    ]
    actions = [
        f"- **{CONTROLS[row['control_id']][0]}:** {CONTROLS[row['control_id']][2]} {citations(row['source_ids'])}"
        for row in controls
    ]
    highlights = []
    for source in sources:
        line = "- " + _link(source)
        if include_digest:
            destination = quote(str(source["digest_url"]), safe=":/?#[]@!$&*+,;=%")
            line += f" · [View in SentryDigest]({destination})"
        highlights.append(line)
    sections = (
        ("Executive Summary", executive),
        ("Sourced Regulatory Changes", regulatory),
        (
            "Inferred Control and Governance Implications",
            "\n".join(implications)
            or "No control mappings were selected from the supplied evidence.",
        ),
        (
            "Industry Impact Analysis",
            "\n".join(industries)
            or "No sector-specific implications were selected from the supplied evidence.",
        ),
        ("Risk Assessment", "\n".join(risks) or "No inferred review priorities were selected."),
        (
            "Recommendations for Action",
            "\n".join(actions)
            or "Review the supplied evidence before assigning follow-up actions.",
        ),
        ("Source Highlights", "\n".join(highlights)),
    )
    body = "\n\n".join(f"## {heading}\n\n{text}" for heading, text in sections)
    validate_regulatory_evidence(body, sources)
    return body


def validate_rendered_report(
    body: str, plan: Any, sources: list[dict[str, Any]], *, include_digest: bool = False
) -> None:
    expected = render_report_plan(plan, sources, include_digest=include_digest)
    if body.strip() != expected:
        raise ValueError("report content does not match the retained report plan")
