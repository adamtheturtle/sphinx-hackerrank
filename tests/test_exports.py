"""Export boundaries own metadata independently of question mappings."""

from collections.abc import Callable
from pathlib import Path

import pytest
from docutils import nodes
from sphinx.errors import SphinxWarning
from sphinx.testing.util import SphinxTestApp

from sphinx_hackerrank import GuidelineExportNode
from sphinx_hackerrank.exports import Export, ExportInventory, HackerRankDomain
from tests.builds import write_sources


@pytest.mark.parametrize(
    argnames=("field", "value", "message"),
    argvalues=[
        ("name", "", "must not be empty"),
        ("output_path", " ", "must not be empty"),
        ("output_path", "../guide.html", "inside"),
        ("output_path", "/outside.html", "inside"),
        ("output_path", "C:/outside.html", "inside"),
        ("output_path", "a\\b.html", "inside"),
        ("output_path", "output.txt", "HTML file"),
    ],
)
def test_invalid_export(*, field: str, value: str, message: str) -> None:
    """Reject incomplete requests and unsafe output destinations."""
    fields = {"output_path": "exports/guide.html", "name": "Review"}
    fields[field] = value
    with pytest.raises(expected_exception=ValueError, match=message):
        _ = GuidelineExportNode(**fields)


def test_node_copies_preserve_metadata() -> None:
    """Docutils deep copies retain content and export metadata."""
    node = GuidelineExportNode(
        nodes.paragraph("", "Review content"),
        rawsource="source",
        output_path="./exports/guide.html",
        name="Review",
    )
    assert node.copy().export == node.export
    copied = node.deepcopy()
    assert copied.export == Export(
        output_path="exports/guide.html", name="Review"
    )
    assert copied.astext() == "Review content"
    assert copied["classes"] == ["hr-interviewer-guideline"]


@pytest.mark.parametrize(
    argnames=("destination", "duplicate", "message"),
    argvalues=[
        ("index.html", False, "overlaps"),
        ("./other.html", False, "overlaps"),
        ("interviewer-guidelines/index.html", False, "overlaps"),
        ("genindex.html", False, "overlaps"),
        ("search.html", False, "overlaps"),
        ("exports/review.html", True, "Duplicate export"),
    ],
)
def test_destination_collisions(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    destination: str,
    duplicate: bool,
    message: str,
) -> None:
    """Validate all document boundaries before writing any output."""
    source = tmp_path / "source"
    declaration = (
        f".. hackerrank-export:: {destination}\n"
        "   :name: Review\n\n   Example.\n"
    )
    write_sources(
        source=source,
        files={
            "index.rst": "Index\n=====\n\n.. toctree::\n\n   other\n\n"
            + declaration,
            "other.rst": "Other\n=====\n\n"
            + (declaration if duplicate else "Other content.\n"),
        },
    )
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        confoverrides={"extensions": ["sphinx_hackerrank"]},
    )
    with pytest.raises(expected_exception=ValueError, match=message):
        app.build()
    assert not (Path(app.outdir) / "exports/review.html").exists()


def test_invalid_directive(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Report malformed RST exports at their source location."""
    source = tmp_path / "source"
    write_sources(
        source=source,
        files={
            "index.rst": (
                "Index\n=====\n\n.. hackerrank-export:: exports/review.html\n"
                "\n   Example.\n"
            )
        },
    )
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        exception_on_warning=True,
        confoverrides={"extensions": ["sphinx_hackerrank"]},
    )
    with pytest.raises(
        expected_exception=SphinxWarning, match="must not be empty"
    ):
        app.build()


@pytest.mark.parametrize(argnames="builder", argvalues=["html", "hackerrank"])
def test_multiple_boundaries(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    builder: str,
) -> None:
    """Identically styled boundaries export independently without
    selectors.
    """
    source = tmp_path / "source"
    write_sources(
        source=source,
        files={
            "index.rst": (
                "Index\n=====\n\nOutside export.\n\n"
                ".. hackerrank-export:: exports/first.html\n"
                "   :name: First\n\n   First content.\n\n"
                ".. hackerrank-export:: exports/second.html\n"
                "   :name: Second\n\n   Second content.\n"
            )
        },
    )
    app = make_app(
        srcdir=source,
        buildername=builder,
        exception_on_warning=True,
        confoverrides={"extensions": ["sphinx_hackerrank"]},
    )
    app.build()
    output = Path(app.outdir)
    page = (output / "index.html").read_text()
    assert "First content" in page
    assert "Second content" in page
    if builder == "hackerrank":
        first = (output / "exports/first.html").read_text()
        assert "First content" in first
        assert "Second content" not in first
        assert "Outside export" not in first
        second = (output / "exports/second.html").read_text()
        assert "Second content" in second
        assert "First content" not in second
    else:
        assert not (output / "exports").exists()


def test_exports_refresh_incremental_outputs(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Source changes and missing outputs refresh persisted
    inventories.
    """
    source = tmp_path / "source"
    write_sources(
        source=source,
        files={
            "index.rst": (
                "Index\n=====\n\n.. hackerrank-export:: exports/review.html\n"
                "   :name: First review\n\n   First text.\n"
            )
        },
    )
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        exception_on_warning=True,
        confoverrides={"extensions": ["sphinx_hackerrank"]},
    )
    app.build()
    output = Path(app.outdir) / "exports/review.html"
    original_time = output.stat().st_mtime_ns
    assert "First text" in output.read_text()
    app.build()
    assert output.stat().st_mtime_ns == original_time
    recipe = source / "index.rst"
    _ = recipe.write_text(data=recipe.read_text().replace("First", "Second"))
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
    _ = recipe.write_text(data="Index\n=====\n\nNo exports.\n")
    app.build()
    assert "Second review" not in index.read_text()


def test_parallel_inventory_merging(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Parallel readers merge only their assigned documents."""
    source = tmp_path / "source"
    write_sources(source=source, files={"index.rst": "Index\n=====\n"})
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        confoverrides={"extensions": ["sphinx_hackerrank"]},
    )
    domain = app.env.get_domain(domainname="hackerrank")
    assert isinstance(domain, HackerRankDomain)
    export = Export(output_path="exports/review.html", name="Review")
    domain.merge_domaindata(
        docnames={"other", "missing"},
        otherdata={
            "exports": ExportInventory(
                {"other": [export], "unrelated": [export]}
            )
        },
    )
    assert domain.exports == {"other": [export]}
    domain.clear_doc(docname="other")
    domain.clear_doc(docname="missing")
    assert domain.exports == {}
