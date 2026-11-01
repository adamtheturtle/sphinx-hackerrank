"""Generated Interviewer Guidelines reuse native guide sections and
language-specific
inputs.
"""

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
        "interviewer-guideline-python\n\n"
        "   .. rubric:: Guide: Python\n\n"
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
    files["view-interviewer-guideline.yml"] = (
        "version: 1\nquestions:\n  - language: python\n    name: Example\n"
    )
    source = tmp_path / "actual"
    write_sources(source=source, files=files)
    app = make_app(
        srcdir=source,
        exception_on_warning=True,
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
            "hackerrank_languages": {"python": {"name": "Python"}},
        },
    )
    app.build()
    for docname, html in expected.items():
        assert (Path(app.outdir) / f"{docname}.html").read_text(
            encoding="utf-8"
        ) == html


@pytest.mark.parametrize(
    argnames=("filename", "language", "message"),
    argvalues=[
        ("../outside.rst", "python", "within the source directory"),
        ("guide.txt", "python", "within the source directory"),
        ("view-interviewer-guideline.rst", "python", "cannot include itself"),
        (
            "guide.rst",
            "unknown",
            "Expected one Interviewer Guideline language config",
        ),
    ],
)
def test_invalid_recipe_sources_report_errors(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    filename: str,
    language: str,
    message: str,
) -> None:
    """The RST entry point validates source paths and mapped languages."""
    source = tmp_path / "source"
    write_sources(
        source=source,
        files={
            "index.rst": (
                "Index\n=====\n\n.. toctree::\n\n"
                "   guide\n   view-interviewer-guideline\n"
            ),
            "guide.rst": _SECTION_SOURCE,
            "view-interviewer-guideline.rst": (
                f".. interviewer-guideline:: {filename}\n\n"
                "   .. guideline-part:: Q1\n\n"
                "      .. guideline-group:: Work\n\n"
                "         .. guideline-select:: Prompt\n"
            ),
            "view-interviewer-guideline.yml": (
                f"version: 1\nquestions:\n  - language: {language}\n"
                "    name: Example\n"
            ),
        },
    )
    app = make_app(
        srcdir=source,
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
            "jinja2_contexts": {"languages": {"original": True}},
            "hackerrank_languages": {
                "python": {"name": "Python", "context": {}}
            },
        },
    )
    app.build()
    assert message in app.warning.getvalue()
    assert app.config.jinja2_contexts["languages"] == {"original": True}


def _assert_preview_refreshes(
    *, app: SphinxTestApp, source: Path, fragment: Path
) -> None:
    """Preview links, mappings, and missing artifacts follow incremental
    builds.
    """
    preview_index = fragment.parent.parent / "index.html"
    original = fragment.read_text(encoding="utf-8")
    original_index = preview_index.read_text(encoding="utf-8")
    modified = fragment.stat().st_mtime_ns
    app.build()
    assert fragment.stat().st_mtime_ns == modified
    mapping = source / "guide-interviewer-guideline.yml"
    _ = mapping.write_text(
        data=mapping.read_text(encoding="utf-8").replace(
            "name: Example", "name: Renamed"
        ),
        encoding="utf-8",
    )
    app.build()
    assert fragment.stat().st_mtime_ns > modified
    fragment.unlink()
    preview_index.unlink()
    app.build()
    assert fragment.read_text(encoding="utf-8") == original
    assert preview_index.read_text(encoding="utf-8") != original_index


