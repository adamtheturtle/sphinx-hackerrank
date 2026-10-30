"""Reuse parsed guide sections in language-specific Sphinx Interviewer
Guidelines.
"""

from collections.abc import Callable
from copy import copy
from pathlib import Path
from typing import Any, ClassVar, override

from docutils import nodes
from docutils.parsers.rst import Parser, directives
from docutils.transforms.references import (
    AnonymousHyperlinks,
    DanglingReferences,
    ExternalTargets,
    IndirectHyperlinks,
    InternalTargets,
    PropagateTargets,
    Substitutions,
)
from docutils.utils import new_document
from sphinx.application import Sphinx
from sphinx.transforms import DefaultSubstitutions
from sphinx.util.docutils import SphinxDirective
from sphinx_toolbox.collapse import CollapseNode, CollapseSummaryNode


def select_section(
    *, document: nodes.document | nodes.section, selector: str
) -> nodes.section:
    """Resolve an exact heading path or a standard RST section label."""
    sections: list[nodes.section] = list(
        document.findall(condition=nodes.section)
    )
    matches: list[nodes.section]
    if selector.startswith("#"):
        label = nodes.fully_normalize_name(name=selector[1:])
        matches = [
            section
            for section in sections
            if label in section["names"] or label in section["ids"]
        ]
    else:
        parts = [part.strip() for part in selector.split(sep="/")]
        matches = [
            section for section in sections if section[0].astext() == parts[0]
        ]
        for part in parts[1:]:
            matches = [
                child
                for section in matches
                for child in section.children
                if isinstance(child, nodes.section)
                and child[0].astext() == part
            ]
    if len(matches) != 1:
        msg = (
            f"Expected one guide section for {selector!r}, "
            f"found {len(matches)}"
        )
        raise ValueError(msg)
    selected = matches[0]
    assert isinstance(selected, nodes.section)
    return selected


def _rubric(title: nodes.Node) -> nodes.rubric:
    """Copy a section heading as an unnumbered rubric."""
    assert isinstance(title, nodes.title)
    rubric = nodes.rubric(rawsource=title.rawsource)
    rubric += title.deepcopy().children
    return rubric


def _copy_without_sections(
    *, section: nodes.section, exclude_sections: tuple[str, ...]
) -> nodes.section:
    """Copy a section while omitting validated descendant selections."""
    copied = section.deepcopy()
    excluded = [
        select_section(document=copied, selector=selector)
        for selector in exclude_sections
    ]
    if any(target is copied for target in excluded):
        message = "Cannot exclude the selected section itself"
        raise ValueError(message)
    excluded_ids = {id(target) for target in excluded}
    for target in list(copied.findall(condition=nodes.section)):
        if id(target) in excluded_ids:
            assert target.parent is not None
            _ = target.parent.remove(item=target)
    return copied


def section_content(
    *,
    section: nodes.section,
    guide: str,
    language: str,
    include_heading: bool,
    exclude_sections: tuple[str, ...] = (),
) -> list[nodes.Node]:
    """Copy selected nodes without importing the guide's anchors or
    language selectors.
    """
    copied = _copy_without_sections(
        section=section, exclude_sections=exclude_sections
    )
    container = nodes.container()
    if include_heading:
        container += _rubric(title=copied[0])
    container += copied.children[1:]
    for subsection in list(container.findall(condition=nodes.section)):
        subsection.replace_self(
            new=[_rubric(title=subsection[0]), *subsection.children[1:]]
        )
    for target in list(container.findall(condition=nodes.target)):
        assert target.parent is not None
        _ = target.parent.remove(item=target)
    for element in container.findall(condition=nodes.Element):
        element["ids"] = []
        element["names"] = []
        if isinstance(element, nodes.reference) and "refid" in element:
            element["refuri"] = f"{guide}.html#{element['refid']}"
            del element["refid"]
    for collapse in list(container.findall(condition=CollapseNode)):
        if collapse["label"] == language:
            collapse.replace_self(
                new=[
                    child
                    for child in collapse.children
                    if not isinstance(child, CollapseSummaryNode)
                ]
            )
    return container.children


