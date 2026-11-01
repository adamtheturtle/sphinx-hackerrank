"""Apply a caller-defined layout to the maintained guide tree."""

import posixpath
from pathlib import Path
from typing import override

from docutils import nodes
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective
from sphinx_section_include import find_sections, read_document, resolve_source
from sphinx_toolbox.collapse import CollapseNode, CollapseSummaryNode

from sphinx_hackerrank.layout import (
    GuidelineLayout,
    GuidelinePart,
    SectionSelection,
)
from sphinx_hackerrank.recipe import parse_recipe
from sphinx_hackerrank.sections import section_content


def _disclosure(*, title: str, content: list[nodes.Node]) -> CollapseNode:
    """Build the same disclosure nodes as the native collapse
    directive.
    """
    disclosure = CollapseNode(
        "", title, classes=[f"summary-{nodes.make_id(string=title)}"]
    )
    disclosure += CollapseSummaryNode(title, "", nodes.Text(data=title))
    disclosure.extend(item=content)
    return disclosure


def _discard_admonitions(*, container: nodes.container) -> None:
    """Filter source and introductory content before it is rendered."""
    for admonition in list(
        container.findall(
            condition=lambda node: isinstance(node, nodes.Admonition)
        )
    ):
        assert admonition.parent is not None
        _ = admonition.parent.remove(item=admonition)


def _scope_title(*, scope: nodes.document | nodes.section) -> str:
    """Describe a source scope in a validation error."""
    return next(scope.findall(condition=nodes.title)).astext()


def _resolve_selection(
    *,
    scope: nodes.document | nodes.section,
    selection: SectionSelection,
) -> nodes.section | None:
    """Find exactly one configured alternative without guessing or merging."""
    if selection.headings == (".",):
        assert isinstance(scope, nodes.section)
        return scope
    matches = list(
        {
            id(section): section
            for heading in selection.headings
            for section in find_sections(document=scope, selector=heading)
            if section is not scope
        }.values()
    )
    if len(matches) > 1:
        message = (
            f"Ambiguous selection {selection.headings!r} "
            f"in {_scope_title(scope=scope)!r}"
        )
        raise ValueError(message)
    if bool(matches):
        return matches[0]
    if selection.required:
        message = (
            f"Required selection {selection.headings!r} "
            f"missing in {_scope_title(scope=scope)!r}"
        )
        raise ValueError(message)
    return None


def _selected_sections(
    *,
    part: nodes.section,
    layout: GuidelinePart,
) -> dict[SectionSelection, nodes.section]:
    """Resolve configured selections at any depth beneath a matched
    part.
    """
    found: dict[SectionSelection, nodes.section] = {}
    for group in layout.groups:
        for selection in group.sections:
            section = _resolve_selection(scope=part, selection=selection)
            if section is not None:
                found[selection] = section
    return found


def _category_content(
    *,
    section: nodes.section,
    selected: dict[SectionSelection, nodes.section],
    guide: str,
    exclude_admonitions: bool,
    include_heading: bool,
) -> list[nodes.Node]:
    """Copy a category without duplicating separately grouped
    descendants.
    """
    descendants = list(section.findall(condition=nodes.section))
    exclusions = tuple(
        other
        for other in selected.values()
        if other is not section
        and any(other is child for child in descendants)
    )
    content = section_content(
        section=section,
        guide=guide,
        include_heading=include_heading,
        exclude_sections=exclusions,
    )
    container = nodes.container()
    container.extend(item=content)
    # Parser diagnostics are already reported and do not make a category
    # visible in HTML. Repeated native headings commonly create INFO nodes.
    for message in list(container.findall(condition=nodes.system_message)):
        assert message.parent is not None
        _ = message.parent.remove(item=message)
    if exclude_admonitions:
        _discard_admonitions(container=container)
    if not any(
        bool(child.astext().strip())
        for child in container.children
        if not isinstance(child, nodes.rubric)
    ):
        return []
    return container.children


