"""Sphinx extension for portable HackerRank Interviewer Guidelines."""

from importlib.metadata import version
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.util.typing import ExtensionMetadata

from sphinx_hackerrank.builder import HackerRankBuilder
from sphinx_hackerrank.exports import (
    GuidelineExportDirective,
    GuidelineExportNode,
    HackerRankDomain,
    is_metadata_sequence,
    native_export_containers,
)
from sphinx_hackerrank.publisher import HackerRankPublishBuilder
from sphinx_hackerrank.writer import depart_export, visit_export

__all__ = ["GuidelineExportNode"]

__version__: str = version(distribution_name="sphinx-hackerrank")


@runtime_checkable
class _ConfigRegistrar(Protocol):
    """The configuration registration interface used by this extension."""

    def add_config_value(
        self,
        *,
        name: str,
        default: object,
        rebuild: Literal["html"],
        types: type[object] | tuple[type[object], ...],
    ) -> None:
        """Register an HTML configuration option."""
        ...


def _add_static_path(_app: Sphinx, config: Config) -> None:
    """Make the guideline assets available to themed HTML pages."""
    static_paths: object = config["html_static_path"]
    assert is_metadata_sequence(static_paths)
    config.html_static_path = [
        *static_paths,
        str(object=Path(__file__).parent / "static"),
    ]


def _register_config(*, registrar: _ConfigRegistrar) -> None:
    """Register settings for rendering and publishing."""
    registrar.add_config_value(
        name="hackerrank_source_url",
        default=None,
        rebuild="html",
        types=(str, type(None)),
    )
    registrar.add_config_value(
        name="hackerrank_source_suffix",
        default=".html",
        rebuild="html",
        types=str,
    )
    registrar.add_config_value(
        name="hackerrank_source_anchors",
        default=True,
        rebuild="html",
        types=bool,
    )
    registrar.add_config_value(
        name="hackerrank_api_operations",
        default=[],
        rebuild="html",
        types=list,
    )


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
    app.add_builder(builder=HackerRankBuilder)
    app.add_builder(builder=HackerRankPublishBuilder)
    _register_config(registrar=app)
    return {
        "version": __version__,
        "env_version": 3,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
