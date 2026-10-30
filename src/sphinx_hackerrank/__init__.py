"""Sphinx extension for portable HackerRank interviewer mini-maps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx_hackerrank.builder import HackerRankBuilder
from sphinx_hackerrank.sections import MiniMapSection, discard_guide_cache, simplify_mini_map

if TYPE_CHECKING:
    from sphinx.application import Sphinx

__version__ = "2026.10.30.1"


def setup(app: Sphinx) -> dict[str, object]:
    """Register the builder, directive, and project-independent settings."""
    app.setup_extension("sphinx_jinja2")
    app.setup_extension("sphinx_toolbox.collapse")
    app.add_config_value("hackerrank_manifest_pattern", "**/*-mini-map.yml", "env", types=str)
    app.add_config_value("hackerrank_languages", {}, "env", types=dict)
    app.add_config_value("hackerrank_jinja_context", "languages", "env", types=str)
    app.add_config_value("hackerrank_source_url", None, "html", types=(str, type(None)))
    app.add_config_value("hackerrank_source_suffix", ".html", "html", types=str)
    app.add_config_value("hackerrank_source_anchors", True, "html", types=bool)
    app.add_config_value("hackerrank_exclude_admonitions", True, "html", types=bool)
    app.add_builder(HackerRankBuilder)
    app.add_directive("mini-map-section", MiniMapSection)
    app.connect("doctree-read", discard_guide_cache)
    app.connect("doctree-resolved", simplify_mini_map)
    return {"version": __version__, "parallel_read_safe": True, "parallel_write_safe": True}
