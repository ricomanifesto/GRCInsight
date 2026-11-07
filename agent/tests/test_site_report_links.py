"""The site report checker's link scanner keeps its character-by-character contract."""

from pathlib import Path
import random
import runpy

REPO_ROOT = Path(__file__).resolve().parents[2]


def checker_links():
    return runpy.run_path(str(REPO_ROOT / "scripts" / "check_site_report.py"))["markdown_links"]


def reference_links(markdown: str) -> list[tuple[int, int, str, str]]:
    """Original per-character scanner, kept as the behavioral reference."""

    def closing(start: int, opener: str, closer: str) -> int:
        depth, escaped = 1, False
        for index in range(start, len(markdown)):
            character = markdown[index]
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == opener:
                depth += 1
            elif character == closer:
                depth -= 1
                if depth == 0:
                    return index
        return -1

    links = []
    cursor = 0
    while cursor < len(markdown):
        label_start = markdown.find("[", cursor)
        if label_start < 0:
            break
        label_end = closing(label_start + 1, "[", "]")
        if label_end < 0:
            break
        if label_end + 1 >= len(markdown) or markdown[label_end + 1] != "(":
            cursor = label_start + 1
            continue
        destination_end = closing(label_end + 2, "(", ")")
        if destination_end < 0:
            cursor = label_end + 2
            continue
        links.append(
            (
                label_start,
                destination_end + 1,
                markdown[label_start + 1 : label_end],
                markdown[label_end + 2 : destination_end],
            )
        )
        cursor = destination_end + 1
    return links


def test_link_scanner_handles_nesting_and_escapes():
    markdown_links = checker_links()
    text = r"See [a [nested] \] label](https://x.test/a_(b)\)c) and [plain](/p) [no link] [x](open"
    assert markdown_links(text) == reference_links(text)
    assert [link[2:] for link in markdown_links(text)] == [
        (r"a [nested] \] label", r"https://x.test/a_(b)\)c"),
        ("plain", "/p"),
    ]


def test_link_scanner_matches_reference_on_generated_syntax():
    markdown_links = checker_links()
    rng = random.Random(20261107)
    for _ in range(20000):
        text = "".join(rng.choice("[]()\\ab\n") for _ in range(rng.randint(0, 24)))
        assert markdown_links(text) == reference_links(text), repr(text)


def test_link_scanner_matches_reference_on_published_reports():
    markdown_links = checker_links()
    site = REPO_ROOT / "site"
    for report in [site / "index.md", *sorted(site.glob("archive/*/report.md"))]:
        markdown = report.read_text(encoding="utf-8")
        assert markdown_links(markdown) == reference_links(markdown), report.name
