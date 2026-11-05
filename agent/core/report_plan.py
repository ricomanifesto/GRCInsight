"""Bounded model selections, grounded model narrative and application-owned structure.

Keep this module dependency-free: publication verifies the same rendering offline.
Model-selected event excerpts and review focuses must match retained source text.
From contract version 6 the model also writes the executive narrative and, per finding,
a headline and a short significance statement. Each narrative field must pass
deterministic grounding rules against the sources it cites before rendering.
Citations, links, owners, evidence requests, triggers and reference controls remain
application-owned. Regulatory claims remain confined to their separately validated
primary-source table. Versions 3 to 5 are supported only to verify immutable
historical publications.
"""

from copy import deepcopy
import json
import re
from typing import Any
from urllib.parse import quote

from core.article_evidence import article_segments, has_non_headline_text
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

# Frames are conditional management judgments, never claims about a common cause
# or the reader's actual exposure. Unsupported grouping must use separate decisions.
DECISION_FRAMES: dict[str, dict[str, Any]] = {
    "exposure": {
        "controls": {"vulnerability_management", "access_management", "data_protection"},
        "judgment": "Make confirmed exposure the basis for remediation and access-control decisions.",
        "purpose": "Start by checking which reported conditions apply to",
    },
    "supplier": {
        "controls": {"third_party_risk"},
        "judgment": "Decide where supplier access requires stronger assurance before relying on delegated controls.",
        "purpose": "Start by checking delegated responsibilities and available assurance for",
    },
    "response": {
        "controls": {"incident_response", "monitoring"},
        "judgment": "Decide whether detection and response evidence is sufficient for the reported activity before relying on response readiness.",
        "purpose": "Start by testing visibility, containment and response ownership for",
    },
    "governance": {
        "controls": {"governance", "change_management"},
        "judgment": "Decide which control assumptions need renewed evidence before continuing to rely on them.",
        "purpose": "Start by checking the assumptions that connect existing controls to",
    },
    "regulatory": {
        "controls": set(),
        "judgment": "Decide whether the sourced regulatory changes apply to your organization before assigning compliance work.",
        "purpose": "Begin the applicability assessment with",
    },
    "separate": {
        "controls": set(CONTROLS),
        "judgment": "Assess the leading findings as separate decisions, each with its own applicability and evidence requirements.",
        "purpose": "Begin with",
    },
}

# A summary step sets the agenda; the detail adds evidence, ownership and a trigger.
# Neither is a factual assertion that the cited event affects the reader.
CONTROL_DECISIONS = {
    "vulnerability_management": (
        "establish affected-asset and configuration scope",
        "A remediation decision depends on matching deployed assets to the source's exposure conditions.",
        "If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.",
    ),
    "access_management": (
        "test the relevant account and permission boundaries",
        "An access-control decision depends on whether the reported path crosses a permission boundary in your environment.",
        "If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.",
    ),
    "third_party_risk": (
        "establish which supplier access and responsibilities are delegated",
        "A supplier-assurance decision depends on the access and control responsibilities you actually delegate.",
        "If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.",
    ),
    "incident_response": (
        "test containment ownership and evidence availability",
        "A containment decision depends on whether responders can identify the affected scope and preserve evidence.",
        "If an exercise exposes an ownership or evidence gap, assign a response-plan correction and retest it.",
    ),
    "data_protection": (
        "establish the relevant data and access scope",
        "A data-protection decision depends on the data involved and the controls governing access to it.",
        "If relevant data is exposed to the reported access path, decide which protection or access change is needed.",
    ),
    "change_management": (
        "test the proposed change and recovery assumptions",
        "A change decision depends on evidence that the proposed remedy works and that recovery remains possible.",
        "If validation or recovery evidence is missing, resolve that gap before relying on the change.",
    ),
    "monitoring": (
        "test whether the reported behavior is observable",
        "A monitoring decision depends on distinguishing the reported behavior from authorized activity in your telemetry.",
        "If a detection test fails, assign the coverage or routing correction and repeat the test.",
    ),
    "governance": (
        "check whether the development changes a control assumption",
        "An assurance decision depends on whether the development changes an assumption used by your control owners.",
        "If an assumption no longer holds, record an accountable decision to change the control or accept the resulting uncertainty.",
    ),
}

