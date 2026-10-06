"""Evidence boundary for regulatory changes, separate from inferred controls.

This checks publication structure and correspondence to supplied primary-source
excerpts. It does not establish the legal meaning of a rule or its applicability.
"""

from dataclasses import dataclass
import re
from typing import Any
from urllib.parse import quote, urlsplit

from core.regulatory_dates import document_effective_date

REPORT_CONTRACT_VERSION = 3
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


def _contains_complete_phrase(text: str, phrase: str) -> bool:
    """Match exact source casing and token boundaries, including short codes."""
    normalized_text = _plain(text)
    normalized_phrase = _plain(phrase)
    return bool(
        normalized_phrase
        and re.search(
            rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)",
            normalized_text,
        )
    )


def _markdown_link_destination(value: str) -> str:
    """Match the URL serialization used when evidence is placed in the prompt."""
    return quote(value, safe=":/?#[]@!$&*+,;=%")


def _table_cells(line: str) -> list[str]:
    """Split a Markdown table row without treating escaped pipes as delimiters."""
    if not line.startswith("|") or not line.endswith("|"):
        return []
    cells = []
    cell = []
    escaped = False
    for character in line[1:-1]:
        if character == "|" and not escaped:
            cells.append("".join(cell).strip())
            cell = []
        else:
            cell.append(character)
        escaped = character == "\\" and not escaped
    cells.append("".join(cell).strip())
    return cells


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
    text = match.group(1).strip()
    if text == NO_REGULATORY_CHANGES:
        return []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header = ["Change", "Jurisdiction", "Document effective date", "Source", "Evidence excerpt"]
    if (
        len(lines) < 3
        or _table_cells(lines[0]) != header
        or not re.fullmatch(r"\|[\s:|\-]+\|", lines[1])
    ):
        raise ValueError(
            "sourced regulatory changes require the evidence table or explicit absence"
        )
    by_url: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        by_url.setdefault(_markdown_link_destination(str(source["url"])), []).append(source)
    changes = []
    for line in lines[2:]:
        cells = _table_cells(line)
        if len(cells) != 5 or not all(cells):
            raise ValueError("regulatory row must supply all five evidence fields")
        change, jurisdiction, effective_date, link, excerpt = cells
        if re.search(r"\b(implied|inferred|inference)\b", change, re.I):
            raise ValueError("inferred control mappings belong in the implications section")
        linked = re.fullmatch(r"\[((?:\\.|[^\]])+)\]\((https://[^\s]+)\)", link)
        label = re.sub(r"\\([\\[\]()|])", r"\1", linked.group(1)) if linked else ""
        url = linked.group(2) if linked else ""
        candidates = [source for source in by_url.get(url, []) if source["title"] == label]
        if not candidates or not is_regulatory_publisher(url):
            raise ValueError("regulatory change requires a supplied primary regulatory source")
        candidates = [
            source
            for source in candidates
            if len(excerpt) >= 20 and _plain(excerpt) in _plain(str(source.get("snippet") or ""))
        ]
        if not candidates:
            raise ValueError("regulatory evidence excerpt is absent from the supplied source text")
        if not _contains_complete_phrase(excerpt, change):
            raise ValueError("regulatory change must quote an evidenced clause")
        dates = {document_effective_date(source) for source in candidates}
        if not any(effective_date == (date or "Unknown") for date in dates):
            raise ValueError("document effective date must match publisher metadata or be Unknown")
        attested_date = None if effective_date == "Unknown" else effective_date
        if jurisdiction != "Unknown" and not _contains_complete_phrase(excerpt, jurisdiction):
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
