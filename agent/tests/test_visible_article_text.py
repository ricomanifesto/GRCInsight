"""Adversarial cases for the single ingestion/publication text boundary."""

from copy import deepcopy
from html import escape
import json

import pytest

from core.article_evidence import article_segments, eligible_article_segments
from core.report_plan import parse_report_plan
from test_article_evidence import TITLE, DETAIL, plan, source


@pytest.mark.parametrize(
    "raw",
    [
        TITLE,
        TITLE + ".",
        TITLE.replace(":", ""),
        (TITLE + " ") * 3,
        f"<p>{TITLE}</p>",
        f"<p>{TITLE}</p><p>{TITLE}</p>",
        escape(f"<p>{TITLE}</p>"),
        escape(escape(f"<p>{TITLE}</p>")),
        f'<a href="https://example.com/new-words" title="new evidence">{TITLE}</a>',
        f"{TITLE}<!-- new evidence -->",
        f"{TITLE}<script>new evidence</script>",
        f"{TITLE}<style>.x{{display:none}}</style>",
        f"{TITLE}<template>new evidence</template>",
        f"{TITLE}<span hidden>new evidence</span>",
        f'{TITLE}<span aria-hidden="true">new evidence</span>',
        f'{TITLE}<span style="display:none">new evidence</span>',
        f'{TITLE}<span class="hidden">new evidence</span>',
        f'{TITLE}<span id="hidden">new evidence</span>',
        TITLE.replace("gateway", "gate<b>way</b>"),
        TITLE.replace("gateway", "gate way"),
        TITLE.replace("gateway", "gate-way"),
        TITLE.replace("gateway", "gate\u200bway"),
        f"{TITLE}<span hidden/>new evidence",
        f"<p>{TITLE}<div>ambiguous extra words</p>",
        f"{TITLE}<custom-element>new evidence</custom-element>",
    ],
)
def test_non_article_content_cannot_supply_finding_evidence(raw):
    item = source(summary=raw)
    assert eligible_article_segments(item) == {}
    for text in article_segments(item).values():
        with pytest.raises(ValueError):
            parse_report_plan(json.dumps(plan(text)), [item])


def test_receipt_retains_raw_origin_and_deterministic_extraction_version():
    raw = f"<p>{TITLE}</p><p>The affected <b>gateway</b> requires an administrator session &amp; a valid token.</p>"
    expected = TITLE + " The affected gateway requires an administrator session & a valid token."
    item = source(summary=raw)
    receipt = item["article_evidence"][0]
    assert receipt == {
        "origin": "summary",
        "extraction_version": 1,
        "raw_text": raw,
        "text": expected,
    }
    assert article_segments(item) == {"summary": expected}
    assert parse_report_plan(json.dumps(plan(expected)), [item]) == plan(expected)


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r.pop("raw_text"),
        lambda r: r.pop("extraction_version"),
        lambda r: r.update(extraction_version=2),
        lambda r: r.update(extraction_version=True),
        lambda r: r.update(raw_text=TITLE),
        lambda r: r.update(
            text="Invented additional evidence from an unsupported publisher statement."
        ),
    ],
)
def test_receipts_are_rederived_not_trusted(change):
    item = source()
    change(item["article_evidence"][0])
    with pytest.raises(ValueError, match="article evidence"):
        article_segments(item)


def test_headline_identity_is_preserved_but_compared_as_extracted_text():
    item = source(title=escape(f"<b>{TITLE}</b>"), summary=TITLE)
    assert item["title"] == escape(f"<b>{TITLE}</b>")
    assert eligible_article_segments(item) == {}


def test_hidden_subtree_never_contributes_to_a_valid_quote():
    raw = f"<p>{DETAIL}</p><div hidden><b>invented assertions</b></div>"
    item = source(summary=raw)
    assert article_segments(item) == {"summary": DETAIL}
    assert parse_report_plan(json.dumps(plan()), [item]) == plan()


def test_input_byte_bound_fails_closed_and_output_truncation_preserves_words():
    assert source(summary="x" * 4097)["article_evidence"] == []
    assert source(summary="é" * 2049)["article_evidence"] == []
    item = source(summary=f"<p>{(DETAIL + ' ') * 15}</p>")
    text = article_segments(item)["summary"]
    assert len(text) <= 700
    assert text.split()[-1] in DETAIL.split()
    assert parse_report_plan(json.dumps(plan(text)), [item]) == plan(text)


def test_prompt_and_plan_use_the_same_extracted_text():
    from services.model_service import GRCModelService

    item = source(summary=f"<p>{DETAIL}</p>")
    service = GRCModelService.__new__(GRCModelService)
    prompt = service._create_report_prompt({"source_evidence": [item]}, {})
    line = next(x for x in prompt.splitlines() if "Eligible article evidence segments:" in x)
    assert json.loads(line.split("segments: ")[1]) == {"summary": DETAIL}
    assert parse_report_plan(json.dumps(plan()), [item]) == plan()
    broken = deepcopy(item)
    broken["article_evidence"][0]["raw_text"] = TITLE
    with pytest.raises(ValueError, match="article evidence"):
        parse_report_plan(json.dumps(plan()), [broken])