# Review aids that locate each control area in two widely used catalogs. They are
# not a determination that a framework applies or that a control is deficient.
REFERENCE_CONTROLS = {
    "access_management": (
        "ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), "
        "A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, "
        "authentication and access control)"
    ),
    "vulnerability_management": (
        "ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); "
        "NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)"
    ),
    "incident_response": (
        "ISO/IEC 27001:2022 A.5.24 (incident management planning and preparation), "
        "A.5.26 (response to information security incidents); NIST CSF 2.0 RS.MA "
        "(incident management), RS.MI (incident mitigation)"
    ),
    "third_party_risk": (
        "ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), "
        "A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC "
        "(cybersecurity supply chain risk management)"
    ),
    "data_protection": (
        "ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage "
        "prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)"
    ),
    "change_management": (
        "ISO/IEC 27001:2022 A.8.32 (change management); NIST CSF 2.0 PR.PS (platform security)"
    ),
    "monitoring": (
        "ISO/IEC 27001:2022 A.8.15 (logging), A.8.16 (monitoring activities); "
        "NIST CSF 2.0 DE.CM (continuous monitoring), DE.AE (adverse event analysis)"
    ),
    "governance": (
        "ISO/IEC 27001:2022 A.5.1 (policies for information security), A.5.2 (roles and "
        "responsibilities); NIST CSF 2.0 GV.RR (roles, responsibilities and authorities), "
        "GV.OV (oversight)"
    ),
}

# Grounding rules for model-written narrative. Each rule returns an application-owned
# reason; diagnostics never echo the untrusted text that failed.
NARRATIVE_MARKUP = set("[]|*_`#<>\\{}~")
NARRATIVE_OBLIGATIONS = tuple(
    re.compile(pattern, re.I)
    for pattern in (
        r"\bmust\b",
        r"\bmandat\w*",
        r"\bobligat\w*",
        r"\bviolat\w*",
        r"\bnon-?complian\w*",
        r"\bpenalt\w*",
        r"\bfine[sd]?\b",
        r"\bsanction\w*",
        r"\bdeadlines?\b",
        r"\bliab(?:le|ility|ilities)\b",
        r"\bshall\b",
        r"\blegal(?:ly)?\s+(?:required|bound|duty|duties|requirements?)\b",
        r"\brequired\s+(?:to|by)\b",
        r"\b(?:has|have|had)\s+to\b",
        r"\bobliged\b",
    )
)
EXCERPT_RUN_WORDS = 10


def _source_corpus(sources: list[dict[str, Any]], ids: list[int]) -> str:
    parts = []
    for index in ids:
        source = sources[index - 1]
        parts.extend([str(source.get("title", "")), str(source.get("snippet", ""))])
        parts.extend(str(item.get("text", "")) for item in source.get("article_evidence") or [])
    return " ".join(parts)


def _narrative_tokens(text: str) -> list[tuple[bool, str]]:
    """Yield (sentence_initial, token) for words that carry a figure or a name."""
    tokens = []
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        for position, word in enumerate(sentence.split()):
            for part in re.split(r"[-/–—]", word):
                part = part.strip("\"“”‘’'()[],;:.!?")
                part = re.sub(r"(?:'s|’s|'|’)$", "", part)
                if part:
                    tokens.append((position == 0, part))
    return tokens


def _application_vocabulary() -> set[str]:
    owned = [label for label, *_ in CONTROLS.values()]
    owned += [owner for owner, *_ in CONTROL_REVIEWS.values()]
    owned += list(REFERENCE_CONTROLS.values())
    return {token for text in owned for _initial, token in _narrative_tokens(text)}


APPLICATION_VOCABULARY = _application_vocabulary()


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _repeats_excerpt(text: str, excerpts: list[str]) -> bool:
    words = _words(text)
    runs = {
        tuple(words[index : index + EXCERPT_RUN_WORDS])
        for index in range(len(words) - EXCERPT_RUN_WORDS + 1)
    }
    for excerpt in excerpts:
        quoted = _words(excerpt)
        for index in range(len(quoted) - EXCERPT_RUN_WORDS + 1):
            if tuple(quoted[index : index + EXCERPT_RUN_WORDS]) in runs:
                return True
    return False


