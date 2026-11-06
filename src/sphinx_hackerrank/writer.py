"""Render a resolved export boundary with Sphinx's HTML translator."""

from docutils import nodes
from sphinx.builders import Builder
from sphinx.writers.html5 import HTML5Translator

from sphinx_hackerrank.exports import GuidelineExportNode


def visit_export(
    translator: HTML5Translator, node: GuidelineExportNode
) -> None:
    """Render the export as a standard styled container."""
    translator.visit_container(node=node)


def depart_export(
    translator: HTML5Translator, node: GuidelineExportNode
) -> None:
    """Close the container without capturing a whole-page rendering."""
    translator.depart_container(node=node)


def render_export(
    *, builder: Builder, document: nodes.document, node: GuidelineExportNode
) -> str:
    """Visit only the export, preserving its original document context."""
    translator = builder.create_translator(document, builder)
    assert isinstance(translator, HTML5Translator)
    parent = node.parent
    while parent is not None:
        if isinstance(parent, nodes.section):
            translator.section_level += 1
        parent = parent.parent
    _ = node.walkabout(visitor=translator)
    return "".join(translator.body)
