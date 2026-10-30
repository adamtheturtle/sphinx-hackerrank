"""Reuse parsed guide sections in language-specific Sphinx mini-maps."""

from __future__ import annotations

from copy import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import Parser, directives
from docutils.transforms.references import (
    AnonymousHyperlinks,
    ExternalTargets,
    IndirectHyperlinks,
    InternalTargets,
    PropagateTargets,
    Substitutions,
)
from docutils.utils import new_document
from sphinx.transforms import DefaultSubstitutions
from sphinx.util.docutils import SphinxDirective
from sphinx_toolbox.collapse import CollapseNode, CollapseSummaryNode

if TYPE_CHECKING:
    from collections.abc import Callable

    from sphinx.application import Sphinx


def select_section(*, document: nodes.document, selector: str) -> nodes.section:
    """Resolve an exact heading path or a standard RST section label."""
    sections = list(document.findall(condition=nodes.section))
    if selector.startswith("#"):
        label = nodes.fully_normalize_name(name=selector[1:])
        matches = [section for section in sections if label in section["names"] or label in section["ids"]]
    else:
        parts = [part.strip() for part in selector.split(sep="/")]
        matches = [section for section in sections if section[0].astext() == parts[0]]
        for part in parts[1:]:
            matches = [
                child
                for section in matches
                for child in section.children
                if isinstance(child, nodes.section) and child[0].astext() == part
            ]
    if len(matches) != 1:
        msg = f"Expected one guide section for {selector!r}, found {len(matches)}"
        raise ValueError(msg)
    return matches[0]


def _rubric(title: nodes.Node) -> nodes.rubric:
    assert isinstance(title, nodes.title)
    rubric = nodes.rubric(rawsource=title.rawsource)
    rubric += title.deepcopy().children
    return rubric


def section_content(*, section: nodes.section, guide: str, language: str, include_heading: bool) -> list[nodes.Node]:
    """Copy selected nodes without importing the guide's anchors or
    language selectors.
    """
    container = nodes.container()
    if include_heading:
        container += _rubric(title=section[0])
    container += [child.deepcopy() for child in section.children[1:]]
    for subsection in list(container.findall(condition=nodes.section)):
        subsection.replace_self(new=[_rubric(title=subsection[0]), *subsection.children[1:]])
    for target in list(container.findall(condition=nodes.target)):
        assert target.parent is not None
        target.parent.remove(item=target)
    for element in container.findall(condition=nodes.Element):
        element["ids"] = []
        element["names"] = []
        if isinstance(element, nodes.reference) and "refid" in element:
            element["refuri"] = f"{guide}.html#{element['refid']}"
            del element["refid"]
    for collapse in list(container.findall(condition=CollapseNode)):
        if collapse["label"] == language:
            collapse.replace_self(
                new=[child for child in collapse.children if not isinstance(child, CollapseSummaryNode)]
            )
    return container.children


class MiniMapSection(SphinxDirective):
    """Include one parsed section from a maintained guide in one
    language.
    """

    required_arguments = 1
    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        "section": directives.unchanged_required,
        "language": directives.unchanged_required,
        "include-heading": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        """Select a guide section, preserving source files and dependency
        tracking.
        """
        source_root = Path(self.env.srcdir).resolve()
        _relative, filename = self.env.relfn2path(filename=self.arguments[0])
        source_path = Path(filename).resolve()
        if not source_path.is_relative_to(source_root) or source_path.suffix != ".rst":
            raise self.error(message="Mini-map source must be an RST guide within the source directory")
        if source_path == Path(self.env.doc2path(docname=self.env.docname)).resolve():
            raise self.error(message="A mini-map cannot include itself")
        if "section" not in self.options or "language" not in self.options:
            raise self.error(message="mini-map-section requires :section: and :language:")
        language = self.config.hackerrank_languages.get(self.options["language"])
        if language is None:
            raise self.error(message=f"Expected one mini-map language config for {self.options['language']!r}")
        self.env.note_dependency(filename=source_path)
        cache: dict[tuple[str, str], nodes.document] = self.state.document.attributes.setdefault("_mini_map_guides", {})
        key = (str(object=source_path), self.options["language"])
        if key not in cache:
            settings = copy(x=self.state.document.settings)
            document = new_document(
                source_path=str(object=self.env.doc2path(docname=self.env.docname)), settings=settings
            )
            contexts = self.config.jinja2_contexts
            context_name = self.config.hackerrank_jinja_context
            self.config.jinja2_contexts = {
                **contexts,
                context_name: {**contexts.get(context_name, {}), **language.get("context", {})},
            }
            try:
                source = "\n\n".join(
                    part
                    for part in (
                        self.config.rst_prolog or "",
                        f".. include:: /{source_path.relative_to(source_root).as_posix()}",
                        self.config.rst_epilog or "",
                    )
                    if part
                )
                Parser().parse(inputstring=source, document=document)
                for transform in (
                    DefaultSubstitutions,
                    Substitutions,
                    PropagateTargets,
                    AnonymousHyperlinks,
                    IndirectHyperlinks,
                    ExternalTargets,
                    InternalTargets,
                ):
                    transform(document=document).apply()
            finally:
                self.config.jinja2_contexts = contexts
            cache[key] = document
        try:
            section = select_section(document=cache[key], selector=self.options["section"])
        except ValueError as error:
            raise self.error(message=str(object=error)) from error
        content = section_content(
            section=section,
            guide=source_path.relative_to(source_root).with_suffix(suffix="").as_posix(),
            language=language.get("name", self.options["language"]),
            include_heading="include-heading" in self.options,
        )
        for root in content:
            for node in root.findall():
                node.document = self.state.document
        return content


def discard_guide_cache(_app: Sphinx, doctree: nodes.document) -> None:
    """Keep temporary language variants out of Sphinx's persisted doctrees."""
    doctree.attributes.pop("_mini_map_guides", None)


def simplify_mini_map(_app: Sphinx, doctree: nodes.document, docname: str) -> None:
    """Remove admonitions from mini-map views after includes render."""
    if not _app.config.hackerrank_exclude_admonitions:
        return
    containers = [node for node in doctree.findall(condition=nodes.container) if "hr-mini-map" in node["classes"]]
    for container in containers:
        for admonition in list(container.findall(condition=lambda node: isinstance(node, nodes.Admonition))):
            parent = admonition.parent
            assert parent is not None
            parent.remove(item=admonition)