def _narrative_problem(
    text: str, corpus: str, excerpts: list[str], *, sentence_start: bool = True
) -> str | None:
    """Return why narrative text is not grounded in its cited sources, or None.

    A capitalized word that opens a sentence is usually an ordinary word, so it is
    exempt from the name check unless it is an acronym or carries a figure. Text
    that continues a sentence, such as a headline after its focus, has no such
    opening word and is checked in full.
    """
    if any(character in NARRATIVE_MARKUP for character in text) or re.search(
        r"https?:|www\.", text, re.I
    ):
        return "narrative must be plain text without markup or links"
    if re.search(r"\bCVE-\d{4}-\d+\b", text, re.I) or re.search(r"\bCVSS\b", text, re.I):
        return "narrative names a vulnerability identifier or severity score; keep those in the quoted evidence"
    if re.search(r"\b(?:you|your|yours|yourself)\b", text, re.I):
        return (
            "narrative addresses the reader; describe owners and organizations in the third person"
        )
    for pattern in NARRATIVE_OBLIGATIONS:
        if pattern.search(text) and not pattern.search(corpus):
            return "narrative uses obligation or penalty language that its cited sources do not use"
    for initial, token in _narrative_tokens(text):
        figure = any(character.isdigit() for character in token)
        acronym = sum(character.isupper() for character in token) >= 2
        name = token[0].isupper()
        exempt = initial and sentence_start and not (figure or acronym)
        if not (figure or acronym or name) or exempt:
            continue
        if token in APPLICATION_VOCABULARY or _contains_complete_phrase(corpus, token):
            continue
        if figure:
            return "narrative contains a figure absent from its cited sources"
        return "narrative names an entity absent from its cited sources"
    if _repeats_excerpt(text, excerpts):
        return "narrative repeats quoted evidence; analysis must add interpretation, not restate the excerpt"
    return None


def _bounded_text(value: Any, words: tuple[int, int], characters: int) -> str | None:
    if (
        not isinstance(value, str)
        or value != value.strip()
        or any(character in value for character in "\r\n")
        or len(value) > characters
        or not words[0] <= len(value.split()) <= words[1]
    ):
        return f"must be one line of {words[0]} to {words[1]} words and at most {characters} characters"
    return None


def _validate_narrative(plan: dict[str, Any], sources: list[dict[str, Any]]) -> None:
    """Hold model-written narrative to the evidence it cites (contract version 6)."""
    findings = plan["control_implications"]
    covered = {row["source_ids"][0] for row in findings}
    covered.update(row["source_id"] for row in plan["regulatory_changes"])
    excerpts = [row["evidence_excerpt"] for row in findings]
    excerpts += [row["evidence_excerpt"] for row in plan["regulatory_changes"]]
    brief = plan["executive_brief"]
    try:
        _object(brief, {"paragraphs"})
        paragraphs = _list(brief["paragraphs"], 2)
        if not paragraphs:
            raise ValueError
    except ValueError as error:
        raise ReportQualityError(
            "executive_brief: requires one or two narrative paragraphs"
        ) from error
    seen_text = set()
    for index, paragraph in enumerate(paragraphs):
        field = f"executive_brief.paragraphs[{index}]"
        try:
            paragraph = _object(paragraph, {"text", "source_ids"})
            _source_ids(paragraph["source_ids"], sources)
        except ValueError as error:
            raise ReportQualityError(
                f"{field}: requires text and one or more unique listed source IDs"
            ) from error
        if not set(paragraph["source_ids"]) <= covered:
            raise ReportQualityError(
                f"{field}: cites a source without a supported finding or regulatory change"
            )
        problem = _bounded_text(paragraph["text"], (25, 120), 900)
        if problem is None and not paragraph["text"].endswith("."):
            problem = "must end as a complete sentence"
        if problem is None and paragraph["text"] in seen_text:
            problem = "repeats another paragraph"
        if problem is None:
            problem = _narrative_problem(
                paragraph["text"], _source_corpus(sources, paragraph["source_ids"]), excerpts
            )
        if problem:
            raise ReportQualityError(f"{field}: {problem}")
        seen_text.add(paragraph["text"])
    for index, row in enumerate(findings):
        corpus = _source_corpus(sources, row["source_ids"])
        headline = row["headline"]
        field = f"control_implications[{index}].headline"
        problem = _bounded_text(headline, (4, 16), 110)
        if problem is None and not headline.startswith(row["focus"] + " "):
            problem = "must begin with its finding focus followed by what happened"
        if problem is None and headline[-1] in ".!?;:,":
            problem = "must not end with punctuation"
        if problem is None:
            # The focus is already verified verbatim against its excerpt.
            problem = _narrative_problem(
                headline[len(row["focus"]) :], corpus, [], sentence_start=False
            )
        if problem:
            raise ReportQualityError(f"{field}: {problem}")
        field = f"control_implications[{index}].significance"
        significance = row["significance"]
        problem = _bounded_text(significance, (15, 70), 480)
        if problem is None and (
            not significance.endswith(".") or len(re.split(r"(?<=[.!?])\s+", significance)) > 3
        ):
            problem = "must be one to three complete sentences"
        if problem is None:
            problem = _narrative_problem(significance, corpus, excerpts)
        if problem:
            raise ReportQualityError(f"{field}: {problem}")


