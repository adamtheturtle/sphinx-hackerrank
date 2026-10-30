"""Derive a standard Interviewer Guideline from the maintained guide
tree.
"""

import posixpath
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar, override

from docutils import nodes
from sphinx_toolbox.collapse import CollapseNode, CollapseSummaryNode

from sphinx_hackerrank.sections import (
    InterviewerGuidelineSection,
    section_content,
)
from sphinx_hackerrank.targets import load_targets

_CATEGORIES = (
    ("Prompt", ("Prompt",)),
    ("FAQ", ("FAQ",)),
    (
        "Signals and edge-case questions",
        ("Follow up questions", "Key considerations"),
    ),
    ("Test cases", ("Test cases",)),
)


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


def _selected_sections(*, part: nodes.section) -> dict[str, nodes.section]:
    """Find supported categories regardless of their nesting in a part."""
    titles = {title for _label, group in _CATEGORIES for title in group}
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
        include_heading=section[0].astext() == "Key considerations",
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
) -> CollapseNode:
    """Arrange a part's existing sections in the standard category
    order.
    """
    selected = _selected_sections(part=part)
    categories: list[nodes.Node] = []
    for label, names in _CATEGORIES:
        content: list[nodes.Node] = []
        for name in names:
            if name in selected:
                content.extend(
                    _category_content(
                        section=selected[name],
                        selected=selected,
                        guide=guide,
                        language=language,
                        exclude_admonitions=exclude_admonitions,
                    )
                )
        if bool(content):
            categories.append(_disclosure(title=label, content=content))
    return _disclosure(title=part[0].astext(), content=categories)


def _guide_content(
    *,
    document: nodes.document,
    guide: str,
    language: str,
    exclude_admonitions: bool,
) -> list[nodes.Node]:
    """Find every question part and the optional evaluation section."""
    parts = [
        section
        for section in document.findall(condition=nodes.section)
        if any(
            isinstance(child, nodes.section) and child[0].astext() == "Prompt"
            for child in section.children
        )
    ]
    if not bool(parts):
        message = "No question parts with a Prompt section found in the guide"
        raise ValueError(message)
    content: list[nodes.Node] = [
        _part_content(
            part=part,
            guide=guide,
            language=language,
            exclude_admonitions=exclude_admonitions,
        )
        for part in parts
    ]
    evaluations = [
        section
        for section in document.findall(condition=nodes.section)
        if section[0].astext() == "Evaluation"
    ]
    if len(evaluations) > 1:
        message = "Expected at most one Evaluation section in the guide"
        raise ValueError(message)
    if bool(evaluations):
        evaluation = _category_content(
            section=evaluations[0],
            selected={},
            guide=guide,
            language=language,
            exclude_admonitions=exclude_admonitions,
        )
        if bool(evaluation):
            content.append(_disclosure(title="Evaluation", content=evaluation))
    return content


class InterviewerGuideline(InterviewerGuidelineSection):
    """Compose all mapped languages from the guide's own section structure."""

    # Docutils defines option converter return values as Any.
    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {}  # pyrefly: ignore[explicit-any]

    @override
    def run(self) -> list[nodes.Node]:
        """Derive the mapped language views from the source guide."""
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
            container += self._introduction(guide=guide)
            try:
                container.extend(
                    item=_guide_content(
                        document=document,
                        guide=guide,
                        language=language,
                        exclude_admonitions=self.config.hackerrank_exclude_admonitions,
                    )
                )
            except ValueError as error:
                raise self.error(message=str(object=error)) from error
            root += container
        for node in root.findall():
            node.document = self.state.document
        return [root]

    def _introduction(self, *, guide: str) -> nodes.paragraph:
        """Link to the maintained guide with the configured source URL."""
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
        introduction = nodes.paragraph(
            "",
            "Interviewer only. "
            "Share prompts and test cases as you reach each part. See the ",
        )
        introduction += nodes.reference("", "full guide", refuri=uri)
        introduction += nodes.Text(
            data=" for interview setup and reference solutions."
        )
        return introduction
