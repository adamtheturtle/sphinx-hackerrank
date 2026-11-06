"""Capture export boundaries during Sphinx's native HTML traversal."""

from sphinx.writers.html5 import HTML5Translator

from sphinx_hackerrank.builder import HackerRankBuilder
from sphinx_hackerrank.exports import GuidelineExportNode


def visit_export(
    translator: HTML5Translator, node: GuidelineExportNode
) -> None:
    """Mark the start of this boundary in Sphinx's native HTML output."""
    node["html_start"] = len(translator.body)
    translator.visit_container(node=node)


def depart_export(
    translator: HTML5Translator, node: GuidelineExportNode
) -> None:
    """Retain the page's container and export its fully rendered HTML."""
    translator.depart_container(node=node)
    builder = translator.builder
    assert isinstance(builder, HackerRankBuilder)
    builder.write_fragment(
        export=node.export,
        html="".join(translator.body[node["html_start"] :]),
    )
    del node["html_start"]
