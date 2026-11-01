"""Automatic layouts follow native sections and the consumer's
mappings.
"""

import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from sphinx.testing.util import SphinxTestApp

from sphinx_hackerrank.layout import (
    GroupRequirement,
    GuidelineLayout,
    SectionGroup,
    SectionSelection,
)
from tests.builds import write_sources

_MAPPING = """\
version: 1
questions:
  - language: python
    name: Widgets - Python
  - language: javascript
    name: Widgets - JavaScript
"""
_GUIDE = """\
Widgets
=======

First part
----------

Prompt
~~~~~~

.. jinja:: snippets

   {{ example }}

.. include:: /details.rst

PROMPT_CONTENT

FAQ
~~~

The name is always a string.

FAQ_CONTENT

Key considerations
~~~~~~~~~~~~~~~~~~

Consider empty names.

Test cases
~~~~~~~~~~

.. code-block:: text

   widget = ""

Second part
-----------

Prompt
~~~~~~

Discuss another requirement.

FAQ
~~~

.. note:: Only an admonition, with no FAQ content.

Evaluation
----------

Explain the code.

.. warning:: Private evaluation admonition.
"""
_FOLLOW_UP = """\
Follow up questions
^^^^^^^^^^^^^^^^^^^

How would you handle an empty widget name?
"""


def _configuration() -> dict[str, object]:
    """Use a custom template context to expose accidental cross-language
    reads.
    """
    return {
        "extensions": ["sphinx_hackerrank"],
        "hackerrank_guideline_layout": GuidelineLayout(
            part_pattern=(
                r"(?:Q[1-9]\d*|First part|Second part|New part|Build a widget)"
            ),
            groups=(
                SectionGroup(
                    title="Prompt",
                    sections=(SectionSelection(headings=("Prompt",)),),
                ),
                SectionGroup(
                    title="FAQ",
                    sections=(
                        SectionSelection(headings=("FAQ",), required=False),
                    ),
                ),
                SectionGroup(
                    title="Signals and edge-case questions",
                    sections=(
                        SectionSelection(
                            headings=("Follow up questions",), required=False
                        ),
                        SectionSelection(
                            headings=("Key considerations",),
                            required=False,
                            include_heading=True,
                        ),
                    ),
                ),
                SectionGroup(
                    title="Test cases",
                    sections=(
                        SectionSelection(
                            headings=("Test cases",), required=False
                        ),
                    ),
                ),
            ),
            trailing_sections=(
                SectionSelection(headings=("Evaluation",), required=False),
            ),
            introduction=(
                "Interviewer only. "
                "Share prompts and test cases as you reach each part. See the "
                "`full guide <{source_url}>`_ for interview setup "
                "and reference solutions."
            ),
        ),
        "hackerrank_jinja_context": "snippets",
        "jinja2_contexts": {"snippets": {"example": "unselected language"}},
        "hackerrank_languages": {
            "python": {
                "name": "Python",
                "context": {"example": "Python prompt"},
            },
            "javascript": {
                "name": "JavaScript",
                "context": {"example": "JavaScript prompt"},
            },
        },
    }


def _files(*, guide: str, mapping: str) -> dict[str, str]:
    """Keep the source guide, composed view, and mapping in a nested
    folder.
    """
    files = {
        "index.rst": (
            "Index\n=====\n\n.. toctree::\n\n"
            "   topics/guide\n   topics/derived-interviewer-guideline\n"
        ),
        "topics/guide.rst": guide,
        "topics/derived-interviewer-guideline.rst": (
            ".. interviewer-guideline:: guide.rst\n"
        ),
        "topics/derived-interviewer-guideline.yml": mapping,
    }
    if "details.rst" in guide:
        files["details.rst"] = ".. tip:: Prompt admonition.\n"
    return files


