"""An independent consumer renders like hand-expanded native RST."""

import shutil
import textwrap
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path

import pytest
from sphinx.testing.util import SphinxTestApp

from sphinx_hackerrank import __version__
from sphinx_hackerrank.html import render_fragment
from tests.builds import build_expected


@pytest.mark.parametrize(argnames="retain_notes", argvalues=[False, True])
def test_independent_example(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    retain_notes: bool,
) -> None:
    """Compare the copied sample with independently written native RST."""
    example = Path(__file__).resolve().parents[1] / "sample/source"
    variants = [
        {"name": "Python", "lexer": "python", "prompt": "print('widget')"},
        {
            "name": "JavaScript",
            "lexer": "javascript",
            "prompt": "console.log('widget');",
        },
    ]
    guideline = (
        "Widget Interviewer Guideline\n============================\n\n"
    )
    for variant in variants:
        classes = (
            "hr-interviewer-guideline "
            f"interviewer-guideline-{variant['lexer']}"
        )
        guideline += textwrap.dedent(
            text=f"""\
            .. container:: {classes}

               .. rubric:: Widgets: {variant["name"]}

               See the :doc:`full guide <widgets>`.

               .. collapse:: Part 1

                  .. collapse:: Prompt

                     Print a widget's name.

                     .. code-block:: {variant["lexer"]}
                        :class: summary-{variant["lexer"]}

                        {variant["prompt"]}

                     .. collapse:: Alternate inputs

                        .. code-block:: text

                           widget = ""

            """
        )
        if retain_notes:
            guideline += (
                "         .. tip:: Ask the participant to explain "
                "their choice.\n\n"
            )
        guideline += textwrap.indent(
            text=textwrap.dedent(
                text="""\
                .. collapse:: Follow up questions

                   How would you handle an empty widget name?

                .. collapse:: FAQ

                   The widget's name is always a string.

                """
            ),
            prefix="      ",
        )
    docname = "topics/widgets-interviewer-guideline"
    expected = build_expected(
        make_app=make_app,
        source=tmp_path / "expected",
        files={
            "index.rst": (example / "index.rst").read_text(encoding="utf-8"),
            "topics/widgets.rst": (example / "topics/widgets.rst").read_text(
                encoding="utf-8"
            ),
            f"{docname}.rst": guideline,
        },
        confoverrides={
            "project": "Widget exercise",
            "html_context": {"builder": "hackerrank"},
            "jinja2_contexts": {"snippets": {"variants": variants}},
        },
        docnames=["index", "topics/widgets", docname],
    )
    source = tmp_path / "unrelated-documentation"
    _ = shutil.copytree(src=example, dst=source)
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        exception_on_warning=True,
        confoverrides={
            "hackerrank_exclude_admonitions": not retain_notes,
        },
    )
    app.build()
    assert app.statuscode == 0
    assert app.warning.getvalue() == ""
    assert __version__ == version(distribution_name="sphinx-hackerrank")
    output = Path(app.outdir)
    for name, html in expected.items():
        assert (output / f"{name}.html").read_text(encoding="utf-8") == html
    assert (output / "interviewer-guidelines/index.html").is_file()
    for variant in variants:
        fragment = (
            output
            / "interviewer-guidelines/topics/widgets"
            / f"{variant['lexer']}.html"
        )
        assert fragment.read_text(encoding="utf-8") == render_fragment(
            html=expected[docname], language=variant["lexer"], docname=docname
        )
