"""Generated Interviewer Guidelines reuse native guide sections and
language-specific
inputs.
"""

from collections.abc import Callable
from pathlib import Path

import pytest
from bs4 import BeautifulSoup, Tag
from docutils.core import publish_doctree
from sphinx.testing.util import SphinxTestApp

from sphinx_hackerrank.sections import section_content, select_section

_SECTION_SOURCE = """Guide
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


@pytest.mark.parametrize(
    argnames="selector",
    argvalues=["Q9 / Prompt", "Q1 / Missing", "Prompt", "", "#missing"],
)
def test_missing_or_ambiguous_sections_fail(*, selector: str) -> None:
    """Reject selectors that do not identify exactly one section."""
    document = publish_doctree(source=_SECTION_SOURCE)
    with pytest.raises(
        expected_exception=ValueError, match="Expected one guide section"
    ):
        _ = select_section(document=document, selector=selector)


def test_section_paths_labels_and_copying() -> None:
    """Resolve headings and labels without mutating the source tree."""
    document = publish_doctree(source=_SECTION_SOURCE)
    section = select_section(document=document, selector="Q1 / Prompt")
    assert (
        select_section(document=document, selector="#stable-prompt") is section
    )
    before = document.pformat()
    for include_heading in (True, False):
        content = section_content(
            section=section,
            guide="guide",
            language="Python",
            include_heading=include_heading,
        )
        text = "\n".join(node.astext() for node in content)
        assert "First prompt." in text
        assert "Nested details." in text
        assert "FAQ" not in text
        assert "Second prompt." not in text
        assert "guide.html#details" in "".join(
            node.pformat() for node in content
        )
        assert ("Prompt" in text) == include_heading
    assert document.pformat() == before


@pytest.mark.parametrize(
    argnames=("filename", "options", "message"),
    argvalues=[
        ("../outside.rst", "", "within the source directory"),
        ("guide.txt", "", "within the source directory"),
        ("index.rst", "", "cannot include itself"),
        ("guide.rst", "", "requires :section: and :language:"),
        (
            "guide.rst",
            ":section: Q1 / Prompt\n:language: unknown",
            "Expected one Interviewer Guideline language config",
        ),
        ("guide.rst", ":section: Q9 / Prompt\n:language: python", "found 0"),
        ("guide.rst", ":section: Prompt\n:language: python", "found 2"),
    ],
)
def test_invalid_section_directives_report_errors(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    filename: str,
    options: str,
    message: str,
) -> None:
    """Report invalid source paths, options, and section selections."""
    source = tmp_path / "source"
    source.mkdir()
    _ = (source / "conf.py").write_text(
        data=(
            'extensions = ["sphinx_hackerrank"]\n'
            'jinja2_contexts = {"languages": {"original": '
            'True}, "interviewer_guidelines": {"language_configs": '
            '[{"language": "Python", "pygments_lexer": '
            '"python"}]}}\n'
            'hackerrank_languages = {"python": {"name": '
            '"Python", "context": {}}}\n'
        ),
        encoding="utf-8",
    )
    _ = (source / "guide.rst").write_text(
        data=_SECTION_SOURCE, encoding="utf-8"
    )
    _ = (source / "index.rst").write_text(
        data=(
            "Index\n=====\n\n.. toctree::\n\n   guide\n\n"
            f".. interviewer-guideline-section:: {filename}\n"
            + "\n".join(f"   {option}" for option in options.splitlines())
            + "\n"
        ),
        encoding="utf-8",
    )
    app = make_app(srcdir=source)
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
    index = BeautifulSoup(
        markup=preview_index.read_text(encoding="utf-8"),
        features="html.parser",
    )
    link = index.find(name="a", string="Example")
    assert isinstance(link, Tag)
    assert (
        preview_index.parent / str(object=link["href"])
    ).resolve() == fragment.resolve()
    assert "Updated wording." in fragment.read_text(encoding="utf-8")
    assert "HackerRank-specific content." in fragment.read_text(
        encoding="utf-8"
    )
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
    assert "Updated wording." in fragment.read_text(encoding="utf-8")
    assert preview_index.is_file()


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
    _ = (source / "conf.py").write_text(
        data="""extensions = ["sphinx_hackerrank"]