@pytest.mark.parametrize(
    argnames="buildername", argvalues=["html", "hackerrank"]
)
@pytest.mark.parametrize(
    argnames="follow_up_parent", argvalues=["Prompt", "FAQ", "Deep prompt"]
)
@pytest.mark.parametrize(
    argnames="exclude_admonitions", argvalues=[False, True]
)
@pytest.mark.parametrize(
    argnames="source_url", argvalues=[None, "https://example.com/source/"]
)
def test_derived_layout_tracks_guide_and_mapping(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    buildername: str,
    follow_up_parent: str,
    exclude_admonitions: bool,
    source_url: str | None,
) -> None:
    """Nested follow-ups appear once, absent categories stay absent, and
    new
    source parts refresh both the themed page and standalone fragments.
    """
    follow_up = _FOLLOW_UP
    if follow_up_parent == "Deep prompt":
        follow_up = "Details\n^^^^^^^\n\n" + _FOLLOW_UP.replace("^", '"')
    guide = _GUIDE.replace(
        "PROMPT_CONTENT", follow_up if follow_up_parent != "FAQ" else ""
    )
    guide = guide.replace(
        "FAQ_CONTENT", _FOLLOW_UP if follow_up_parent == "FAQ" else ""
    )
    source = tmp_path / "source"
    write_sources(source=source, files=_files(guide=guide, mapping=_MAPPING))
    app = make_app(
        srcdir=source,
        buildername=buildername,
        exception_on_warning=True,
        confoverrides={
            **_configuration(),
            "hackerrank_exclude_admonitions": exclude_admonitions,
            "hackerrank_source_url": source_url,
            "hackerrank_source_suffix": ".rst",
        },
    )
    app.build()
    html_path = Path(app.outdir) / "topics/derived-interviewer-guideline.html"
    soup = BeautifulSoup(markup=html_path.read_text(), features="html.parser")
    heading = soup.h1
    assert heading is not None
    assert "Widgets: HackerRank Interviewer Guidelines" in heading.get_text()
    containers = soup.select(selector=".hr-interviewer-guideline")
    languages = ["Python", "JavaScript"]
    assert len(containers) == len(languages)
    for container, language in zip(containers, languages, strict=True):
        assert language + " prompt" in container.get_text()
        assert "unselected language" not in container.get_text()
        assert (
            container.get_text().count(
                "How would you handle an empty widget name?"
            )
            == 1
        )
        first, second, evaluation = container.select(
            selector=":scope > details"
        )
        assert [
            item.get_text()
            for item in first.select(selector=":scope > details > summary")
        ] == ["Prompt", "FAQ", "Signals and edge-case questions", "Test cases"]
        assert [
            item.get_text()
            for item in second.select(selector=":scope > details > summary")
        ] == (["Prompt"] if exclude_admonitions else ["Prompt", "FAQ"])
        assert "Explain the code." in evaluation.get_text()
        assert (
            bool(container.select(selector=".admonition"))
            is not exclude_admonitions
        )
        link = container.select_one(selector="a")
        assert link is not None
        assert link["href"] == (
            "guide.html"
            if source_url is None
            else source_url + "topics/guide.rst"
        )
    assert app.config.jinja2_contexts["snippets"] == {
        "example": "unselected language"
    }
    # Add a part and a language by changing only their authoritative inputs.
    guide_path = source / "topics/guide.rst"
    _ = guide_path.write_text(
        data=guide
        + "\nNew part\n--------\n\nPrompt\n~~~~~~\n\nNew requirement.\n"
    )
    mapping_path = source / "topics/derived-interviewer-guideline.yml"
    _ = mapping_path.write_text(
        data=_MAPPING.replace(
            "  - language: javascript\n    name: Widgets - JavaScript\n", ""
        )
    )
    app.build()
    refreshed = BeautifulSoup(
        markup=html_path.read_text(), features="html.parser"
    )
    assert len(refreshed.select(selector=".hr-interviewer-guideline")) == 1
    assert "New requirement." in refreshed.get_text()
    if buildername == "hackerrank":
        fragment = (
            Path(app.outdir)
            / "interviewer-guidelines/topics/derived/python.html"
        )
        assert "New requirement." in fragment.read_text()


@pytest.mark.parametrize(
    argnames=("guide", "mapping", "message"),
    argvalues=[
        ("Widgets\n=======\n", "", "requires an adjacent language mapping"),
        ("No headings here.\n", _MAPPING, "requires a guide title"),
        ("Widgets\n=======\n\nNo parts.\n", _MAPPING, "Expected at least"),
        (
            "Widgets\n=======\n\nQ1\n--\n\nPrompt\n~~~~~~\n\nHi.\n\nFAQ\n~~~\n\nOne.\n\nFAQ\n~~~\n\nTwo.\n",
            _MAPPING,
            "Ambiguous selection",
        ),
        (
            "Widgets\n=======\n\nQ1\n--\n\nPrompt\n~~~~~~\n\nHi.\n\nEvaluation\n----------\n\nOne.\n\nEvaluation\n----------\n\nTwo.\n",
            _MAPPING,
            "Ambiguous selection",
        ),
    ],
)
def test_derived_layout_rejects_incomplete_or_ambiguous_sources(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    guide: str,
    mapping: str,
    message: str,
) -> None:
    """Invalid inputs report errors instead of silently dropping a
    part.
    """
    files = _files(guide=guide, mapping=mapping)
    if not bool(mapping):
        del files["topics/derived-interviewer-guideline.yml"]
    source = tmp_path / "source"
    write_sources(source=source, files=files)
    app = make_app(srcdir=source, confoverrides=_configuration())
    app.build()
    assert message in app.warning.getvalue()


