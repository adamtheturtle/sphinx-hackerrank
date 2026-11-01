"""The HackerRank builder uses Sphinx's standard HTML rendering."""

import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest
from sphinx.testing.util import SphinxTestApp

from sphinx_hackerrank import GuidelineExport
from sphinx_hackerrank.html import render_fragment
from tests.builds import build_expected, write_sources


@pytest.mark.parametrize(
    argnames="source_url", argvalues=[None, "https://example.org/source/"]
)
@pytest.mark.parametrize(argnames="anchors", argvalues=[False, True])
def test_builder_matches_html_builder(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    source_url: str | None,
    anchors: bool,
) -> None:
    """Compare pages and exported fragments to a native HTML build."""
    docname = "topics/widgets-interviewer-guideline"
    classes = "hr-interviewer-guideline selected-guide"
    files = {
        "index.rst": textwrap.dedent(
            text="""\
            Index
            =====

            .. toctree::

               topics/widgets-interviewer-guideline
               topics/widgets
            """
        ),
        "topics/widgets.rst": "Widgets\n=======\n\nPart 1\n------\n",
        f"{docname}.rst": textwrap.dedent(
            text=f"""\
            Interviewer Guideline
            =====================

            .. container:: {classes}

               .. collapse:: Part 1

                  A participant\u2019s example.

                  `Guide <widgets.html#part-1>`_
                  `External <https://example.org>`_
                  `Local <#local>`_
                  `PDF <data.pdf>`_

                  .. code-block:: text
                     :linenos:
                     :caption: Example
                     :name: example-code

                     if x < 3 && y > 0:

            .. container:: other-guide

               Other language.
            """
        ),
    }
    expected = build_expected(
        make_app=make_app,
        source=tmp_path / "expected",
        files=files,
        confoverrides={"html_context": {"builder": "hackerrank"}},
        docnames=["index", "topics/widgets", docname],
    )
    source = tmp_path / "actual"
    write_sources(source=source, files=files)
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        exception_on_warning=True,
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
            "hackerrank_exports": [
                GuidelineExport(
                    docname=docname,
                    selector=".selected-guide",
                    output_path="interviewer-guidelines/topics/widgets/guide.html",
                    name="Example",
                )
            ],
            "hackerrank_source_url": source_url,
            "hackerrank_source_suffix": ".rst",
            "hackerrank_source_anchors": anchors,
        },
    )
    app.build()
    for name, html in expected.items():
        assert (Path(app.outdir) / f"{name}.html").read_text(
            encoding="utf-8"
        ) == html
    # Export the independently built native page through the same public API.
    assert (
        Path(app.outdir) / "interviewer-guidelines/topics/widgets/guide.html"
    ).read_text(encoding="utf-8") == render_fragment(
        html=expected[docname],
        selector=".selected-guide",
        output_path="interviewer-guidelines/topics/widgets/guide.html",
        docname=docname,
        source_url=source_url,
        source_suffix=".rst",
        source_anchors=anchors,
    )


@pytest.mark.parametrize(argnames="containers", argvalues=[0, 2])
def test_invalid_container(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    containers: int,
) -> None:
    """Reject RST without exactly one matching language container."""
    source = tmp_path / "source"
    write_sources(
        source=source,
        files={
            "index.rst": "Index\n=====\n",
            "index-interviewer-guideline.rst": (
                "Interviewer Guideline\n=====================\n\n"
                + textwrap.dedent(
                    text="""\
                    .. container:: selected-guide

                       Example.

                    """
                )
                * containers
            ),
        },
    )
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
            "suppress_warnings": ["toc.not_included"],
            "hackerrank_exports": [
                GuidelineExport(
                    docname="index-interviewer-guideline",
                    selector=".selected-guide",
                    output_path="interviewer-guidelines/example.html",
                    name="Example",
                )
            ],
        },
    )
    with pytest.raises(
        expected_exception=ValueError,
        match="Expected one Interviewer Guideline",
    ):
        app.build()