class ReportQualityError(ValueError):
    """An actionable editorial-contract refusal, distinct from provider failure."""


def report_plan_response_format() -> dict[str, Any]:
    """Provider schema for current selections; host grounding remains mandatory."""

    def obj(properties):
        return {
            "type": "object",
            "properties": properties,
            "required": list(properties),
            "additionalProperties": False,
        }

    source_id = {"type": "integer", "minimum": 1, "maximum": 12}
    text = {"type": "string"}
    schema = obj(
        {
            "regulatory_changes": {
                "type": "array",
                "maxItems": 12,
                "items": obj(
                    {
                        "source_id": source_id,
                        "change": text,
                        "jurisdiction": text,
                        "evidence_excerpt": text,
                    }
                ),
            },
            "control_implications": {
                "type": "array",
                "maxItems": 6,
                "items": obj(
                    {
                        "control_id": {"type": "string", "enum": list(CONTROLS)},
                        "priority": {"type": "string", "enum": list(PRIORITIES)},
                        "source_ids": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 1,
                            "items": source_id,
                        },
                        "focus": text,
                        "evidence_excerpt": text,
                        "evidence_origin": {"type": "string", "enum": ["summary", "content"]},
                        "headline": text,
                        "significance": text,
                    }
                ),
            },
            "industry_impacts": {
                "type": "array",
                "maxItems": 0,
                "items": obj(
                    {
                        "sector_id": {"type": "string", "enum": list(SECTORS)},
                        "source_ids": {"type": "array", "items": source_id},
                    }
                ),
            },
            "executive_brief": obj(
                {
                    "paragraphs": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 2,
                        "items": obj(
                            {
                                "text": text,
                                "source_ids": {
                                    "type": "array",
                                    "minItems": 1,
                                    "maxItems": 6,
                                    "items": source_id,
                                },
                            }
                        ),
                    },
                }
            ),
        }
    )
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "grc_report_plan",
            "strict": True,
            "schema": schema,
        },
    }


def _validate_executive_brief(plan: dict[str, Any], sources: list[dict[str, Any]]) -> None:
    try:
        brief = _object(plan.get("executive_brief"), {"decision_frame", "source_ids"})
        _choice(brief["decision_frame"], DECISION_FRAMES)
        _list(brief["source_ids"], 3)
        _source_ids(brief["source_ids"], sources)
    except ValueError as error:
        raise ReportQualityError(
            "executive brief requires a supported decision frame and one to three unique lead sources"
        ) from error
    findings = {row["source_ids"][0]: row for row in plan["control_implications"]}
    regulatory_ids = {row["source_id"] for row in plan["regulatory_changes"]}
    ids = set(brief["source_ids"])
    if not ids <= findings.keys() | regulatory_ids:
        raise ReportQualityError("executive brief references a source without a supported finding")
    frame = brief["decision_frame"]
    if frame == "regulatory":
        compatible = ids <= regulatory_ids
    elif frame == "separate":
        families = {
            (
                next(
                    name
                    for name, spec in DECISION_FRAMES.items()
                    if name != "separate" and findings[index]["control_id"] in spec["controls"]
                )
                if index in findings
                else "regulatory"
            )
            for index in ids
        }
        compatible = len(families) >= 2
    else:
        compatible = all(
            index in findings
            and findings[index]["control_id"] in DECISION_FRAMES[frame]["controls"]
            for index in ids
        )
    if not compatible:
        raise ReportQualityError(
            "executive decision frame is not supported by its selected findings"
        )
    if plan["industry_impacts"]:
        raise ReportQualityError(
            "sector labels do not establish sector-specific consequences; omit industry mappings"
        )


