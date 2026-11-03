# GRC Reports Archive

The public report archive is available at
[grcinsight.ricomanifesto.com/archive/](https://grcinsight.ricomanifesto.com/archive/).

Model-backed reports are preserved under
`site/archive/YYYY-MM-DDTHH-MM-SSZ/` by the report-publication workflow, so
same-day reruns keep distinct snapshots. The archive begins August 13, 2026;
earlier report commits remain in Git history but are not presented as a complete
public archive.

## Latest Report

The most current report is available at the
[GRCInsight reader](https://grcinsight.ricomanifesto.com/).

## Report History

`scripts/build_site.py --archive-current` snapshots the current Markdown and
rebuilds both the current pre-rendered page and the static archive. The generated
site artifacts are verified by `make check-site` before publication.
