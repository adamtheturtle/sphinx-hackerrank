"""Generated guides reuse native sections and caller-selected inputs."""

import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest
from sphinx.testing.util import SphinxTestApp

from tests.builds import build_expected, write_sources

_SECTION_SOURCE = textwrap.dedent(
    text="""\
    Guide
    =====

    Q1
    --

    .. _stable-prompt:

    Prompt
    ~~~~~~

    First prompt.

    .. _extra-target:

    See Details_.

    Details
    ^^^^^^^

    Nested details.

    FAQ
    ~~~

    First FAQ.

    Q2
    --

    Prompt
    ~~~~~~

    Second prompt.
    """
)


@pytest.mark.parametrize(
    argnames="selector", argvalues=["Q1 / Prompt", "#stable-prompt"]
)
@pytest.mark.parametrize(argnames="include_heading", argvalues=[False, True])
@pytest.mark.parametrize(argnames="separate_details", argvalues=[False, True])
def test_recipe_selections_match_native_rst(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    selector: str,
    include_heading: bool,
    separate_details: bool,
) -> None:
    """Paths, labels, and automatic exclusions match native RST output."""
    index = (
        "Index\n=====\n\n.. toctree::\n\n"
        "   guide\n   view-interviewer-guideline\n"
    )
    body = "First prompt.\n\nSee `Details <guide.html#details>`_.\n"
    if include_heading:
        body = ".. rubric:: Prompt\n\n" + body
    if not separate_details:
        body += "\n.. rubric:: Details\n\nNested details.\n"
    native = (
        "Guide: HackerRank Interviewer Guidelines\n"
        "========================================\n\n"
        ".. container:: hr-interviewer-guideline "
        "\n\n"
        "   .. rubric:: Guide\n\n"
        "   .. collapse:: Q1\n\n"
        "      .. collapse:: Work\n\n"
        + textwrap.indent(text=body, prefix="         ")
    )
    recipe = (
        ".. interviewer-guideline:: guide.rst\n\n"
        "   .. guideline-part:: Q1\n\n"
        "      .. guideline-group:: Work\n\n"
        f"         .. guideline-select:: {selector}\n"
    )
    if include_heading:
        recipe += "            :include-heading:\n"
    if separate_details:
        recipe += (
            "\n      .. guideline-group:: Details\n\n"
            "         .. guideline-select:: Prompt / Details\n"
        )
        native += "\n      .. collapse:: Details\n\n         Nested details.\n"
    files = {
        "index.rst": index,
        "guide.rst": _SECTION_SOURCE,
        "view-interviewer-guideline.rst": native,
    }
    expected = build_expected(
        make_app=make_app,
        source=tmp_path / "expected",
        files=files,
        confoverrides={},
        docnames=["index", "guide", "view-interviewer-guideline"],
    )
    files["view-interviewer-guideline.rst"] = recipe
    source = tmp_path / "actual"
    write_sources(source=source, files=files)
    app = make_app(
        srcdir=source,
        exception_on_warning=True,
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
        },
    )
    app.build()
    for docname, html in expected.items():
        assert (Path(app.outdir) / f"{docname}.html").read_text(
            encoding="utf-8"
        ) == html


@pytest.mark.parametrize(argnames="retain_notes", argvalues=[False, True])
def test_prepared_context_and_all_admonitions(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    retain_notes: bool,
) -> None:
    """Caller contexts and native admonition filtering work together."""
    source = tmp_path / "source"
    kinds = (
        "note",
        "tip",
        "hint",
        "warning",
        "caution",
        "important",
        "attention",
        "danger",
        "error",
    )
    admonitions = "\n\n".join(f".. {kind}:: Private {kind}." for kind in kinds)
    write_sources(
        source=source,
        files={
            "index.rst": (
                "Index\n=====\n\n.. toctree::\n\n   guide\n   review\n"
            ),
            "guide.rst": (
                "Guide\n=====\n\nWork\n----\n\nBody\n~~~~\n\n"
                "Visible |product|.\n\n"
                ".. jinja:: prepared\n\n   {{ message }}\n\n"
            )
            + admonitions
            + "\n\n.. include:: shared.txt\n",
            "shared.txt": ".. admonition:: Custom\n\n   Private custom.\n",
            "review.rst": (
                ".. interviewer-guideline:: guide.rst\n\n"
                "   .. guideline-part:: Work\n\n"
                "      .. guideline-group:: Content\n\n"
                "         .. guideline-select:: Body\n"
            ),
        },
    )
    app = make_app(
        srcdir=source,
        exception_on_warning=True,
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
            "hackerrank_exclude_admonitions": not retain_notes,
            "rst_prolog": ".. |product| replace:: Widget\n",
            "jinja2_contexts": {
                "prepared": {"message": "Caller-selected example."}
            },
        },
    )
    app.build()
    html = (Path(app.outdir) / "review.html").read_text()
    assert "Visible Widget." in html
    assert "Caller-selected example." in html
    assert ("Private custom." in html) is retain_notes
    for kind in kinds:
        assert ("Private " + kind + "." in html) is retain_notes
    assert app.config.jinja2_contexts["prepared"] == {
        "message": "Caller-selected example."
    }
    dependencies = {Path(path).name for path in app.env.dependencies["review"]}
    assert "shared.txt" in dependencies
    assert app.warning.getvalue() == ""
