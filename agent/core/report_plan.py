"""Bounded model selections and application-owned report prose.

Keep this module dependency-free: publication verifies the same rendering offline.
Model-selected event excerpts and review focuses must match retained source text.
Regulatory claims remain confined to their separately validated primary-source table.
Version 3 is supported only to verify immutable historical publications.
"""

from copy import deepcopy
import json
from typing import Any
import unicodedata
from urllib.parse import quote

from core.regulatory_dates import document_effective_date
from core.report_evidence import (
    NO_REGULATORY_CHANGES,
    REPORT_CONTRACT_VERSION,
    _contains_complete_phrase,
    validate_regulatory_evidence,
)

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


# Conditional review questions, owners and evidence requests are application-owned.
# They do not assert local exposure, measured severity or legal applicability.
CONTROL_REVIEWS = {
    "access_management": (
        "Identity and access owner",
        "Could the reported access path bypass your account or privilege boundaries?",
        "access scope, authentication coverage, session revocation and a permission-test result",
    ),
    "vulnerability_management": (
        "Vulnerability and asset owners",
        "Do your deployed products and configurations meet the reported exposure conditions?",
        "affected-asset inventory, installed versions, remediation status and an exception owner",
    ),
    "incident_response": (
        "Incident response lead",
        "Could your response team contain this activity and establish what was accessed?",
        "containment responsibilities, retained logs and the most recent response exercise",
    ),
    "third_party_risk": (
        "Supplier risk owner",
        "Does a supplier have the access or operating responsibility described in this event?",
        "supplier access scope, control responsibilities and evidence of remediation assurance",
    ),
    "data_protection": (
        "Data and privacy owners",
        "Could the reported access path expose personal or sensitive data you hold?",
        "data inventory, access restrictions, audit logs and a documented exposure assessment",
    ),
    "change_management": (
        "Change and service owners",
        "Would your change process detect an incomplete or ineffective remediation?",
        "change approval, rollout coverage, post-change validation and rollback ownership",
    ),
    "monitoring": (
        "Detection and monitoring owner",
        "Would your telemetry distinguish the reported activity from expected use?",
        "log coverage, a detection test, alert routing and investigation ownership",
    ),
    "governance": (
        "Risk and control owners",
        "Does this development change an assumption in your control or assurance process?",
        "the affected assumption, accountable owner and a recorded decision to act or accept risk",
    ),
}


def _quoted_text(value: str) -> str:
    """Render untrusted quoted evidence as text, never Markdown or HTML commands."""
    # Numeric character references survive Markdown as literal text. Encode '&'
    # too, so a source's existing entity is displayed verbatim, not decoded twice.
    reserved = set("&<>\\[]()|*_`#!@%")
    return "".join(
        f"&#{ord(character)};" if character in reserved else character for character in value
    )


def _title_only_text(value: str) -> str:
    """Ignore cosmetic differences only when rejecting recycled source titles."""
    text = " ".join(value.split()).casefold()
    start, end = 0, len(text)
    while start < end and (
        text[start].isspace() or unicodedata.category(text[start]).startswith("P")
    ):
        start += 1
    while end > start and (
        text[end - 1].isspace() or unicodedata.category(text[end - 1]).startswith("P")
    ):
        end -= 1
    return text[start:end]


def _validate_finding(row: dict[str, Any], sources: list[dict[str, Any]]) -> None:
    if len(row["source_ids"]) != 1:
        raise ValueError("each finding requires exactly one source, not a citation bundle")
    source = sources[row["source_ids"][0] - 1]
    excerpt, focus = row["evidence_excerpt"], row["focus"]
    for value, minimum, maximum in ((excerpt, 40, 700), (focus, 3, 120)):
        if (
            not isinstance(value, str)
            or not minimum <= len(value) <= maximum
            or value != value.strip()
            or any(c in value for c in "\r\n")
        ):
            raise ValueError("finding requires a bounded source excerpt and review focus")
    snippet = source.get("snippet")
    if (
        not isinstance(snippet, str)
        or not _contains_complete_phrase(snippet, excerpt)
        or not _contains_complete_phrase(excerpt, focus)
    ):
        raise ValueError("finding excerpt and focus must match the selected source exactly")
    if _title_only_text(excerpt) == _title_only_text(str(source.get("title", ""))):
        raise ValueError("a source title alone is not finding evidence")


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


