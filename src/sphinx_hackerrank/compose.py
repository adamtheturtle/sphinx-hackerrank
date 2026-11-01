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
from sphinx_hackerrank.targets import load_targets


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
    language: str,
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
        language=language,
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
    language: str,
    exclude_admonitions: bool,
) -> list[nodes.Node]:
    """Require meaningful content for mandatory selections after filtering."""
    content = _category_content(
        section=section,
        selected=selected,
        guide=guide,
        language=language,
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
    language: str,
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
                        language=language,
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
    language: str,
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
            language=language,
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
    language: str,
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
        language=language,
        exclude_admonitions=exclude_admonitions,
    )
    for part, declaration in zip(parts, layout.parts, strict=True):
        content.append(
            _part_content(
                part=part,
                guide=guide,
                language=language,
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
            language=language,
            exclude_admonitions=exclude_admonitions,
        )
    )
    return content


class InterviewerGuideline(SphinxDirective):
    """Compose mapped language views using the consumer's layout
    policy.
    """

    required_arguments = 1
    has_content = True

    @override
    def run(self) -> list[nodes.Node]:
        """Derive the mapped language views from the source guide."""
        self.assert_has_content()
        try:
            layout, introduction = parse_recipe(directive=self)
            source_path = resolve_source(
                directive=self, source=self.arguments[0]
            )
        except (TypeError, ValueError) as error:
            raise self.error(message=str(object=error)) from error
        source_root = Path(self.env.srcdir).resolve()
        guide = (
            source_path.relative_to(source_root)
            .with_suffix(suffix="")
            .as_posix()
        )
        targets = load_targets(
            source_dir=source_root,
            pattern=self.config.hackerrank_manifest_pattern,
        ).get(self.env.docname)
        if targets is None:
            raise self.error(
                message="interviewer-guideline requires "
                "an adjacent language mapping"
            )
        self.env.note_dependency(filename=targets[0].metadata_path)
        root = nodes.section()
        for target in targets:
            document, language = self._guide_document(
                language_key=target.language
            )
            title = next(document.findall(condition=nodes.title), None)
            if title is None:
                raise self.error(
                    message="Interviewer Guideline source requires "
                    "a guide title"
                )
            if not bool(root.children):
                title_text = (
                    title.astext() + ": HackerRank Interviewer Guidelines"
                )
                root += nodes.title("", title_text)
                root["names"].append(
                    nodes.fully_normalize_name(name=title_text)
                )
                self.state.document.note_implicit_target(target=root)
            container = nodes.container(
                classes=[
                    "hr-interviewer-guideline",
                    f"interviewer-guideline-{target.language}",
                ]
            )
            container += nodes.rubric("", title.astext() + ": " + language)
            container.extend(
                item=self._introduction(guide=guide, introduction=introduction)
            )
            try:
                container.extend(
                    item=_guide_content(
                        document=document,
                        guide=guide,
                        language=language,
                        exclude_admonitions=self.config.hackerrank_exclude_admonitions,
                        layout=layout,
                    )
                )
            except ValueError as error:
                raise self.error(message=str(object=error)) from error
            root += container
        for node in root.findall():
            node.document = self.state.document
        return [root]

    def _guide_document(
        self, *, language_key: str
    ) -> tuple[nodes.document, str]:
        """Read each mapped language once and track its dependencies."""
        language = self.config.hackerrank_languages.get(language_key)
        if language is None:
            raise self.error(
                message=(
                    "Expected one Interviewer Guideline language config for "
                    f"{language_key!r}"
                )
            )
        contexts = self.config.jinja2_contexts
        context_name = self.config.hackerrank_jinja_context
        self.config.jinja2_contexts = {
            **contexts,
            context_name: {
                **contexts.get(context_name, {}),
                **language.get("context", {}),
            },
        }
        try:
            document = read_document(
                directive=self,
                source=self.arguments[0],
                docname=self.env.docname,
            )
        finally:
            self.config.jinja2_contexts = contexts
        return document, str(object=language.get("name", language_key))

    def _introduction(
        self, *, guide: str, introduction: StringList
    ) -> list[nodes.Node]:
        """Render the consumer's introductory RST with its source URL."""
        source_url = self.config.hackerrank_source_url
        uri = (
            source_url.rstrip("/")
            + "/"
            + guide
            + self.config.hackerrank_source_suffix
            if source_url is not None
            else posixpath.relpath(
                path=guide + ".html",
                start=posixpath.dirname(self.env.docname),
            )
        )
        container = nodes.container()
        _ = self.state.nested_parse(
            block=StringList(
                initlist=[
                    line.replace("{source_url}", uri) for line in introduction
                ],
                items=introduction.items.copy(),
            ),
            input_offset=0,
            node=container,
        )
        if self.config.hackerrank_exclude_admonitions:
            _discard_admonitions(container=container)
        return container.children