def _executive_narrative(plan: dict[str, Any], sources: list[dict[str, Any]], citations) -> str:
    brief = plan["executive_brief"]
    frame = DECISION_FRAMES[brief["decision_frame"]]
    findings = {row["source_ids"][0]: row for row in plan["control_implications"]}
    regulatory = {row["source_id"]: row for row in plan["regulatory_changes"]}
    leads, steps = [], []
    for index in brief["source_ids"]:
        row = findings.get(index) if brief["decision_frame"] != "regulatory" else None
        focus = row["focus"] if row else regulatory[index]["change"]
        leads.append(f"“{_quoted_text(focus)}” {citations([index])}")
        step = (
            CONTROL_DECISIONS[row["control_id"]][0]
            if row
            else "verify jurisdiction and organizational applicability with the regulatory owner"
        )
        if step not in steps:
            steps.append(step)
    agenda = (
        f"The next step is to {steps[0]}."
        if len(steps) == 1
        else " ".join(
            f"{('First', 'Next', 'Then')[index]}, {step}." for index, step in enumerate(steps)
        )
    )
    lead_text = (
        leads[0]
        if len(leads) == 1
        else (
            " and ".join(leads) if len(leads) == 2 else ", ".join(leads[:-1]) + ", and " + leads[-1]
        )
    )
    scope = (
        "No primary-source regulatory change is established by this selection. "
        if not regulatory
        else "Regulatory applicability still requires an assessment of the cited primary material. "
    )
    truncated = any(
        "…" in row["evidence_excerpt"] or "..." in row["evidence_excerpt"]
        for row in plan["control_implications"]
    )
    watch = (
        "Some retained passages are truncated; consult the complete source before making a final decision. "
        if truncated
        else "The supplied evidence does not establish your organization's exposure or control effectiveness. "
    )
    return (
        f"{frame['judgment']} {frame['purpose']} "
        + lead_text
        + ". Use that assessment to decide where control evidence is sufficient and where an owner needs to investigate.\n\n"
        + agenda
        + " These are proposed review priorities: confirm local applicability before assigning work. "
        "In each case, record the applicability decision and the evidence supporting the next step.\n\n"
        + watch
        + scope
        + "Revise the agenda if the relevant product, activity or dependency is absent, or if stronger evidence changes the assessment."
    )


def _quoted_text(value: str) -> str:
    """Render untrusted quoted evidence as text, never Markdown or HTML commands."""
    # Numeric character references survive Markdown as literal text. Encode '&'
    # too, so a source's existing entity is displayed verbatim, not decoded twice.
    reserved = set("&<>\\[]()|*_`#!@%")
    return "".join(
        f"&#{ord(character)};" if character in reserved else character for character in value
    )


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
    origin = row["evidence_origin"]
    segments = article_segments(source)
    if not isinstance(origin, str) or origin not in segments:
        raise ValueError("finding requires a retained article evidence origin")
    if excerpt not in segments[origin] or not _contains_complete_phrase(segments[origin], excerpt):
        raise ValueError(
            "evidence_excerpt: finding excerpt must match its selected article evidence segment exactly"
        )
    if focus not in excerpt or not _contains_complete_phrase(excerpt, focus):
        raise ValueError("focus: finding focus must match the selected excerpt exactly")
    if not has_non_headline_text(excerpt, str(source.get("title", ""))):
        raise ValueError(
            "finding requires non-headline article evidence; a source title alone is insufficient"
        )


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
    if type(contract_version) is not int or contract_version not in {3, 4, 5, 6}:
        raise ValueError("unsupported report plan contract version")
    keys = {"regulatory_changes", "control_implications", "industry_impacts"}
    if contract_version >= 5:
        if not isinstance(value, dict) or "executive_brief" not in value:
            raise ReportQualityError(
                "report plan executive brief is required for a new publication"
            )
        keys.add("executive_brief")
    plan = _object(value, keys)
    if not 1 <= len(sources) <= 12:
        raise ValueError("report plan requires one to twelve retained sources")
    if contract_version >= 4:
        for source in sources:
            article_segments(source)
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
            keys = keys | {"focus", "evidence_excerpt", "evidence_origin"}
            if contract_version >= 6:
                keys = keys | {"headline", "significance"}
        for index, row in enumerate(_list(plan[collection], 6 if findings else len(catalog))):
            row = _object(row, keys)
            _choice(row[identity], catalog)
            _source_ids(row["source_ids"], sources)
            selection = row["source_ids"][0] if findings else row[identity]
            if selection in seen:
                raise ValueError("report plan repeats a catalog selection or finding source")
            seen.add(selection)
            if findings:
                try:
                    _validate_finding(row, sources)
                except ValueError as error:
                    # Keep diagnostic identity application-owned. Never echo an
                    # untrusted origin, candidate passage or source text in logs.
                    origin = row["evidence_origin"]
                    safe_origin = origin if origin in ("summary", "content") else "unsupported"
                    raise ReportQualityError(
                        f"{collection}[{index}] source_id={row['source_ids'][0]} "
                        f"evidence_origin={safe_origin}: {error}"
                    ) from error
                if contract_version >= 5 and (
                    len(row["focus"]) > 80 or len(row["focus"].split()) > 8
                ):
                    raise ReportQualityError(
                        "finding focus must be a short review label: at most eight words and 80 characters"
                    )
                if contract_version >= 5 and row["focus"] == row["evidence_excerpt"]:
                    raise ReportQualityError(
                        "finding focus must be an identifying label shorter than its evidence passage"
                    )
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
    if contract_version == 5:
        _validate_executive_brief(plan, sources)
    elif contract_version >= 6:
        if plan["industry_impacts"]:
            raise ReportQualityError(
                "sector labels do not establish sector-specific consequences; omit industry mappings"
            )
        _validate_narrative(plan, sources)
    return plan


