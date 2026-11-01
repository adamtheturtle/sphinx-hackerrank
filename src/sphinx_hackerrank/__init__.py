"""Sphinx extension for portable HackerRank Interviewer Guidelines."""

from importlib.metadata import version
from pathlib import Path

from sphinx.application import Sphinx
from sphinx.config import Config

from sphinx_hackerrank.builder import HackerRankBuilder
from sphinx_hackerrank.compose import InterviewerGuideline
from sphinx_hackerrank.recipe import (
    GuidelineAfter,
    GuidelineBefore,
    GuidelineGroup,
    GuidelineIntroduction,
    GuidelinePartDirective,
    GuidelineSelect,
)

__version__ = version(distribution_name="sphinx-hackerrank")


def _add_static_path(_app: Sphinx, config: Config) -> None:
    """Make the guideline assets available to themed HTML pages."""
    config.html_static_path = [
        *config.html_static_path,
        str(object=Path(__file__).parent / "static"),
    ]


def setup(app: Sphinx) -> dict[str, object]:
    """Register the builder, directive, and project-independent
    settings.
    """
    app.setup_extension(extname="sphinx_jinja2")
    app.setup_extension(extname="sphinx_toolbox.collapse")
    _ = app.connect(event="config-inited", callback=_add_static_path)
    app.add_css_file(filename="interviewer_guideline.css")
    app.add_js_file(filename="interviewer_guideline.js")
    app.add_config_value(
        name="hackerrank_manifest_pattern",
        default="**/*-interviewer-guideline.yml",
        rebuild="env",
        types=str,
    )
    app.add_config_value(
        name="hackerrank_languages", default={}, rebuild="env", types=dict
    )
    app.add_config_value(
        name="hackerrank_jinja_context",
        default="languages",
        rebuild="env",
        types=str,
    )
    app.add_config_value(
        name="hackerrank_source_url",
        default=None,
        rebuild="html",
        types=(str, type(None)),
    )
    app.add_config_value(
        name="hackerrank_source_suffix",
        default=".html",
        rebuild="html",
        types=str,
    )
    app.add_config_value(
        name="hackerrank_source_anchors",
        default=True,
        rebuild="html",
        types=bool,
    )
    app.add_config_value(
        name="hackerrank_exclude_admonitions",
        default=True,
        rebuild="html",
        types=bool,
    )
    app.add_builder(builder=HackerRankBuilder)
    app.add_directive(name="interviewer-guideline", cls=InterviewerGuideline)
    app.add_directive(name="guideline-introduction", cls=GuidelineIntroduction)
    app.add_directive(name="guideline-part", cls=GuidelinePartDirective)
    app.add_directive(name="guideline-group", cls=GuidelineGroup)
    app.add_directive(name="guideline-select", cls=GuidelineSelect)
    app.add_directive(name="guideline-before", cls=GuidelineBefore)
    app.add_directive(name="guideline-after", cls=GuidelineAfter)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