language_configs = [
    {"language": "Python", "pygments_lexer": "python"},
    {"language": "Java", "pygments_lexer": "java"},
]
jinja2_contexts = {
    "one": {},
    "languages": {"language_configs": language_configs},
    "interviewer_guidelines": {"language_configs": language_configs[:1]},
}
suppress_warnings = ["config.cache"]
rst_prolog = ".. |test-name| replace:: Shared guide text."
hackerrank_languages = {
    "python": {
        "name": "Python",
        "context": {"language_configs": language_configs[:1]},
    }
}
""",
        encoding="utf-8",
    )
    _ = (source / "index.rst").write_text(
        data="Index\n=====\n\n.. toctree::\n\n   guide\n"
        "   guide-interviewer-guideline\n",
        encoding="utf-8",
    )
    _ = (source / "shared-note.txt").write_text(
        data=".. caution:: Included caution.\n", encoding="utf-8"
    )
    guide = source / "guide.rst"
    _ = guide.write_text(
        data=(
            "Guide\n"
            "=====\n"
            "\n"
            "Outside the selected section.\n"
            "\n"
            "Prompt\n"
            "~~~~~~\n"
            "\n"
            "Original wording.\n"
            "\n"
            "|test-name|\n"
            "\n"
            + "\n\n".join(
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
            + "\n"
            "\n"
            ".. admonition:: Custom admonition\n"
            "\n"
            "   Hidden custom content.\n"
            "\n"
            ".. include:: shared-note.txt\n"
            "\n"
            ".. jinja:: one\n"
            "\n"
            "   .. note:: Generated note.\n"
            "\n"
            ".. code-block:: text\n"
            "\n"
            "   .. note:: Keep this literal example.\n"
            "\n"
            ".. only:: builder_hackerrank\n"
            "\n"
            "   HackerRank-specific content.\n"
            "\n"
            ".. only:: builder_html\n"
            "\n"
            "   Website-specific content.\n"
            "\n"
            ".. only:: html\n"
            "\n"
            "   Shared HTML content.\n"
        ),
        encoding="utf-8",
    )
    _ = (source / "guide-interviewer-guideline.rst").write_text(
        data=(
            "Interviewer Guideline\n"
            "=====================\n"
            "\n"
            ".. container:: hr-interviewer-guideline "
            "interviewer-guideline-python\n"
            "\n"
            "   .. interviewer-guideline-section:: guide.rst\n"
            "      :section: Prompt\n"
            "      :language: python\n"
        ),
        encoding="utf-8",
    )
    _ = (source / "guide-interviewer-guideline.yml").write_text(
        data="version: 1\n"
        "questions:\n"
        "  - language: python\n"
        "    question_id: '123'\n"
        "    name: Example\n",
        encoding="utf-8",
    )
    app = make_app(srcdir=source, buildername=buildername)
    app.build()
    output = Path(app.outdir) / "guide-interviewer-guideline.html"
    assert "Original wording." in output.read_text(encoding="utf-8")
    guideline = BeautifulSoup(
        markup=output.read_text(encoding="utf-8"), features="html.parser"
    )
    full = BeautifulSoup(
        markup=(Path(app.outdir) / "guide.html").read_text(encoding="utf-8"),
        features="html.parser",
    )
    assert bool(full.select(selector=".admonition"))
    assert not bool(guideline.select(selector=".admonition"))
    assert "Hidden" not in guideline.get_text()
    assert "Outside the selected section." not in guideline.get_text()
    expected_languages = 2
    assert (
        len(app.config.jinja2_contexts["languages"]["language_configs"])
        == expected_languages
    )
    tree = app.env.get_doctree(docname="guide-interviewer-guideline")
    assert "_interviewer_guideline_guides" not in tree.attributes
    assert all(node.document is tree for node in tree.findall())
    assert "Included caution" not in guideline.get_text()
    assert "Generated note" not in guideline.get_text()
    assert "Keep this literal example" in guideline.get_text()
    assert "Shared guide text." in guideline.get_text()
    assert "Included caution" in full.get_text()
    assert "Generated note" in full.get_text()
    assert "Shared HTML content." in guideline.get_text()
    assert ("HackerRank-specific content." in guideline.get_text()) == (
        buildername == "hackerrank"
    )
    assert ("Website-specific content." in guideline.get_text()) == (
        buildername == "html"
    )
    _ = guide.write_text(
        data=guide.read_text(encoding="utf-8").replace(
            "Original wording", "Updated wording"
        ),
        encoding="utf-8",
    )
    app.build()
    assert "Updated wording." in output.read_text(encoding="utf-8")
    assert "Original wording." not in output.read_text(encoding="utf-8")
    assert app.statuscode == 0
    assert app.warning.getvalue() == ""
    fragment = (
        Path(app.outdir) / "interviewer-guidelines" / "guide" / "python.html"
    )
    if buildername == "hackerrank":
        _assert_preview_refreshes(app=app, source=source, fragment=fragment)
    else:
        assert not fragment.exists()