def _validate_plan(
    value: Any,
    sources: list[dict[str, Any]],
    contract_version: int = REPORT_CONTRACT_VERSION,
) -> dict[str, Any]:
    if type(contract_version) is not int or contract_version not in {
        3,
        REPORT_CONTRACT_VERSION,
    }:
        raise ValueError("unsupported report plan contract version")
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
        for name, maximum in (
            ("change", 400),
            ("jurisdiction", 120),
            ("evidence_excerpt", 1600),
        ):
            text = row[name]
            if (
                not isinstance(text, str)
                or not text.strip()
                or len(text) > maximum
                or any(character in text for character in "\r\n|")
            ):
                raise ValueError("report plan regulatory fields must be bounded table cells")
    for collection, identity, catalog, keys in (
        (
            "control_implications",
            "control_id",
            CONTROLS,
            {"control_id", "priority", "source_ids"},
        ),
        ("industry_impacts", "sector_id", SECTORS, {"sector_id", "source_ids"}),
    ):
        seen = set()
        findings = collection == "control_implications" and contract_version >= 4
        if findings:
            keys = keys | {"focus", "evidence_excerpt"}
        for row in _list(plan[collection], 6 if findings else len(catalog)):
            row = _object(row, keys)
            _choice(row[identity], catalog)
            _source_ids(row["source_ids"], sources)
            selection = row["source_ids"][0] if findings else row[identity]
            if selection in seen:
                raise ValueError("report plan repeats a catalog selection or finding source")
            seen.add(selection)
            if findings:
                _validate_finding(row, sources)
            if collection == "control_implications":
                _choice(row["priority"], PRIORITIES)
    if contract_version >= 4:
        covered = {row["source_ids"][0] for row in plan["control_implications"]}
        covered.update(row["source_id"] for row in plan["regulatory_changes"])
        if not covered:
            raise ValueError(
                "report requires at least one evidence-backed finding or regulatory change"
            )
        for row in plan["industry_impacts"]:
            if not set(row["source_ids"]) <= covered:
                raise ValueError(
                    "industry implications require a supported finding or regulatory change"
                )
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
    value: Any,
    sources: list[dict[str, Any]],
    *,
    include_digest: bool = False,
    contract_version: int = REPORT_CONTRACT_VERSION,
) -> str:
    plan = _validate_plan(value, sources, contract_version)

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
    if contract_version >= 4:
        # Present events before control categories; keep each excerpt once in the
        # body so selecting more controls cannot multiply generic paragraphs.
        ordered = sorted(controls, key=lambda row: list(PRIORITIES).index(row["priority"]))
        executive_source_ids = {row["source_ids"][0] for row in ordered[:3]}
        executive_items = [
            f"- **{_quoted_text(row['focus'])}.** Source excerpt: "
            f"“{_quoted_text(row['evidence_excerpt'])}” {citations(row['source_ids'])} "
            f"**Inferred review priority:** {PRIORITIES[row['priority']]} "
            f"({CONTROLS[row['control_id']][0]})."
            for row in ordered[:3]
        ]
        if not executive_items:
            executive_items = [
                f"- Source reports: “{_quoted_text(row['change'])}”. "
                f"{citations([row['source_id']])}"
                for row in plan["regulatory_changes"][:3]
            ]
        executive = "\n".join(executive_items) + (
            f"\n\nScope: {len(controls)} selected control findings and "
            f"{len(plan['regulatory_changes'])} sourced regulatory changes from "
            f"{len(sources)} retained sources. Review questions and priorities are inferences; "
            "local exposure and legal applicability require verification."
        )
        implications = [
            f"- **{_quoted_text(row['focus'])} — {CONTROLS[row['control_id']][0]}.** "
            + (
                f"Source excerpt: “{_quoted_text(row['evidence_excerpt'])}” "
                if row["source_ids"][0] not in executive_source_ids
                else ""
            )
            + f"**Inferred control question:** {CONTROL_REVIEWS[row['control_id']][1]} "
            + citations(row["source_ids"])
            for row in ordered
        ]
        risks = [
            f"- **{_quoted_text(row['focus'])} — Inferred priority: {PRIORITIES[row['priority']]}.** "
            "Validate the exposure conditions in the quoted finding before adopting this priority. "
            f"{citations(row['source_ids'])}"
            for row in ordered
        ]
        actions = [
            f"- **{_quoted_text(row['focus'])}. Owner:** {CONTROL_REVIEWS[row['control_id']][0]}. "
            f"**If applicable — Evidence to request:** {CONTROL_REVIEWS[row['control_id']][2]}. "
            "Record applicability and the follow-up decision against this finding. "
            f"{citations(row['source_ids'])}"
            for row in ordered
        ]
        by_source = {row["source_ids"][0]: row["focus"] for row in controls}
        by_source.update({row["source_id"]: row["change"] for row in plan["regulatory_changes"]})
        industries = [
            f"- **{SECTORS[row['sector_id']]} — Inferred relevance:** "
            + "; ".join(
                f"“{_quoted_text(by_source[index])}” {citations([index])}"
                for index in row["source_ids"]
            )
            + ". Check whether these activities or dependencies exist in your organization."
            for row in plan["industry_impacts"]
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
        (
            "Risk Assessment",
            "\n".join(risks) or "No inferred review priorities were selected.",
        ),
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
    body: str,
    plan: Any,
    sources: list[dict[str, Any]],
    *,
    include_digest: bool = False,
    contract_version: int = REPORT_CONTRACT_VERSION,
) -> None:
    expected = render_report_plan(
        plan, sources, include_digest=include_digest, contract_version=contract_version
    )
    if body.strip() != expected:
        raise ValueError("report content does not match the retained report plan")
