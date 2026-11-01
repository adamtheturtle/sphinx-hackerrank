"""Document-owned recipes preserve content and reject invalid RST
grammar.
"""

import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.builds import write_sources

_GUIDE = textwrap.dedent(
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
_RECIPE = """.. interviewer-guideline:: guide.rst

   .. include:: recipe.txt
"""
_DECLARATIONS = """\
.. guideline-introduction::

   .. include:: intro.txt

   See the `full guide <{source_url}>`_.

.. guideline-before:: Shared brief

.. guideline-part:: Stage one

   .. guideline-group:: Work

      .. include:: selections.txt

   .. guideline-group:: Questions

      .. guideline-select:: Discussion
         :alternatives: Discussions
                       Discussion topics
         :optional:
         :include-heading:

.. guideline-part:: Stage two

   .. guideline-group:: Next steps

      .. guideline-select:: .

.. guideline-after:: Review

.. guideline-after:: Absent
   :optional:
"""


def _sources(*, recipe: str) -> dict[str, str]:
    """Keep render-only question mappings independent of any API
    client.
    """
    return {
        "index.rst": (
            "Index\n=====\n\n.. toctree::\n\n"
            "   guide\n   view-interviewer-guideline\n"
        ),
        "guide.rst": _GUIDE,
        "view-interviewer-guideline.rst": recipe,
        "view-interviewer-guideline.yml": (
            "version: 1\nquestions:\n"
            "  - language: python\n    name: Widgets - Python\n"
            "  - language: javascript\n    name: Widgets - JavaScript\n"
        ),
    }


def _configuration() -> dict[str, object]:
    """Configure site-wide language settings without layout policy."""
    return {
        "extensions": ["sphinx_hackerrank"],
        "hackerrank_languages": {
            "python": {"name": "Python"},
            "javascript": {"name": "JavaScript"},
        },
    }


@pytest.mark.parametrize(
    argnames="buildername", argvalues=["html", "hackerrank"]
)
def test_inline_recipe_tracks_native_includes(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    buildername: str,
) -> None:
    """Shared instructions, body selections, and recipe changes refresh
    both languages.
    """
    source = tmp_path / "source"
    originals = _sources(recipe=_RECIPE)
    files = {
        f"topics/{name}": content
        for name, content in originals.items()
        if name != "index.rst"
    }
    files.update(
        {
            "index.rst": originals["index.rst"]
            .replace("   guide", "   topics/guide")
            .replace("   view", "   topics/view"),
            "topics/recipe.txt": _DECLARATIONS,
            "topics/selections.txt": ".. guideline-select:: .\n",
            "topics/intro.txt": "Interviewer only.\n",
        }
    )
    write_sources(source=source, files=files)
    app = make_app(
        srcdir=source,
        buildername=buildername,
        exception_on_warning=True,
        confoverrides=_configuration(),
    )
    for iteration in range(2):
        app.build()
        html = (
            Path(app.outdir) / "topics/view-interviewer-guideline.html"
        ).read_text()
        soup = BeautifulSoup(markup=html, features="html.parser")
        containers = soup.select(selector=".hr-interviewer-guideline")
        languages = ("Python", "JavaScript")
        assert len(containers) == len(languages)
        for container, language in zip(containers, languages, strict=True):
            assert "Widgets: " + language in container.get_text()
            assert [
                item.get_text()
                for item in container.select(
                    selector=":scope > details > summary"
                )
            ] == ["Shared brief", "Stage one", "Stage two", "Review"]
            assert [
                item.get_text()
                for item in container.select(
                    selector=":scope > details:nth-of-type(2) "
                    "> details > summary"
                )
            ] == [
                "Work",
                "Updated questions" if bool(iteration) else "Questions",
            ]
            assert [
                item.get_text()
                for item in container.select(
                    selector=":scope > details:nth-of-type(3) "
                    "> details > summary"
                )
            ] == ["Next steps"]
            assert container.get_text().count("What would you improve?") == 1
            assert "Make the first version." in container.get_text()
            assert "Discuss the next version." in container.get_text()
            assert "Explain your decisions." in container.get_text()
            assert (
                "Updated interview advice." in container.get_text()
            ) is bool(iteration)
            assert ("Updated questions" in container.get_text()) is bool(
                iteration
            )
            link = container.select_one(selector="a")
            assert link is not None
            assert link["href"] == "guide.html"
        tree = app.env.get_doctree(docname="topics/view-interviewer-guideline")
        introductions = [
            node
            for node in tree.findall(condition=nodes.paragraph)
            if "full guide" in node.astext()
        ]
        assert len(introductions) == len(languages)
        for introduction in introductions:
            assert introduction.source is not None
            assert Path(introduction.source).name == "recipe.txt"
        # Only the included recipe and introduction change, not the parent RST.
        _ = (source / "topics/recipe.txt").write_text(
            data=_DECLARATIONS.replace(
                "guideline-group:: Questions",
                "guideline-group:: Updated questions",
            )
        )
        _ = (source / "topics/intro.txt").write_text(
            data="Updated interview advice.\n"
        )
    dependencies = {
        str(object=path)
        for path in app.env.dependencies["topics/view-interviewer-guideline"]
    }
    for name in ("recipe.txt", "selections.txt", "intro.txt"):
        assert any(path.endswith(name) for path in dependencies)
    if buildername == "hackerrank":
        for language in ("python", "javascript"):
            fragment = (
                Path(app.outdir)
                / "interviewer-guidelines/topics/view"
                / f"{language}.html"
            )
            assert "Updated interview advice." in fragment.read_text()
    assert app.warning.getvalue() == ""


def _recipe(*, declarations: str) -> str:
    """Nest explicit declarations beneath the language composition."""
    return ".. interviewer-guideline:: guide.rst\n\n" + textwrap.indent(
        text=declarations, prefix="   "
    )


def _part(*, heading: str, selections: str) -> str:
    """Build one part for grammar and source-validation failures."""
    return (
        f".. guideline-part:: {heading}\n\n   .. guideline-group:: Work\n\n"
        + textwrap.indent(text=selections, prefix="      ")
    )


@pytest.mark.parametrize(
    argnames=("recipe", "message"),
    argvalues=[
        (
            _recipe(
                declarations=_part(
                    heading="Missing", selections=".. guideline-select:: .\n"
                )
            ),
            "Required guide parts are missing: ['Missing']",
        ),
        (
            _recipe(
                declarations=_part(
                    heading="Stage one", selections=".. guideline-select:: .\n"
                )
                + "\n"
                + _part(
                    heading="Stage one", selections=".. guideline-select:: .\n"
                )
            ),
            "must not contain duplicates",
        ),
        (
            _recipe(declarations=".. guideline-before:: Shared brief\n"),
            "nonempty names",
        ),
        (
            _recipe(declarations="Unstructured prose.\n"),
            "only accepts recipe declarations",
        ),
        (
            _recipe(
                declarations=(
                    ".. guideline-part:: Stage one\n\n   Unstructured prose.\n"
                )
            ),
            "only accepts guideline-group",
        ),
        (
            _recipe(
                declarations=(
                    ".. guideline-part:: Stage one\n\n   .. "
                    "guideline-group:: Work\n\n      Unstructured "
                    "prose.\n"
                )
            ),
            "only accepts guideline-select",
        ),
        (
            _recipe(
                declarations=_part(
                    selections=(
                        ".. guideline-select:: Discussion\n   "
                        ":alternatives: Discussion\n"
                    ),
                    heading="Stage one",
                )
            ),
            "must not contain duplicates",
        ),
        (
            _recipe(
                declarations=(
                    ".. guideline-introduction::\n\n   One.\n\n.. "
                    "guideline-introduction::\n\n   Two.\n"
                )
            ),
            "Only one guideline-introduction",
        ),
        (
            _recipe(
                declarations=_part(
                    selections=".. guideline-select:: Missing\n",
                    heading="Stage one",
                )
            ),
            "Required selection ('Missing',) missing",
        ),
        (
            _recipe(
                declarations=(
                    ".. guideline-part:: Stage one\n\n   .. "
                    "guideline-group:: First\n\n      .. "
                    "guideline-select:: .\n\n   .. guideline-group:: "
                    "Second\n\n      .. guideline-select:: .\n"
                )
            ),
            "must not contain duplicates",
        ),
        (
            ".. interviewer-guideline:: guide.rst\n   :layout: existing\n\n"
            + textwrap.indent(
                text=_part(
                    heading="Stage one", selections=".. guideline-select:: .\n"
                ),
                prefix="   ",
            ),
            "cannot be combined",
        ),
        *[
            (
                f".. {name}:: {argument}\n",
                "only allowed inside its recipe parent",
            )
            for name, argument in (
                ("guideline-part", "Stage one"),
                ("guideline-group", "Work"),
                ("guideline-select", "Brief"),
                ("guideline-before", "Brief"),
                ("guideline-after", "Review"),
                ("guideline-introduction", ""),
            )
        ],
    ],
)
def test_invalid_recipe_reports_directive_errors(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    recipe: str,
    message: str,
) -> None:
    """Malformed recipes fail during reading without leaving unknown writer
    nodes.
    """
    source = tmp_path / "source"
    write_sources(source=source, files=_sources(recipe=recipe))
    app = make_app(srcdir=source, confoverrides=_configuration())
    app.build()
    assert message in app.warning.getvalue()


def test_part_names_treat_regex_punctuation_literally(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An explicit bracketed heading never expands to similarly named
    parts.
    """
    source = tmp_path / "source"
    files = {
        **_sources(recipe=_RECIPE),
        "guide.rst": _GUIDE.replace("Stage one", "Q[1-3]")
        + "\nQ1\n--\n\nUnselected stage.\n",
        "recipe.txt": _DECLARATIONS.replace("Stage one", "Q[1-3]"),
        "selections.txt": ".. guideline-select:: .\n",
        "intro.txt": "Interviewer only.\n",
    }
    write_sources(source=source, files=files)
    app = make_app(
        srcdir=source,
        exception_on_warning=True,
        confoverrides=_configuration(),
    )
    app.build()
    html = (Path(app.outdir) / "view-interviewer-guideline.html").read_text()
    assert "Q[1-3]" in html
    assert "Unselected stage." not in html


@pytest.mark.parametrize(
    argnames="declarations",
    argvalues=[
        ":parts: Stage one\n\n"
        + _part(heading="Stage one", selections=".. guideline-select:: .\n"),
        ":part-pattern: Stage .*\n\n"
        + _part(heading="Stage one", selections=".. guideline-select:: .\n"),
        ":minimum-parts: 2\n\n"
        + _part(heading="Stage one", selections=".. guideline-select:: .\n"),
        (
            ".. guideline-part:: Stage one\n\n   .. "
            "guideline-group:: Work\n      :required-for: "
            "Stage one\n\n      .. guideline-select:: .\n"
        ),
        (
            ".. guideline-part:: Stage one\n\n   .. "
            "guideline-group:: Work\n      "
            ":required-for-pattern: Stage .*\n\n      .. "
            "guideline-select:: .\n"
        ),
    ],
)
def test_removed_selector_options_are_rejected(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    declarations: str,
) -> None:
    """Loop and conditional options cannot weaken explicit part
    selection.
    """
    source = tmp_path / "source"
    write_sources(
        source=source,
        files=_sources(
            recipe=".. interviewer-guideline:: guide.rst\n"
            + ("\n" if declarations.startswith("..") else "")
            + textwrap.indent(text=declarations, prefix="   ")
        ),
    )
    app = make_app(srcdir=source, confoverrides=_configuration())
    app.build()
    expected = (
        "single-line names"
        if "required-for" in declarations
        else "unknown option"
    )
    assert expected in app.warning.getvalue()


def test_explicit_parts_follow_declaration_order(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path
) -> None:
    """The RST controls display order independently of source order."""
    source = tmp_path / "source"
    recipe = _recipe(
        declarations=_part(
            heading="Stage two", selections=".. guideline-select:: .\n"
        )
        + "\n"
        + _part(heading="Stage one", selections=".. guideline-select:: .\n")
    )
    write_sources(source=source, files=_sources(recipe=recipe))
    app = make_app(
        srcdir=source,
        exception_on_warning=True,
        confoverrides=_configuration(),
    )
    app.build()
    soup = BeautifulSoup(
        markup=(
            Path(app.outdir) / "view-interviewer-guideline.html"
        ).read_text(),
        features="html.parser",
    )
    for container in soup.select(selector=".hr-interviewer-guideline"):
        assert [
            item.get_text()
            for item in container.select(selector=":scope > details > summary")
        ] == ["Stage two", "Stage one"]