def _unique_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("report plan contains duplicate JSON fields")
        result[key] = value
    return result


def parse_report_plan(
    text: str,
    sources: list[dict[str, Any]],
    *,
    contract_version: int = REPORT_CONTRACT_VERSION,
) -> dict[str, Any]:
    if not isinstance(text, str) or len(text) > 65536:
        raise ValueError("report plan must be a bounded JSON object")
    plan = _validate_plan(
        json.loads(text, object_pairs_hook=_unique_fields), sources, contract_version
    )
    render_report_plan(plan, sources, contract_version=contract_version)
    return deepcopy(plan)


def _link(source: dict[str, Any]) -> str:
    label = str(source["title"])
    for character in ("\\", "[", "]", "(", ")", "|"):
        label = label.replace(character, "\\" + character)
    destination = quote(str(source["url"]), safe=":/?#[]@!$&*+,;=%")
    return f"[{label}]({destination})"


def report_finding_groups(plan: dict[str, Any]) -> list[list[dict[str, Any]]]:
    """Return validated findings in publication order, preserving grouped source identities."""
    brief = plan["executive_brief"]
    if "paragraphs" in brief:
        # Findings follow the order the narrative introduces them, then priority.
        lead_order = list(
            dict.fromkeys(index for row in brief["paragraphs"] for index in row["source_ids"])
        )
    else:
        lead_order = brief["source_ids"]
    ordered = sorted(
        plan["control_implications"],
        key=lambda row: (
            (
                lead_order.index(row["source_ids"][0])
                if row["source_ids"][0] in lead_order
                else len(lead_order)
            ),
            list(PRIORITIES).index(row["priority"]),
        ),
    )
    groups: dict[tuple, list[dict]] = {}
    for row in ordered:
        key = (
            row["focus"],
            row["evidence_excerpt"],
            row["control_id"],
            row["priority"],
        )
        groups.setdefault(key, []).append(row)
    return list(groups.values())


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
    if contract_version == 5:
        executive = _executive_narrative(plan, sources, citations)
        decisions = []
        shown_excerpts = {row["evidence_excerpt"] for row in plan["regulatory_changes"]}
        for group in report_finding_groups(plan):
            row = group[0]
            ids = [item["source_ids"][0] for item in group]
            control = row["control_id"]
            owner, _question, evidence = CONTROL_REVIEWS[control]
            _step, implication, trigger = CONTROL_DECISIONS[control]
            if row["evidence_excerpt"] in shown_excerpts:
                evidence_line = (
                    "See the sourced regulatory evidence above. "
                    if any(
                        item["evidence_excerpt"] == row["evidence_excerpt"]
                        for item in plan["regulatory_changes"]
                    )
                    else "See the source evidence already quoted above. "
                ) + citations(ids)
            else:
                evidence_line = f"**Source evidence:** “{_quoted_text(row['evidence_excerpt'])}” {citations(ids)}"
                shown_excerpts.add(row["evidence_excerpt"])
            decisions.append(
                f"### {_quoted_text(row['focus'])} — {CONTROLS[control][0]}\n\n"
                f"{evidence_line}\n\n"
                f"**Control decision (inference):** {implication}\n\n"
                f"**Inferred review priority:** {PRIORITIES[row['priority']]}. "
                f"**Owner:** {owner}. **Evidence to request:** {evidence}.\n\n"
                f"**Decision trigger:** {trigger}"
            )
        sections = (
            ("Executive Summary", executive),
            ("Sourced Regulatory Changes", regulatory),
            (
                "Evidence and Decisions",
                "\n\n".join(decisions)
                or "The sourced regulatory table is the evidence for the applicability decision above; no additional control findings were selected.",
            ),
            ("Source Highlights", "\n".join(highlights)),
        )
    if contract_version >= 6:
        sections = _narrative_sections(plan, sources, citations, regulatory, highlights)
    body = "\n\n".join(f"## {heading}\n\n{text}" for heading, text in sections)
    if contract_version >= 5:
        validate_editorial_quality(body, plan, sources)
    validate_regulatory_evidence(body, sources, contract_version=contract_version)
    return body