@pytest.mark.parametrize(argnames="empty_evaluation", argvalues=[False, True])
def test_derived_layout_allows_a_guide_without_evaluation(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    empty_evaluation: bool,
) -> None:
    """A single prompt needs no evaluation section or fixed part names."""
    source = tmp_path / "source"
    guide = (
        "Widgets\n=======\n\nBuild a widget\n--------------\n\n"
        "Prompt\n~~~~~~\n\nBuild it.\n"
        "\nKey considerations\n~~~~~~~~~~~~~~~~~~\n\n.. note:: No content.\n"
    )
    if empty_evaluation:
        guide += "\nEvaluation\n----------\n\n.. warning:: No content.\n"
    write_sources(source=source, files=_files(guide=guide, mapping=_MAPPING))
    app = make_app(
        srcdir=source,
        exception_on_warning=True,
        confoverrides=_configuration(),
    )
    app.build()
    html = (
        Path(app.outdir) / "topics/derived-interviewer-guideline.html"
    ).read_text()
    assert "Build it." in html
    assert "Evaluation" not in html
    assert "Signals and edge-case questions" not in html


def test_layout_must_be_supplied_by_the_consumer(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """No built-in outline is selected when the consumer omits its
    policy.
    """
    source = tmp_path / "source"
    write_sources(
        source=source, files=_files(guide="Guide\n=====\n", mapping=_MAPPING)
    )
    app = make_app(
        srcdir=source,
        confoverrides={
            **_configuration(),
            "hackerrank_guideline_layout": None,
        },
    )
    app.build()
    assert "requires a caller-supplied layout" in app.warning.getvalue()


def test_layout_accepts_unrelated_heading_vocabulary(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Accept unrelated source labels and display labels without
    changes.
    """
    source = tmp_path / "source"
    guide = (
        "Widgets\n=======\n\nStage one\n---------\n\nBrief\n~~~~~\n\n"
        "Make a widget.\n\nCases\n~~~~~\n\nUse a blue widget.\n"
    )
    write_sources(source=source, files=_files(guide=guide, mapping=_MAPPING))
    app = make_app(
        srcdir=source,
        exception_on_warning=True,
        confoverrides={
            **_configuration(),
            "hackerrank_guideline_layout": GuidelineLayout(
                part_pattern=r"Stage .*",
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(SectionSelection(headings=("Brief",)),),
                    ),
                    SectionGroup(
                        title="Examples",
                        sections=(
                            SectionSelection(
                                headings=("Cases",), include_heading=True
                            ),
                        ),
                    ),
                ),
            ),
        },
    )
    app.build()
    html = (
        Path(app.outdir) / "topics/derived-interviewer-guideline.html"
    ).read_text()
    soup = BeautifulSoup(markup=html, features="html.parser")
    for container in soup.select(selector=".hr-interviewer-guideline"):
        assert [
            summary.get_text()
            for summary in container.select(
                selector=":scope > details > details > summary"
            )
        ] == ["Work", "Examples"]
        assert "Use a blue widget." in container.get_text()
        assert "See the" not in container.get_text()


@pytest.mark.parametrize(
    argnames=("guide", "layout", "message"),
    argvalues=[
        (
            "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n\nQ2\n--\n\nRenamed\n~~~~~~~\n\nTwo.\n",
            GuidelineLayout(
                part_pattern=r"Q\d",
                minimum_parts=2,
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(
                            SectionSelection(headings=("Brief", "Briefs")),
                        ),
                    ),
                ),
            ),
            "Required selection ('Brief', 'Briefs') missing in 'Q2'",
        ),
        (
            "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n",
            GuidelineLayout(
                part_pattern=r"Q\d",
                minimum_parts=2,
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(SectionSelection(headings=("Brief",)),),
                    ),
                ),
            ),
            "Expected at least 2 guide parts",
        ),
        (
            "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n\nBriefs\n~~~~~~\n\nTwo.\n",
            GuidelineLayout(
                part_pattern=r"Q\d",
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(
                            SectionSelection(headings=("Brief", "Briefs")),
                        ),
                    ),
                ),
            ),
            "Ambiguous selection",
        ),
        (
            (
                "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\n"
                ".. note:: Private content only.\n"
            ),
            GuidelineLayout(
                part_pattern=r"Q\d",
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(SectionSelection(headings=("Brief",)),),
                    ),
                ),
            ),
            "is empty after filtering",
        ),
        (
            (
                "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\n"
                ".. note:: Private content only.\n"
            ),
            GuidelineLayout(
                part_pattern=r"Q\d",
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(
                            SectionSelection(
                                headings=("Brief",), required=False
                            ),
                        ),
                    ),
                ),
            ),
            "has no rendered content",
        ),
        (
            "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n\nQ1\n--\n\nBrief\n~~~~~\n\nTwo.\n",
            GuidelineLayout(
                part_pattern=r"Q\d",
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(SectionSelection(headings=("Brief",)),),
                    ),
                ),
            ),
            "duplicate headings",
        ),
        (
            "Widgets\n=======\n\nQ1\n--\n\nQ2\n~~\n\nBrief\n^^^^^\n\nOne.\n",
            GuidelineLayout(
                part_pattern=r"Q\d",
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(SectionSelection(headings=("Brief",)),),
                    ),
                ),
            ),
            "must not be nested",
        ),
        (
            "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n",
            GuidelineLayout(
                part_pattern=r"Q\d",
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(SectionSelection(headings=("Brief",)),),
                    ),
                    SectionGroup(
                        title="Examples",
                        sections=(
                            SectionSelection(
                                headings=("Cases",), required=False
                            ),
                        ),
                    ),
                ),
                required_groups=(
                    GroupRequirement(part_pattern=r"Q1", groups=("Examples",)),
                ),
            ),
            "Required groups ['Examples'] missing from guide part 'Q1'",
        ),
        (
            "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n",
            GuidelineLayout(
                part_pattern=r"Q\d",
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(SectionSelection(headings=("Brief",)),),
                    ),
                ),
                required_groups=(
                    GroupRequirement(
                        part_pattern=r"Q[12]",
                        groups=("Work",),
                        minimum_parts=2,
                    ),
                ),
            ),
            "Group requirement 'Q[12]' expected at least 2 parts",
        ),
        *[
            (
                "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n",
                GuidelineLayout(
                    part_pattern=r"Q\d",
                    groups=(
                        SectionGroup(
                            title="Work",
                            sections=(SectionSelection(headings=("Brief",)),),
                        ),
                    ),
                    leading_sections=(SectionSelection(headings=(heading,)),),
                ),
                "overlaps a guide part",
            )
            for heading in ("Widgets", "Q1", "Brief")
        ],
    ],
)
def test_completeness_contract_rejects_lost_content(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    guide: str,
    layout: GuidelineLayout,
    message: str,
) -> None:
    """Renamed, empty, or missing content cannot silently remove a
    part.
    """
    source = tmp_path / "source"
    write_sources(source=source, files=_files(guide=guide, mapping=_MAPPING))
    app = make_app(
        srcdir=source,
        confoverrides={
            **_configuration(),
            "hackerrank_guideline_layout": layout,
        },
    )
    app.build()
    assert message in app.warning.getvalue()


@pytest.mark.parametrize(argnames="layout_name", argvalues=["body", "unknown"])
def test_named_body_layout_with_shared_sections(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    layout_name: str,
) -> None:
    """Shared introductions and body-based stages need no category
    headings.
    """
    guide = textwrap.dedent(
        text="""\
        Widgets
        =======

        Shared brief
        ------------

        Build something useful.

        Stage one
        ---------

        Make the first version.

        Discussion
        ~~~~~~~~~~

        What would you improve?

        Stage two
        ---------

        Discuss the next version.

        Review
        ------

        Explain your decisions.
        """
    )

    layout = GuidelineLayout(
        part_pattern=r"Stage .*",
        minimum_parts=2,
        leading_sections=(SectionSelection(headings=("Shared brief",)),),
        groups=(
            SectionGroup(
                title="Work", sections=(SectionSelection(headings=(".",)),)
            ),
            SectionGroup(
                title="Questions",
                sections=(
                    SectionSelection(headings=("Discussion",), required=False),
                ),
            ),
        ),
        trailing_sections=(
            SectionSelection(headings=("Review",)),
            SectionSelection(headings=("Absent",), required=False),
        ),
        required_groups=(
            GroupRequirement(
                part_pattern=r"Stage .*", groups=("Work",), minimum_parts=2
            ),
        ),
    )
    source = tmp_path / "source"
    files = _files(guide=guide, mapping=_MAPPING)
    files["topics/derived-interviewer-guideline.rst"] += (
        f"   :layout: {layout_name}\n"
    )
    write_sources(source=source, files=files)
    app = make_app(
        srcdir=source,
        confoverrides={
            **_configuration(),
            "hackerrank_guideline_layout": None,
            "hackerrank_guideline_layouts": {"body": layout},
        },
    )
    app.build()
    if layout_name == "unknown":
        assert "requires a caller-supplied layout" in app.warning.getvalue()
        return
    assert app.warning.getvalue() == ""
    html = (
        Path(app.outdir) / "topics/derived-interviewer-guideline.html"
    ).read_text()
    soup = BeautifulSoup(markup=html, features="html.parser")
    for container in soup.select(selector=".hr-interviewer-guideline"):
        assert [
            summary.get_text()
            for summary in container.select(
                selector=":scope > details > summary"
            )
        ] == ["Shared brief", "Stage one", "Stage two", "Review"]
        assert container.get_text().count("What would you improve?") == 1
        assert "Discuss the next version." in container.get_text()
