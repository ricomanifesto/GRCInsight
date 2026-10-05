"""Evidence boundary for regulatory changes, separate from inferred controls.

This checks publication structure and correspondence to supplied primary-source
excerpts. It does not establish the legal meaning of a rule or its applicability.
"""

from dataclasses import dataclass
import re
from typing import Any
from urllib.parse import urlsplit

REPORT_CONTRACT_VERSION = 2
REGULATORY_SECTION = "Sourced Regulatory Changes"
INFERENCE_SECTION = "Inferred Control and Governance Implications"
NO_REGULATORY_CHANGES = "No sourced regulatory changes identified in the supplied evidence."
REPORT_SECTION_TITLES = (
    "Executive Summary",
    REGULATORY_SECTION,
    INFERENCE_SECTION,
    "Industry Impact Analysis",
    "Risk Assessment",
    "Recommendations for Action",
    "Source Highlights",
)
# Bounded primary-publisher policy. A publisher's presence permits an evidenced
# row, never automatically classifies an article as a regulatory development.
REGULATORY_PUBLISHERS = (
    "sec.gov",
    "ftc.gov",
    "federalregister.gov",
    "congress.gov",
    "eur-lex.europa.eu",
    "commission.europa.eu",
    "edpb.europa.eu",
    "ico.org.uk",
    "legislation.gov.uk",
    "fca.org.uk",
    "cppa.ca.gov",
)


@dataclass(frozen=True)
class RegulatoryChange:
    change: str
    jurisdiction: str | None
    effective_date: str | None
    source_url: str
    evidence_excerpt: str


def is_regulatory_publisher(url: str) -> bool:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and parsed.username is None
        and parsed.password is None
        and any(host == domain or host.endswith("." + domain) for domain in REGULATORY_PUBLISHERS)
    )


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def validate_regulatory_evidence(
    markdown: str, sources: list[dict[str, Any]]
) -> list[RegulatoryChange]:
    """Reject unsourced legal-change rows; unknown facts remain explicit nulls."""
    for title in (REGULATORY_SECTION, INFERENCE_SECTION):
        if len(re.findall(rf"(?m)^## {re.escape(title)}\s*$", markdown)) != 1:
            raise ValueError(f"report requires one {title} section")
    if re.search(r"(?m)^## Key Regulatory Developments\s*$", markdown):
        raise ValueError("legacy regulatory heading cannot classify a new report")
    match = re.search(rf"(?ms)^## {REGULATORY_SECTION}\s*\n(.*?)(?=^## |\Z)", markdown)
    assert match is not None
    text = match.group(1).strip()
    if text == NO_REGULATORY_CHANGES:
        return []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header = ["Change", "Jurisdiction", "Effective date", "Source", "Evidence excerpt"]
    if (
        len(lines) < 3
        or [cell.strip() for cell in lines[0].strip("|").split("|")] != header
        or not re.fullmatch(r"\|[\s:|\-]+\|", lines[1])
    ):
        raise ValueError(
            "sourced regulatory changes require the evidence table or explicit absence"
        )
    by_url = {str(source["url"]): source for source in sources}
    changes = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 5 or not all(cells):
            raise ValueError("regulatory row must supply all five evidence fields")
        change, jurisdiction, effective_date, link, excerpt = cells
        if re.search(r"\b(implied|inferred|inference)\b", change, re.I):
            raise ValueError("inferred control mappings belong in the implications section")
        linked = re.fullmatch(r"\[(?:\\.|[^\]])+\]\((https://[^\s]+)\)", link)
        url = linked.group(1) if linked else ""
        source = by_url.get(url)
        if source is None or not is_regulatory_publisher(url):
            raise ValueError("regulatory change requires a supplied primary regulatory source")
        evidence = _plain(str(source.get("snippet") or ""))
        if len(excerpt) < 20 or _plain(excerpt) not in evidence:
            raise ValueError("regulatory evidence excerpt is absent from the supplied source text")
        if _plain(change).casefold() not in _plain(excerpt).casefold():
            raise ValueError("regulatory change must quote an evidenced clause")
        if effective_date != "Unknown":
            operative_phrase = (
                r"(?:takes? effect|effective(?: date)?|enters? into force|applies? from)"
            )
            date = re.escape(effective_date)
            if not re.search(
                rf"(?:{operative_phrase}\s*(?:is|on|from|:)?\s*{date}"
                rf"|{date}(?:(?!\d{{4}}-\d{{2}}-\d{{2}})[^.!?\n]){{0,200}}"
                rf"{operative_phrase}(?!(?:\s*(?:is|on|from|:)\s*)?"
                rf"\d{{4}}-\d{{2}}-\d{{2}}))",
                excerpt,
                re.I,
            ):
                raise ValueError("regulatory effective date must be identified as such in evidence")
        for field, value in (("jurisdiction", jurisdiction), ("effective date", effective_date)):
            if value != "Unknown" and _plain(value).casefold() not in _plain(excerpt).casefold():
                raise ValueError(f"regulatory {field} must be evidenced or Unknown")
        changes.append(
            RegulatoryChange(
                change,
                None if jurisdiction == "Unknown" else jurisdiction,
                None if effective_date == "Unknown" else effective_date,
                url,
                excerpt,
            )
        )
    return changes