FINDING_LABELS = (
    "Review priority",
    "Why it matters",
    "Source evidence",
    "Evidence to request",
    "Decision trigger",
    "Reference controls",
)
EVIDENCE_NOTE = (
    "Each finding is analysis of the quoted evidence: why it matters for control assurance, "
    "who owns the review and what evidence settles it. Reference controls are review aids, "
    "not a compliance determination."
)


def _count(value: int, noun: str) -> str:
    return f"{value} {noun}" if value == 1 else f"{value} {noun}s"


def _narrative_sections(plan, sources, citations, regulatory, highlights):
    """Render contract version 6: model narrative inside one fixed finding template."""
    groups = report_finding_groups(plan)
    paragraphs = [
        f"{_quoted_text(row['text'])} {citations(row['source_ids'])}"
        for row in plan["executive_brief"]["paragraphs"]
    ]
    changes = len(plan["regulatory_changes"])
    paragraphs.append(
        f"Scope: {_count(len(groups), 'finding')} and "
        f"{_count(changes, 'sourced regulatory change')} from "
        f"{_count(len(sources), 'retained source')}. Review priorities rank what to check first; "
        "confirm whether each finding applies to your organization before assigning work."
    )
    decisions = []
    shown_excerpts = {row["evidence_excerpt"] for row in plan["regulatory_changes"]}
    for group in groups:
        row = group[0]
        ids = [item["source_ids"][0] for item in group]
        control = row["control_id"]
        owner, _question, evidence = CONTROL_REVIEWS[control]
        _step, _implication, trigger = CONTROL_DECISIONS[control]
        if row["evidence_excerpt"] in shown_excerpts:
            quoted = "See the sourced regulatory evidence above. " + citations(ids)
        else:
            quoted = f"“{_quoted_text(row['evidence_excerpt'])}” {citations(ids)}"
            shown_excerpts.add(row["evidence_excerpt"])
        values = (
            f"{PRIORITIES[row['priority']]} · {CONTROLS[control][0]} · Owner: {owner}",
            _quoted_text(row["significance"]),
            quoted,
            f"{evidence[0].upper()}{evidence[1:]}.",
            trigger,
            REFERENCE_CONTROLS[control],
        )
        decisions.append(
            f"### {_quoted_text(row['headline'])}\n\n"
            + "\n\n".join(f"**{label}:** {value}" for label, value in zip(FINDING_LABELS, values))
        )
    evidence_section = (
        "\n\n".join([EVIDENCE_NOTE, *decisions])
        if decisions
        else "The sourced regulatory table is the evidence for the applicability decision above; no additional control findings were selected."
    )
    return (
        ("Executive Summary", "\n\n".join(paragraphs)),
        ("Sourced Regulatory Changes", regulatory),
        ("Evidence and Decisions", evidence_section),
        ("Source Highlights", "\n".join(highlights)),
    )


