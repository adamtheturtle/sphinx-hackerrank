"""Explicit layouts follow native sections and the consumer's recipe."""

import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from sphinx.testing.util import SphinxTestApp

from sphinx_hackerrank import GuidelineExport
from tests.builds import write_sources

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
    """Use a caller-selected template context and explicit export."""
    return {
        "extensions": ["sphinx_hackerrank"],
        "jinja2_contexts": {"snippets": {"example": "Configured prompt"}},
        "hackerrank_exports": [
            GuidelineExport(
                docname="topics/derived-interviewer-guideline",
                selector=".hr-interviewer-guideline",
                output_path="interviewer-guidelines/topics/derived/guide.html",
                name="Widgets",
            )
        ],
    }


def _default_recipe(*, parts: tuple[str, ...]) -> str:
    """Build repeated test fixtures through the public RST workflow."""
    prefix = (
        ".. interviewer-guideline:: guide.rst\n\n"
        "   .. guideline-introduction::\n\n"
        "      Interviewer only. Share prompts and test cases "
        "as you reach each part.\n"
        "      See the `full guide <{source_url}>`_ for interview setup "
        "and reference solutions.\n\n"
    )
    groups = textwrap.dedent(
        text="""\
        .. guideline-group:: Prompt

           .. guideline-select:: Prompt

        .. guideline-group:: FAQ

           .. guideline-select:: FAQ
              :optional:

        .. guideline-group:: Signals and edge-case questions

           .. guideline-select:: Follow up questions
              :optional:

           .. guideline-select:: Key considerations
              :optional:
              :include-heading:

        .. guideline-group:: Test cases

           .. guideline-select:: Test cases
              :optional:

        """
    )
    return (
        prefix
        + "".join(
            f"   .. guideline-part:: {heading}\n\n"
            + textwrap.indent(text=groups, prefix="      ")
            for heading in parts
        )
        + "   .. guideline-after:: Evaluation\n      :optional:\n"
    )