@pytest.mark.parametrize(
    argnames="buildername", argvalues=["html", "hackerrank"]
)
def test_incremental_build_refreshes_the_view(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    buildername: str,
) -> None:
    """Changing only the main guide also rebuilds its Interviewer
    Guideline.
    """
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "index.rst").write_text(
        data=textwrap.dedent(
            text="""\
            Index
            =====

            .. toctree::

               guide
               guide-interviewer-guideline
            """
        ),
        encoding="utf-8",
    )
    _ = (source / "shared-note.txt").write_text(
        data=".. caution:: Included caution.\n", encoding="utf-8"
    )
    guide = source / "guide.rst"
    admonitions = "\n\n".join(
        f".. {kind}:: Hidden {kind}."
        for kind in (
            "tip",
            "hint",
            "note",
            "warning",
            "attention",
            "important",
            "danger",
            "error",
        )
    )
    _ = guide.write_text(
        data=(
            textwrap.dedent(
                text="""\
                Guide
                =====

                Outside the selected section.

                Prompt
                ~~~~~~

                Original wording.

                |test-name|

                """
            )
            + admonitions
            + "\n\n"
            + textwrap.dedent(
                text="""\
                .. admonition:: Custom admonition

                   Hidden custom content.

                .. include:: shared-note.txt

                .. jinja:: one

                   .. note:: Generated note.

                .. code-block:: text

                   .. note:: Keep this literal example.

                .. only:: builder_hackerrank

                   HackerRank-specific content.

                .. only:: builder_html

                   Website-specific content.

                .. only:: html

                   Shared HTML content.
                """
            )
        ),
        encoding="utf-8",
    )
    classes = "hr-interviewer-guideline interviewer-guideline-python"
    _ = (source / "guide-interviewer-guideline.rst").write_text(
        data=textwrap.dedent(
            text="""\
            .. interviewer-guideline:: guide.rst

               .. guideline-part:: Prompt

                  .. guideline-group:: Instructions

                     .. guideline-select:: .
            """
        ),
        encoding="utf-8",
    )
    _ = (source / "guide-interviewer-guideline.yml").write_text(
        data=textwrap.dedent(
            text="""\
            version: 1
            questions:
              - language: python
                question_id: '123'
                name: Example
            """
        ),
        encoding="utf-8",
    )
    language_configs = [
        {"language": "Python", "pygments_lexer": "python"},
        {"language": "Java", "pygments_lexer": "java"},
    ]
    audience = "HackerRank" if buildername == "hackerrank" else "Website"
    native_guideline = textwrap.dedent(
        text=f"""\
        Guide: HackerRank Interviewer Guidelines
        ========================================

        .. container:: {classes}

           .. rubric:: Guide: Python

           .. collapse:: Prompt

              .. collapse:: Instructions

                 Original wording.

                 Shared guide text.

                 .. code-block:: text

                    .. note:: Keep this literal example.

                 {audience}-specific content.

                 Shared HTML content.
        """
    )
    native_guide = guide.read_text(encoding="utf-8")
    if buildername == "hackerrank":
        native_guide = native_guide.replace(
            "builder_html", "unused_builder"
        ).replace("builder_hackerrank", "builder_html")
    expected_pages = [
        build_expected(
            make_app=make_app,
            source=tmp_path / f"expected-{wording}",
            files={
                "index.rst": (source / "index.rst").read_text(
                    encoding="utf-8"
                ),
                "guide.rst": native_guide.replace(
                    "Original wording", f"{wording} wording"
                ),
                "shared-note.txt": (source / "shared-note.txt").read_text(
                    encoding="utf-8"
                ),
                "guide-interviewer-guideline.rst": native_guideline.replace(
                    "Original wording", f"{wording} wording"
                ),
            },
            confoverrides={
                "html_context": {"builder": buildername},
                "jinja2_contexts": {
                    "one": {},
                    "languages": {"language_configs": language_configs},
                },
                "rst_prolog": ".. |test-name| replace:: Shared guide text.",
                "suppress_warnings": ["config.cache"],
            },
            docnames=["index", "guide", "guide-interviewer-guideline"],
        )
        for wording in ("Original", "Updated")
    ]
    app = make_app(
        srcdir=source,
        buildername=buildername,
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
            "jinja2_contexts": {
                "one": {},
                "languages": {"language_configs": language_configs},
                "interviewer_guidelines": {
                    "language_configs": language_configs[:1],
                },
            },
            "suppress_warnings": ["config.cache"],
            "rst_prolog": ".. |test-name| replace:: Shared guide text.",
            "hackerrank_languages": {
                "python": {
                    "name": "Python",
                    "context": {"language_configs": language_configs[:1]},
                },
            },
        },
    )
    app.build()
    for docname, html in expected_pages[0].items():
        assert (Path(app.outdir) / f"{docname}.html").read_text(
            encoding="utf-8"
        ) == html
    expected_languages = 2
    assert (
        len(app.config.jinja2_contexts["languages"]["language_configs"])
        == expected_languages
    )
    tree = app.env.get_doctree(docname="guide-interviewer-guideline")
    assert all(node.document is tree for node in tree.findall())
    _ = guide.write_text(
        data=guide.read_text(encoding="utf-8").replace(
            "Original wording", "Updated wording"
        ),
        encoding="utf-8",
    )
    app.build()
    for docname, html in expected_pages[1].items():
        assert (Path(app.outdir) / f"{docname}.html").read_text(
            encoding="utf-8"
        ) == html
    assert app.statuscode == 0
    assert app.warning.getvalue() == ""
    fragment = (
        Path(app.outdir) / "interviewer-guidelines" / "guide" / "python.html"
    )
    if buildername == "hackerrank":
        _assert_preview_refreshes(app=app, source=source, fragment=fragment)
    else:
        assert not fragment.exists()