class InterviewerGuidelineSection(SphinxDirective):
    """Include one parsed section from a maintained guide in one
    language.
    """

    required_arguments = 1
    # Docutils defines option converter return values as Any.
    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {  # pyrefly: ignore[explicit-any]
        "section": directives.unchanged_required,
        "language": directives.unchanged_required,
        "include-heading": directives.flag,
        "exclude-sections": directives.unchanged_required,
    }

    def _source_path(self) -> Path:
        """Validate the maintained RST source before parsing it."""
        source_root = Path(self.env.srcdir).resolve()
        _relative, filename = self.env.relfn2path(filename=self.arguments[0])
        source_path = Path(filename).resolve()
        if (
            not source_path.is_relative_to(source_root)
            or source_path.suffix != ".rst"
        ):
            raise self.error(
                message="Interviewer Guideline source must be an RST guide "
                "within the source directory"
            )
        if (
            source_path
            == Path(self.env.doc2path(docname=self.env.docname)).resolve()
        ):
            raise self.error(
                message="An Interviewer Guideline cannot include itself"
            )
        return source_path

    def _guide_document(
        self, *, source_path: Path, language_key: str
    ) -> tuple[nodes.document, str]:
        """Read one cached language variant and track its dependencies."""
        source_root = Path(self.env.srcdir).resolve()
        language = self.config.hackerrank_languages.get(language_key)
        if language is None:
            raise self.error(
                message=(
                    "Expected one Interviewer Guideline language config for "
                    f"{language_key!r}"
                )
            )
        self.env.note_dependency(filename=source_path)
        # Docutils stores extension attributes in an Any-valued dictionary.
        cache: dict[tuple[str, str], nodes.document] = (  # ty: ignore[unsound-assignment]
            self.state.document.attributes.setdefault(
                "_interviewer_guideline_guides", {}
            )
        )
        key = (str(object=source_path), language_key)
        if key not in cache:
            document = self._parse_guide(
                source_path=source_path,
                source_root=source_root,
                context=language.get("context", {}),
            )
            cache[key] = document
        return cache[key], str(object=language.get("name", language_key))

    @override
    def run(self) -> list[nodes.Node]:
        """Select a guide section while tracking source dependencies."""
        source_path = self._source_path()
        if "section" not in self.options or "language" not in self.options:
            raise self.error(
                message="interviewer-guideline-section requires "
                ":section: and :language:"
            )
        document, language = self._guide_document(
            source_path=source_path, language_key=self.options["language"]
        )
        guide = (
            source_path.relative_to(Path(self.env.srcdir).resolve())
            .with_suffix(suffix="")
            .as_posix()
        )
        try:
            section = select_section(
                document=document, selector=self.options["section"]
            )
            content = section_content(
                section=section,
                guide=guide,
                language=language,
                include_heading="include-heading" in self.options,
                exclude_sections=tuple(
                    selector.strip()
                    for selector in self.options.get(
                        "exclude-sections", ""
                    ).splitlines()
                    if bool(selector.strip())
                ),
            )
        except ValueError as error:
            raise self.error(message=str(object=error)) from error
        for root in content:
            for node in root.findall():
                node.document = self.state.document
        return content

    def _parse_guide(
        self,
        *,
        source_path: Path,
        source_root: Path,
        context: dict[str, object],
    ) -> nodes.document:
        """Parse a guide with the selected language context and restore
        settings.
        """
        settings = copy(x=self.state.document.settings)
        document = new_document(
            source_path=str(
                object=self.env.doc2path(docname=self.env.docname)
            ),
            settings=settings,
        )
        contexts = self.config.jinja2_contexts
        context_name = self.config.hackerrank_jinja_context
        self.config.jinja2_contexts = {
            **contexts,
            context_name: {
                **contexts.get(context_name, {}),
                **context,
            },
        }
        relative_source = source_path.relative_to(source_root).as_posix()
        try:
            source = "\n\n".join(
                part
                for part in (
                    self.config.rst_prolog or "",
                    f".. include:: /{relative_source}",
                    self.config.rst_epilog or "",
                )
                if bool(part)
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
                DanglingReferences,
            ):
                transform(document=document).apply()
        finally:
            self.config.jinja2_contexts = contexts
        return document


def discard_guide_cache(_app: Sphinx, doctree: nodes.document) -> None:
    """Keep temporary language variants out of Sphinx's persisted doctrees."""
    _ = doctree.attributes.pop("_interviewer_guideline_guides", None)


def simplify_interviewer_guideline(
    _app: Sphinx, doctree: nodes.document, _docname: str
) -> None:
    """Remove admonitions from Interviewer Guideline views after includes
    render.
    """
    if not _app.config.hackerrank_exclude_admonitions:
        return
    containers = [
        node
        for node in doctree.findall(condition=nodes.container)
        if "hr-interviewer-guideline" in node["classes"]
    ]
    for container in containers:
        for admonition in list(
            container.findall(
                condition=lambda node: isinstance(node, nodes.Admonition)
            )
        ):
            parent = admonition.parent
            assert parent is not None
            _ = parent.remove(item=admonition)
