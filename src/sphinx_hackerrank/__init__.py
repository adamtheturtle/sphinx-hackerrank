"""Sphinx extension for portable HackerRank interviewer mini-maps."""

from importlib.metadata import version

from sphinx.application import Sphinx

from sphinx_hackerrank.builder import HackerRankBuilder
from sphinx_hackerrank.sections import (
    MiniMapSection,
    discard_guide_cache,
    simplify_mini_map,
)

__version__ = version(distribution_name="sphinx-hackerrank")


def setup(app: Sphinx) -> dict[str, object]:
    """Register the builder, directive, and project-independent
    settings.
    """
    app.setup_extension(extname="sphinx_jinja2")
    app.setup_extension(extname="sphinx_toolbox.collapse")
    app.add_config_value(
        name="hackerrank_manifest_pattern",
        default="**/*-mini-map.yml",
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
    app.add_directive(name="mini-map-section", cls=MiniMapSection)
    _ = app.connect(event="doctree-read", callback=discard_guide_cache)
    _ = app.connect(event="doctree-resolved", callback=simplify_mini_map)
    return {
        "version": __version__,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
