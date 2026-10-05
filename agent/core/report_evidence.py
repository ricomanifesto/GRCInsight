"""Evidence boundary for regulatory changes, separate from inferred controls.

This checks publication structure and correspondence to supplied primary-source
excerpts. It does not establish the legal meaning of a rule or its applicability.
"""

from dataclasses import dataclass
import re
from typing import Any
from urllib.parse import quote, urlsplit

from core.regulatory_dates import document_effective_date

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
    document_effective_date: str | None
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


def _markdown_link_destination(value: str) -> str:
    """Match the URL serialization used when evidence is placed in the prompt."""
    return quote(value, safe=":/?#[]@!$&*+,;=%")


def _reject_effective_dates_outside_regulatory_table(
    markdown: str, regulatory_section: re.Match[str]
) -> None:
    """Keep model-authored regulatory timing inside the evidence table.

    A date in prose cannot be checked against the row that supplied it (and, in
    particular, can be inferred from a snippet when publisher metadata says
    ``Unknown``).  Remove the complete section body before looking for the
    common ways an ISO date is asserted as an effective or deadline date.
    """
    outside = markdown[: regulatory_section.start(1)] + markdown[regulatory_section.end(1) :]
    timing = (
        r"(?:takes?|took|comes?|came|enters?|entered)\s+(?:into\s+)?(?:effect|force)"
        r"|(?:becomes?|became)\s+effective"
        r"|effective\s+(?:date|on|as\s+of|from)"
        r"|(?:compliance\s+)?deadline"
    )
    iso_date = r"\b\d{4}-\d{2}-\d{2}\b"
    sentence_text = r"[^\n.!?]*"
    if re.search(
        rf"(?:{iso_date}{sentence_text}(?:{timing})|(?:{timing}){sentence_text}{iso_date})",
        outside,
        re.I,
    ):
        raise ValueError(
            "regulatory effective dates and deadlines must appear only in the sourced table"
        )


def validate_regulatory_evidence(
    markdown: str, sources: list[dict[str, Any]]
) -> list[RegulatoryChange]:
    """Reject unsourced legal-change rows; unknown facts remain explicit nulls."""
    for source in sources:
        document_effective_date(source)
    for title in (REGULATORY_SECTION, INFERENCE_SECTION):
        if len(re.findall(rf"(?m)^## {re.escape(title)}\s*$", markdown)) != 1:
            raise ValueError(f"report requires one {title} section")
    if re.search(r"(?m)^## Key Regulatory Developments\s*$", markdown):
        raise ValueError("legacy regulatory heading cannot classify a new report")
    match = re.search(rf"(?ms)^## {REGULATORY_SECTION}\s*\n(.*?)(?=^## |\Z)", markdown)
    assert match is not None
    _reject_effective_dates_outside_regulatory_table(markdown, match)
    text = match.group(1).strip()
    if text == NO_REGULATORY_CHANGES:
        return []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header = ["Change", "Jurisdiction", "Document effective date", "Source", "Evidence excerpt"]
    if (
        len(lines) < 3
        or [cell.strip() for cell in lines[0].strip("|").split("|")] != header
        or not re.fullmatch(r"\|[\s:|\-]+\|", lines[1])
    ):
        raise ValueError(
            "sourced regulatory changes require the evidence table or explicit absence"
        )
    by_url = {
        serialized: source
        for source in sources
        for serialized in (
            str(source["url"]),
            _markdown_link_destination(str(source["url"])),
        )
    }
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
        attested_date = document_effective_date(source)
        if effective_date != (attested_date or "Unknown"):
            raise ValueError("document effective date must match publisher metadata or be Unknown")
        if (
            jurisdiction != "Unknown"
            and _plain(jurisdiction).casefold() not in _plain(excerpt).casefold()
        ):
            raise ValueError("regulatory jurisdiction must be evidenced or Unknown")
        changes.append(
            RegulatoryChange(
                change,
                None if jurisdiction == "Unknown" else jurisdiction,
                attested_date,
                url,
                excerpt,
            )
        )
    return changes
