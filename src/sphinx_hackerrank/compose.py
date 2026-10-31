"""Apply a caller-defined layout to the maintained guide tree."""

import posixpath
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar, override

from docutils import nodes
from docutils.statemachine import StringList
from sphinx_toolbox.collapse import CollapseNode, CollapseSummaryNode

from sphinx_hackerrank.layout import GuidelineLayout
from sphinx_hackerrank.sections import (
    InterviewerGuidelineSection,
    section_content,
)
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


def _relative_section_path(
    *, section: nodes.section, ancestor: nodes.section
) -> str:
    """Describe a nested section relative to an enclosing selection."""
    path = [section[0].astext()]
    parent = section.parent
    while parent is not ancestor:
        assert isinstance(parent, nodes.section)
        path.append(parent[0].astext())
        parent = parent.parent
    return " / ".join(reversed(path))


def _selected_sections(
    *, part: nodes.section, layout: GuidelineLayout
) -> dict[str, nodes.section]:
    """Find supported categories regardless of their nesting in a part."""
    titles = {title for group in layout.groups for title in group.sections}
    found: dict[str, nodes.section] = {}
    for section in part.findall(condition=nodes.section):
        title = section[0].astext()
        if title not in titles:
            continue
        if title in found:
            message = (
                f"Ambiguous {title!r} section in guide part "
                f"{part[0].astext()!r}"
            )
            raise ValueError(message)
        found[title] = section
    return found


def _category_content(
    *,
    section: nodes.section,
    selected: dict[str, nodes.section],
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
        _relative_section_path(section=other, ancestor=section)
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
        for admonition in list(
            container.findall(
                condition=lambda node: isinstance(node, nodes.Admonition)
            )
        ):
            assert admonition.parent is not None
            _ = admonition.parent.remove(item=admonition)
    if not any(
        bool(child.astext().strip())
        for child in container.children
        if not isinstance(child, nodes.rubric)
    ):
        return []
    return container.children


def _part_content(
    *,
    part: nodes.section,
    guide: str,
    language: str,
    exclude_admonitions: bool,
    layout: GuidelineLayout,
) -> CollapseNode:
    """Arrange existing sections in the order supplied by the consumer."""
    selected = _selected_sections(part=part, layout=layout)
    categories: list[nodes.Node] = []
    for group in layout.groups:
        content: list[nodes.Node] = []
        for name in group.sections:
            if name in selected:
                content.extend(
                    _category_content(
                        section=selected[name],
                        selected=selected,
                        guide=guide,
                        language=language,
                        exclude_admonitions=exclude_admonitions,
                        include_heading=name in group.include_headings,
                    )
                )
        if bool(content):
            categories.append(_disclosure(title=group.title, content=content))
    return _disclosure(title=part[0].astext(), content=categories)


def _guide_content(
    *,
    document: nodes.document,
    guide: str,
    language: str,
    exclude_admonitions: bool,
    layout: GuidelineLayout,
) -> list[nodes.Node]:
    """Find parts and closing sections using caller-supplied headings."""
    parts = [
        section
        for section in document.findall(condition=nodes.section)
        if any(
            isinstance(child, nodes.section)
            and child[0].astext() == layout.part_marker
            for child in section.children
        )
    ]
    if not bool(parts):
        message = (
            f"No guide parts with a {layout.part_marker!r} subsection found"
        )
        raise ValueError(message)
    content: list[nodes.Node] = [
        _part_content(
            part=part,
            guide=guide,
            language=language,
            exclude_admonitions=exclude_admonitions,
            layout=layout,
        )
        for part in parts
    ]
    for heading in layout.trailing_sections:
        matches = [
            section
            for section in document.findall(condition=nodes.section)
            if section[0].astext() == heading
        ]
        if len(matches) > 1:
            message = f"Expected at most one trailing section for {heading!r}"
            raise ValueError(message)
        if bool(matches):
            trailing = _category_content(
                section=matches[0],
                selected={},
                guide=guide,
                language=language,
                exclude_admonitions=exclude_admonitions,
                include_heading=False,
            )
            if bool(trailing):
                content.append(_disclosure(title=heading, content=trailing))
    return content


class InterviewerGuideline(InterviewerGuidelineSection):
    """Compose mapped language views using the consumer's layout
    policy.
    """

    # Docutils defines option converter return values as Any.
    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {}  # pyrefly: ignore[explicit-any]

    @override
    def run(self) -> list[nodes.Node]:
        """Derive the mapped language views from the source guide."""
        layout = self.config.hackerrank_guideline_layout
        if not isinstance(layout, GuidelineLayout):
            raise self.error(
                message="interviewer-guideline requires a "
                "caller-supplied hackerrank_guideline_layout"
            )
        source_path = self._source_path()
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
                source_path=source_path, language_key=target.language
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
                self.state.document.note_implicit_target(target=root)
            container = nodes.container(
                classes=[
                    "hr-interviewer-guideline",
                    f"interviewer-guideline-{target.language}",
                ]
            )
            container += nodes.rubric("", title.astext() + ": " + language)
            container.extend(
                item=self._introduction(guide=guide, layout=layout)
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

    def _introduction(
        self, *, guide: str, layout: GuidelineLayout
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
                initlist=layout.introduction.replace(
                    "{source_url}", uri
                ).splitlines()
            ),
            input_offset=self.content_offset,
            node=container,
        )
        return container.children
