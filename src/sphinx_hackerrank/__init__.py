"""Sphinx extension for portable HackerRank Interviewer Guidelines."""

from importlib.metadata import version
from pathlib import Path

from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.util.typing import ExtensionMetadata

from sphinx_hackerrank.builder import HackerRankBuilder
from sphinx_hackerrank.exports import (
    GuidelineExportDirective,
    GuidelineExportNode,
    HackerRankDomain,
    native_export_containers,
)
from sphinx_hackerrank.writer import depart_export, visit_export

__all__ = ["GuidelineExportNode"]

__version__ = version(distribution_name="sphinx-hackerrank")


def _add_static_path(_app: Sphinx, config: Config) -> None:
    """Make the guideline assets available to themed HTML pages."""
    config.html_static_path = [
        *config.html_static_path,
        str(object=Path(__file__).parent / "static"),
    ]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register portable HTML export and its scoped styles."""
    _ = app.connect(event="config-inited", callback=_add_static_path)
    app.add_css_file(filename="interviewer_guideline.css")
    app.add_node(node=GuidelineExportNode, html=(visit_export, depart_export))
    app.add_directive(name="hackerrank-export", cls=GuidelineExportDirective)
    app.add_domain(domain=HackerRankDomain)
    _ = app.connect(
        event="doctree-resolved", callback=native_export_containers, priority=0
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
    app.add_builder(builder=HackerRankBuilder)
    return {
        "version": __version__,
        "env_version": 2,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