def _editorial_content_roles(body: str, sources: list[dict]) -> tuple[list[str], str]:
    """Separate quotations, analysis and immutable identity before checking economy.

    Regulatory evidence has its own row validator. Citation labels and the source
    index identify evidence; they are not extra analysis. Only explicit quotation
    lines in Evidence and Decisions own a control finding's evidence passage.
    Whole-report recomposition independently enforces exact structure and links.
    """
    quotes, analysis = [], []
    section = ""
    for line in body.splitlines():
        if line.startswith("## "):
            section = line[3:]
            continue
        if section not in {"Executive Summary", "Evidence and Decisions"}:
            continue
        block = (
            re.fullmatch(r"\*\*Source evidence:\*\* “([^\n]*)” (\[.*)", line)
            if section == "Evidence and Decisions"
            else None
        )
        if block:
            quotes.append(block.group(1))
            continue
        for source in sources:
            line = line.replace(_link(source), "")
        analysis.append(line)
    return quotes, "\n".join(analysis)


def validate_editorial_quality(body: str, plan: dict, sources: list[dict]) -> None:
    """Check presentation roles separately from exact source grounding.

    This is a structural quality floor, not an oracle for semantic insight.
    Whole-report recomposition additionally excludes rephrased duplicate sections.
    """
    sections = re.findall(r"(?m)^## (.+)$", body)
    if sections != [
        "Executive Summary",
        "Sourced Regulatory Changes",
        "Evidence and Decisions",
        "Source Highlights",
    ]:
        raise ReportQualityError(
            "editorial sections must separate the brief, evidence and source provenance"
        )
    match = re.search(r"(?ms)^## Executive Summary\s*\n(.*?)(?=^## |\Z)", body)
    if match is None:
        raise ReportQualityError("editorial: executive narrative is missing")
    summary = match.group(1).strip()
    if (
        re.search(r"(?m)^\s*(?:[-*]|\d+[.)])\s", summary)
        or not 2 <= len(summary.split("\n\n")) <= 3
    ):
        raise ReportQualityError(
            "editorial: executive summary requires a connected narrative, not an excerpt list"
        )
    narrative = "paragraphs" in plan["executive_brief"]
    visible = re.sub(r"\[[^\]]+\]\([^\n]+?\)", "", summary)
    minimum, maximum = (40, 300) if narrative else (60, 260)
    if not minimum <= len(visible.split()) <= maximum:
        raise ReportQualityError(
            "editorial: executive summary must be concise without padding or an empty introduction"
        )
    if not re.search(r"\b(if|whether|applicability)\b", summary, re.I):
        raise ReportQualityError(
            "editorial: executive summary must state conditional applicability"
        )
    if narrative:
        written = summary.split("\n\n")
        for paragraph, row in zip(written, plan["executive_brief"]["paragraphs"]):
            if not all(_link(sources[index - 1]) in paragraph for index in row["source_ids"]):
                raise ReportQualityError(
                    "editorial: each narrative paragraph must retain its supporting source citations"
                )
        evidence = re.search(r"(?ms)^## Evidence and Decisions\s*\n(.*?)(?=^## |\Z)", body)
        blocks = re.split(r"(?m)^### ", evidence.group(1) if evidence else "")[1:]
        for block in blocks:
            lines = block.strip().split("\n\n")[1:]
            matches = [re.match(r"\*\*([^*]+):\*\* ", line) for line in lines]
            labels = tuple(match.group(1) if match else "" for match in matches)
            if labels != FINDING_LABELS:
                raise ReportQualityError(
                    "editorial: every finding must use the same fields in the same order"
                )
    else:
        for index in plan["executive_brief"]["source_ids"]:
            if _link(sources[index - 1]) not in summary:
                raise ReportQualityError(
                    "editorial: executive decision must retain its supporting source citation"
                )
    evidence_blocks, analysis_prose = _editorial_content_roles(body, sources)
    regulatory_excerpts = {row["evidence_excerpt"] for row in plan["regulatory_changes"]}
    for row in plan["control_implications"]:
        excerpt = _quoted_text(row["evidence_excerpt"])
        expected_blocks = 0 if row["evidence_excerpt"] in regulatory_excerpts else 1
        if excerpt in analysis_prose or evidence_blocks.count(excerpt) != expected_blocks:
            raise ReportQualityError(
                "editorial: source excerpts belong once in supporting findings, not repeated across sections"
            )


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
    if contract_version >= 5:
        try:
            validate_editorial_quality(body, plan, sources)
        except ReportQualityError as error:
            raise ReportQualityError(
                f"report content does not match the retained report plan: {error}"
            ) from error
    if body.strip() != expected:
        raise ValueError("report content does not match the retained report plan")