def _selection_content(
    *,
    section: nodes.section,
    selection: SectionSelection,
    selected: dict[SectionSelection, nodes.section],
    guide: str,
    exclude_admonitions: bool,
) -> list[nodes.Node]:
    """Require meaningful content for mandatory selections after filtering."""
    content = _category_content(
        section=section,
        selected=selected,
        guide=guide,
        exclude_admonitions=exclude_admonitions,
        include_heading=selection.include_heading,
    )
    if selection.required and not bool(content):
        message = (
            f"Required selection {selection.headings!r} "
            "is empty after filtering"
        )
        raise ValueError(message)
    return content


def _part_content(
    *,
    part: nodes.section,
    guide: str,
    exclude_admonitions: bool,
    layout: GuidelinePart,
) -> CollapseNode:
    """Render this part's explicitly declared groups."""
    selected = _selected_sections(part=part, layout=layout)
    categories: list[nodes.Node] = []
    for group in layout.groups:
        content: list[nodes.Node] = []
        for selection in group.sections:
            if selection in selected:
                content.extend(
                    _selection_content(
                        section=selected[selection],
                        selection=selection,
                        selected=selected,
                        guide=guide,
                        exclude_admonitions=exclude_admonitions,
                    )
                )
        if bool(content):
            categories.append(_disclosure(title=group.title, content=content))
    if not bool(categories):
        message = f"Guide part {part[0].astext()!r} has no rendered content"
        raise ValueError(message)
    return _disclosure(title=part[0].astext(), content=categories)


def _require_parts(*, available: set[str], required: tuple[str, ...]) -> None:
    """Reject every missing heading in an explicit part list."""
    missing = set(required) - available
    if bool(missing):
        message = f"Required guide parts are missing: {sorted(missing)!r}"
        raise ValueError(message)


def _find_parts(
    *, document: nodes.document, layout: GuidelineLayout
) -> list[nodes.section]:
    """Identify parts by their own headings, independently of body
    selections.
    """
    parts = [
        section
        for section in document.findall(condition=nodes.section)
        if section[0].astext() in tuple(part.heading for part in layout.parts)
    ]
    _require_parts(
        available={part[0].astext() for part in parts},
        required=tuple(part.heading for part in layout.parts),
    )
    titles = [part[0].astext() for part in parts]
    if len(titles) != len(set(titles)):
        message = "Matched guide parts have duplicate headings"
        raise ValueError(message)
    identities = {id(part) for part in parts}
    for part in parts:
        parent = part.parent
        while parent is not None:
            if id(parent) in identities:
                message = (
                    "Matched guide parts must not be nested within each other"
                )
                raise ValueError(message)
            parent = parent.parent
    by_title = {part[0].astext(): part for part in parts}
    return [by_title[part.heading] for part in layout.parts]


def _outer_content(
    *,
    document: nodes.document,
    selections: tuple[SectionSelection, ...],
    parts: list[nodes.section],
    guide: str,
    exclude_admonitions: bool,
) -> list[nodes.Node]:
    """Render leading or closing selections without duplicating part
    content.
    """
    content: list[nodes.Node] = []
    for selection in selections:
        section = _resolve_selection(scope=document, selection=selection)
        if section is None:
            continue
        descendants = {
            id(node) for node in section.findall(condition=nodes.section)
        }
        if any(
            id(part) in descendants
            or any(
                node is section
                for node in part.findall(condition=nodes.section)
            )
            for part in parts
        ):
            message = (
                f"Outer selection {selection.headings!r} overlaps a guide part"
            )
            raise ValueError(message)
        body = _selection_content(
            section=section,
            selection=selection,
            selected={},
            guide=guide,
            exclude_admonitions=exclude_admonitions,
        )
        if bool(body):
            content.append(
                _disclosure(title=section[0].astext(), content=body)
            )
    return content


