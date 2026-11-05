"""Give selection-focused fixtures the narrative fields the current contract requires.

Tests that exercise evidence selection, grounding or publication plumbing do not
need bespoke prose. This adds plain, source-independent narrative that satisfies
the grounding rules so those tests keep pinning the behavior they were written for.
"""

from copy import deepcopy
from typing import Any

PARAGRAPH = (
    "This period brings findings that control owners should check against current "
    "assurance evidence. Each one describes conditions that need confirmation before a "
    "priority is adopted, and owners should record whether those conditions apply."
)
SIGNIFICANCE = (
    "This finding matters for control assurance because the quoted evidence describes "
    "conditions that owners need to check. The accountable owner should confirm whether "
    "those conditions apply."
)


def narrated(plan: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a selection fixture as a current-contract report plan."""
    plan = deepcopy(plan)
    for row in plan.get("control_implications", []):
        row.setdefault("headline", f"{row['focus']} requires control review")
        row.setdefault("significance", SIGNIFICANCE)
    brief = plan.get("executive_brief")
    if isinstance(brief, dict) and "paragraphs" not in brief:
        covered = [row["source_ids"][0] for row in plan.get("control_implications", [])]
        covered += [row["source_id"] for row in plan.get("regulatory_changes", [])]
        leads = [index for index in brief.get("source_ids", []) if index in covered]
        ids = list(dict.fromkeys(leads + covered))[:6]
        subject = {row["source_id"]: row["change"] for row in plan.get("regulatory_changes", [])}
        subject.update(
            {row["source_ids"][0]: row["focus"] for row in plan.get("control_implications", [])}
        )
        text = PARAGRAPH
        lead = subject.get(ids[0], "") if ids else ""
        if lead and not set(lead) & set("[]|*_`#<>\\{}~"):
            text = f"The leading item concerns {lead}. {PARAGRAPH}"
        plan["executive_brief"] = {"paragraphs": [{"text": text, "source_ids": ids}]}
    return plan
