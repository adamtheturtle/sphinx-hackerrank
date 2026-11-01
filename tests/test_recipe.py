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
_RECIPE = r""".. interviewer-guideline:: guide.rst
   :parts: Stage .*
   :minimum-parts: 2

   .. include:: recipe.txt
"""
_DECLARATIONS = """\
.. guideline-introduction::

   .. include:: intro.txt

   See the `full guide <{source_url}>`_.

.. guideline-before:: Shared brief

.. guideline-group:: Work
   :required-for: Stage .*
   :minimum-parts: 2

   .. include:: selections.txt

.. guideline-group:: Questions

   .. guideline-select:: Discussion
      :alternatives: Discussions
                     Discussion topics
      :optional:
      :include-heading:

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


@pytest.mark.parametrize(
    argnames=("recipe", "message"),
    argvalues=[
        (
            ".. interviewer-guideline:: guide.rst\n   :minimum-parts: 2\n",
            "requires :parts:",
        ),
        (
            (
                ".. interviewer-guideline:: guide.rst\n"
                "\n"
                "   .. guideline-group:: Work\n"
                "\n"
                "      .. guideline-select:: .\n"
            ),
            "requires :parts:",
        ),
        (
            (
                ".. interviewer-guideline:: guide.rst\n"
                "   :parts: Stage .*\n"
                "   :layout: existing\n"
            ),
            "cannot be combined",
        ),
        (
            (
                ".. interviewer-guideline:: guide.rst\n"
                "   :parts: [\n"
                "\n"
                "   .. guideline-group:: Work\n"
                "\n"
                "      .. guideline-select:: .\n"
            ),
            "Invalid part pattern",
        ),
        (
            ".. interviewer-guideline:: guide.rst\n   :parts: Stage .*\n",
            "nonempty names",
        ),
        (
            (
                ".. interviewer-guideline:: guide.rst\n"
                "   :parts: Stage .*\n"
                "\n"
                "   Unstructured prose.\n"
            ),
            "only accepts recipe declarations",
        ),
        (
            (
                ".. interviewer-guideline:: guide.rst\n"
                "   :parts: Stage .*\n"
                "\n"
                "   .. guideline-group:: Work\n"
                "\n"
                "      Unstructured prose.\n"
            ),
            "only accepts guideline-select",
        ),
        (
            (
                ".. interviewer-guideline:: guide.rst\n"
                "   :parts: Stage .*\n"
                "\n"
                "   .. guideline-group:: Work\n"
                "      :minimum-parts: 2\n"
                "\n"
                "      .. guideline-select:: .\n"
            ),
            "requires required-for",
        ),
        (
            (
                ".. interviewer-guideline:: guide.rst\n"
                "   :parts: Stage .*\n"
                "\n"
                "   .. guideline-group:: Work\n"
                "      :required-for: [\n"
                "\n"
                "      .. guideline-select:: .\n"
            ),
            "Invalid part pattern",
        ),
        (
            (
                ".. interviewer-guideline:: guide.rst\n"
                "   :parts: Stage .*\n"
                "\n"
                "   .. guideline-group:: Work\n"
                "\n"
                "      .. guideline-select:: Discussion\n"
                "         :alternatives: Discussion\n"
            ),
            "must not contain duplicates",
        ),
        (
            (
                ".. interviewer-guideline:: guide.rst\n"
                "   :parts: Stage .*\n"
                "\n"
                "   .. guideline-introduction::\n"
                "\n"
                "      One.\n"
                "\n"
                "   .. guideline-introduction::\n"
                "\n"
                "      Two.\n"
            ),
            "Only one guideline-introduction",
        ),
        (
            (
                ".. interviewer-guideline:: guide.rst\n"
                "   :parts: Stage .*\n"
                "\n"
                "   .. guideline-group:: Work\n"
                "\n"
                "      .. guideline-select:: Missing\n"
            ),
            "Required selection ('Missing',) missing",
        ),
        *[
            (
                f".. {name}:: {argument}\n",
                "only allowed inside its recipe parent",
            )
            for name, argument in (
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