def _files(*, guide: str, recipe: str) -> dict[str, str]:
    """Keep the maintained guide and composed view in a nested folder."""
    files = {
        "index.rst": (
            "Index\n=====\n\n.. toctree::\n\n"
            "   topics/guide\n   topics/derived-interviewer-guideline\n"
        ),
        "topics/guide.rst": guide,
        "topics/derived-interviewer-guideline.rst": recipe,
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
def test_derived_layout_tracks_guide(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    buildername: str,
    follow_up_parent: str,
    exclude_admonitions: bool,
    source_url: str | None,
) -> None:
    """Nested follow-ups appear once, absent categories stay absent, and
    updated
    source content refreshes both the themed page and standalone fragments.
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
    write_sources(
        source=source,
        files=_files(
            guide=guide,
            recipe=_default_recipe(parts=("First part", "Second part")),
        ),
    )
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
    assert len(containers) == 1
    for container in containers:
        assert "Configured prompt" in container.get_text()
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
        "example": "Configured prompt"
    }
    # Changing only the maintained guide refreshes the composed output.
    guide_path = source / "topics/guide.rst"
    _ = guide_path.write_text(
        data=guide.replace("Discuss another requirement.", "New requirement.")
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
            / "interviewer-guidelines/topics/derived/guide.html"
        )
        assert "New requirement." in fragment.read_text()


@pytest.mark.parametrize(
    argnames=("guide", "message"),
    argvalues=[
        ("No headings here.\n", "requires a guide title"),
        (
            "Widgets\n=======\n\nNo parts.\n",
            "Required guide parts are missing",
        ),
        (
            (
                "Widgets\n=======\n\nQ1\n--\n\nPrompt\n~~~~~~\n\nHi.\n\nFAQ\n"
                "~~~\n\nOne.\n\nFAQ\n~~~\n\nTwo.\n"
            ),
            "Ambiguous selection",
        ),
        (
            (
                "Widgets\n=======\n\nQ1\n--\n\nPrompt\n~~~~~~\n\nHi.\n\nEval"
                "uation\n----------\n\nOne.\n\nEvaluation\n----------\n\n"
                "Two.\n"
            ),
            "Ambiguous selection",
        ),
    ],
)
def test_derived_layout_rejects_incomplete_or_ambiguous_sources(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    guide: str,
    message: str,
) -> None:
    """Invalid inputs report errors instead of silently dropping a
    part.
    """
    files = _files(guide=guide, recipe=_default_recipe(parts=("Q1",)))
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
        "\nKey considerations\n~~~~~~~~~~~~~~~~~~\n\n"
        ".. note:: No content.\n"
    )
    if empty_evaluation:
        guide += "\nEvaluation\n----------\n\n.. warning:: No content.\n"
    write_sources(
        source=source,
        files=_files(
            guide=guide,
            recipe=_default_recipe(parts=("Build a widget",)),
        ),
    )
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


def test_recipe_content_is_required(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path
) -> None:
    """Every composition uses explicit RST declarations."""
    source = tmp_path / "source"
    write_sources(
        source=source,
        files=_files(
            guide="Guide\n=====\n",
            recipe=".. interviewer-guideline:: guide.rst\n",
        ),
    )
    app = make_app(srcdir=source, confoverrides=_configuration())
    app.build()
    assert "Content block expected" in app.warning.getvalue()


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
    write_sources(
        source=source,
        files=_files(
            guide=guide,
            recipe=textwrap.dedent(
                text="""\
                .. interviewer-guideline:: guide.rst

                   .. guideline-part:: Stage one

                      .. guideline-group:: Work

                         .. guideline-select:: Brief

                      .. guideline-group:: Examples

                         .. guideline-select:: Cases
                            :include-heading:

                """
            ),
        ),
    )
    app = make_app(
        srcdir=source,
        exception_on_warning=True,
        confoverrides=_configuration(),
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
    argnames=("guide", "recipe", "message"),
    argvalues=[
        (
            (
                "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n\nQ2\n--"
                "\n\nRenamed\n~~~~~~~\n\nTwo.\n"
            ),
            textwrap.dedent(
                text="""\
                .. interviewer-guideline:: guide.rst

                   .. guideline-part:: Q1

                      .. guideline-group:: Work

                         .. guideline-select:: Brief
                            :alternatives: Briefs

                   .. guideline-part:: Q2

                      .. guideline-group:: Work

                         .. guideline-select:: Brief
                            :alternatives: Briefs

                """
            ),
            "Required selection ('Brief', 'Briefs') missing in 'Q2'",
        ),
        (
            "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n",
            textwrap.dedent(
                text="""\
                .. interviewer-guideline:: guide.rst

                   .. guideline-part:: Q1

                      .. guideline-group:: Work

                         .. guideline-select:: Brief

                   .. guideline-part:: Q2

                      .. guideline-group:: Work

                         .. guideline-select:: Brief

                """
            ),
            "Required guide parts are missing",
        ),
        (
            (
                "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n\nBrief"
                "s\n~~~~~~\n\nTwo.\n"
            ),
            textwrap.dedent(
                text="""\
                .. interviewer-guideline:: guide.rst

                   .. guideline-part:: Q1

                      .. guideline-group:: Work

                         .. guideline-select:: Brief
                            :alternatives: Briefs

                """
            ),
            "Ambiguous selection",
        ),
        (
            (
                "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\n"
                ".. note:: Private content only.\n"
            ),
            textwrap.dedent(
                text="""\
                .. interviewer-guideline:: guide.rst

                   .. guideline-part:: Q1

                      .. guideline-group:: Work

                         .. guideline-select:: Brief

                """
            ),
            "is empty after filtering",
        ),
        (
            (
                "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\n"
                ".. note:: Private content only.\n"
            ),
            textwrap.dedent(
                text="""\
                .. interviewer-guideline:: guide.rst

                   .. guideline-part:: Q1

                      .. guideline-group:: Work

                         .. guideline-select:: Brief
                            :optional:

                """
            ),
            "has no rendered content",
        ),
        (
            (
                "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n\nQ1\n--"
                "\n\nBrief\n~~~~~\n\nTwo.\n"
            ),
            textwrap.dedent(
                text="""\
                .. interviewer-guideline:: guide.rst

                   .. guideline-part:: Q1

                      .. guideline-group:: Work

                         .. guideline-select:: Brief

                """
            ),
            "duplicate headings",
        ),
        (
            "Widgets\n=======\n\nQ1\n--\n\nQ2\n~~\n\nBrief\n^^^^^\n\nOne.\n",
            textwrap.dedent(
                text="""\
                .. interviewer-guideline:: guide.rst

                   .. guideline-part:: Q1

                      .. guideline-group:: Work

                         .. guideline-select:: Brief

                   .. guideline-part:: Q2

                      .. guideline-group:: Work

                         .. guideline-select:: Brief

                """
            ),
            "must not be nested",
        ),
        (
            "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n",
            textwrap.dedent(
                text="""\
                .. interviewer-guideline:: guide.rst

                   .. guideline-part:: Q1

                      .. guideline-group:: Work

                         .. guideline-select:: Brief

                      .. guideline-group:: Examples

                         .. guideline-select:: Cases

                """
            ),
            "Required selection ('Cases',) missing in 'Q1'",
        ),
        *[
            (
                "Widgets\n=======\n\nQ1\n--\n\nBrief\n~~~~~\n\nOne.\n",
                textwrap.dedent(
                    text="""\
                    .. interviewer-guideline:: guide.rst

                       .. guideline-before:: __EXCLUSION__

                       .. guideline-part:: Q1

                          .. guideline-group:: Work

                             .. guideline-select:: Brief

                    """
                ).replace("__EXCLUSION__", heading),
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
    recipe: str,
    message: str,
) -> None:
    """Renamed, empty, or missing content cannot silently remove a
    part.
    """
    source = tmp_path / "source"
    write_sources(
        source=source,
        files=_files(guide=guide, recipe=recipe),
    )
    app = make_app(
        srcdir=source,
        confoverrides=_configuration(),
    )
    app.build()
    assert message in app.warning.getvalue()


def test_explicit_body_parts_with_shared_sections(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
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

    recipe = textwrap.dedent(
        text="""\
                 .. interviewer-guideline:: guide.rst

                    .. guideline-before:: Shared brief

                    .. guideline-part:: Stage one

                       .. guideline-group:: Work

                          .. guideline-select:: .

                       .. guideline-group:: Questions

                          .. guideline-select:: Discussion
                             :optional:

                    .. guideline-part:: Stage two

                       .. guideline-group:: Work

                          .. guideline-select:: .

                       .. guideline-group:: Questions

                          .. guideline-select:: Discussion
                             :optional:

                    .. guideline-after:: Review

                    .. guideline-after:: Absent
                       :optional:

                 """
    )
    source = tmp_path / "source"
    files = _files(guide=guide, recipe=recipe)
    write_sources(source=source, files=files)
    app = make_app(
        srcdir=source,
        confoverrides=_configuration(),
    )
    app.build()
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