def _guide_content(
    *,
    document: nodes.document,
    guide: str,
    exclude_admonitions: bool,
    layout: GuidelineLayout,
) -> list[nodes.Node]:
    """Validate all matched parts and apply consumer-owned completeness
    rules.
    """
    parts = _find_parts(document=document, layout=layout)
    content = _outer_content(
        document=document,
        selections=layout.leading_sections,
        parts=parts,
        guide=guide,
        exclude_admonitions=exclude_admonitions,
    )
    for part, declaration in zip(parts, layout.parts, strict=True):
        content.append(
            _part_content(
                part=part,
                guide=guide,
                exclude_admonitions=exclude_admonitions,
                layout=declaration,
            )
        )
    content.extend(
        _outer_content(
            document=document,
            selections=layout.trailing_sections,
            parts=parts,
            guide=guide,
            exclude_admonitions=exclude_admonitions,
        )
    )
    return content


def compose_guide(
    *,
    directive: SphinxDirective,
    document: nodes.document,
    layout: GuidelineLayout,
    introduction: StringList,
    guide: str,
    title: str,
) -> nodes.container:
    """Compose one prepared document using the caller's recipe and
    title.
    """
    container = nodes.container(classes=["hr-interviewer-guideline"])
    container += nodes.rubric("", title)
    container.extend(
        item=_introduction(
            directive=directive,
            guide=guide,
            introduction=introduction,
        )
    )
    container.extend(
        item=_guide_content(
            document=document,
            guide=posixpath.relpath(
                path=guide, start=posixpath.dirname(directive.env.docname)
            ),
            layout=layout,
            exclude_admonitions=directive.config.hackerrank_exclude_admonitions,
        )
    )
    for node in container.findall():
        node.document = directive.state.document
    return container


def _introduction(
    *,
    directive: SphinxDirective,
    guide: str,
    introduction: StringList,
) -> list[nodes.Node]:
    """Render introductory RST with a link to its maintained source."""
    source_url = directive.config.hackerrank_source_url
    uri = (
        source_url.rstrip("/")
        + "/"
        + guide
        + directive.config.hackerrank_source_suffix
        if source_url is not None
        else posixpath.relpath(
            path=guide + ".html",
            start=posixpath.dirname(directive.env.docname),
        )
    )
    container = nodes.container()
    _ = directive.state.nested_parse(
        block=StringList(
            initlist=[
                line.replace("{source_url}", uri) for line in introduction
            ],
            items=introduction.items.copy(),
        ),
        input_offset=0,
        node=container,
    )
    if directive.config.hackerrank_exclude_admonitions:
        _discard_admonitions(container=container)
    return container.children


class InterviewerGuideline(SphinxDirective):
    """Compose one guide in the active Sphinx context."""

    required_arguments = 1
    has_content = True

    @override
    def run(self) -> list[nodes.Node]:
        """Read one document and apply its explicit composition recipe."""
        self.assert_has_content()
        try:
            result = self._compose()
        except (TypeError, ValueError) as error:
            raise self.error(message=str(object=error)) from error
        return result

    def _compose(self) -> list[nodes.Node]:
        """Prepare and compose the requested source content."""
        layout, introduction = parse_recipe(directive=self)
        path = resolve_source(directive=self, source=self.arguments[0])
        guide = (
            path.relative_to(Path(self.env.srcdir).resolve())
            .with_suffix(suffix="")
            .as_posix()
        )
        document = read_document(
            directive=self,
            source=self.arguments[0],
            docname=self.env.docname,
        )
        title = next(document.findall(condition=nodes.title), None)
        if title is None:
            message = "Interviewer Guideline source requires a guide title"
            raise ValueError(message)
        title_text = title.astext() + ": HackerRank Interviewer Guidelines"
        root = nodes.section()
        root += nodes.title("", title_text)
        root["names"].append(nodes.fully_normalize_name(name=title_text))
        self.state.document.note_implicit_target(target=root)
        root += compose_guide(
            directive=self,
            document=document,
            layout=layout,
            introduction=introduction,
            guide=guide,
            title=title.astext(),
        )
        for node in root.findall():
            node.document = self.state.document
        return [root]
