"""Export requests are explicit and independent of question metadata."""

from collections.abc import Callable
from pathlib import Path

import pytest
from sphinx.testing.util import SphinxTestApp

from sphinx_hackerrank import GuidelineExport
from sphinx_hackerrank.exports import group_exports
from tests.builds import write_sources


@pytest.mark.parametrize(
    argnames=("field", "value", "message"),
    argvalues=[
        ("name", "", "must not be empty"),
        ("docname", "../guide", "inside"),
        ("output_path", "/outside.html", "inside"),
        ("output_path", "C:/outside.html", "inside"),
        ("output_path", "./guide.html", "overlaps"),
        ("output_path", "a\\b.html", "inside"),
        ("output_path", "output.txt", "HTML file"),
        ("output_path", "guide.html", "overlaps"),
        ("output_path", "interviewer-guidelines/index.html", "overlaps"),
    ],
)
def test_invalid_export(*, field: str, value: str, message: str) -> None:
    """Reject incomplete requests and unsafe output destinations."""
    fields = {
        "docname": "guide",
        "selector": ".guide",
        "output_path": "exports/guide.html",
        "name": "Review",
    }
    fields[field] = value
    with pytest.raises(expected_exception=ValueError, match=message):
        _ = GuidelineExport(**fields)


def test_sources_and_duplicate_destinations(*, tmp_path: Path) -> None:
    """Validate documents and destinations before writing output."""
    export = GuidelineExport(
        docname="guide",
        selector=".guide",
        output_path="exports/guide.html",
        name="Review",
    )
    with pytest.raises(expected_exception=ValueError, match="Missing RST"):
        _ = group_exports(source_dir=tmp_path, exports=[export])
    _ = (tmp_path / "guide.rst").write_text(data="Guide\n=====\n")
    assert group_exports(source_dir=tmp_path, exports=[export]) == {
        "guide": [export]
    }
    with pytest.raises(
        expected_exception=ValueError, match="Duplicate export"
    ):
        _ = group_exports(source_dir=tmp_path, exports=[export, export])


def test_export_requests_refresh_incremental_outputs(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Export changes and missing outputs refresh incremental builds."""
    source = tmp_path / "source"
    write_sources(
        source=source,
        files={
            "index.rst": (
                "Index\n=====\n\n"
                ".. container:: hr-interviewer-guideline first\n\n"
                "   First text.\n\n"
                ".. container:: hr-interviewer-guideline second\n\n"
                "   Second text.\n"
            )
        },
    )
    first = GuidelineExport(
        docname="index",
        selector=".first",
        output_path="exports/review.html",
        name="First review",
    )
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        exception_on_warning=True,
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
            "hackerrank_exports": [first],
        },
    )
    app.build()
    output = Path(app.outdir) / first.output_path
    original_time = output.stat().st_mtime_ns
    assert "First text" in output.read_text()
    app.build()
    assert output.stat().st_mtime_ns == original_time
    app.config.hackerrank_exports = [
        GuidelineExport(
            docname="index",
            selector=".second",
            output_path=first.output_path,
            name="Second review",
        )
    ]
    app.build()
    assert "Second text" in output.read_text()
    assert "First text" not in output.read_text()
    index = Path(app.outdir) / "interviewer-guidelines/index.html"
    assert 'href="../exports/review.html"' in index.read_text()
    assert "Second review" in index.read_text()
    output.unlink()
    index.unlink()
    app.build()
    assert "Second text" in output.read_text()
    assert index.is_file()
