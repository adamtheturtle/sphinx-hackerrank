"""Read generic composition declarations from native RST directives."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, ClassVar, Literal, override

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective

from sphinx_hackerrank.layout import (
    GuidelineLayout,
    GuidelinePart,
    SectionGroup,
    SectionSelection,
)


class _Recipe(nodes.container):
    """Identify the parent of top-level recipe declarations."""


class _PartBody(nodes.container):
    """Identify the parent of a part's group declarations."""


class _GroupBody(nodes.container):
    """Identify a group body while its selections are parsed."""


@dataclass(frozen=True, kw_only=True)
class _OuterSelection:
    """Place a source selection before or after discovered parts."""

    position: Literal["before", "after"]
    selection: SectionSelection


class _Declaration(nodes.Element):
    """Carry typed recipe data until the enclosing directive consumes
    it.
    """

    def __init__(
        self,
        *,
        value: StringList | SectionGroup | GuidelinePart | _OuterSelection,
    ) -> None:
        """Keep recipe data out of the rendered document tree."""
        super().__init__()
        self.value = value


class _SelectionNode(nodes.Element):
    """Carry one selection while the enclosing group is parsed."""

    def __init__(self, *, selection: SectionSelection) -> None:
        """Store a validated source selection."""
        super().__init__()
        self.selection = selection


def _selection(*, directive: SphinxDirective) -> SectionSelection:
    """Translate native directive options into a validated selection."""
    alternatives = directive.options.get("alternatives", "")
    assert isinstance(alternatives, str)
    return SectionSelection(
        headings=(
            directive.arguments[0],
            *(
                line.strip()
                for line in alternatives.splitlines()
                if bool(line.strip())
            ),
        ),
        required="optional" not in directive.options,
        include_heading="include-heading" in directive.options,
    )


def _require_parent(
    *,
    directive: SphinxDirective,
    parent: type[_Recipe] | type[_PartBody] | type[_GroupBody],
) -> None:
    """Reject declarations outside their enclosing recipe or group."""
    if not isinstance(directive.state.parent, parent):
        message = f"{directive.name} is only allowed inside its recipe parent"
        raise directive.error(message=message)


class GuidelineIntroduction(SphinxDirective):
    """Declare introductory RST, rendered with the maintained source
    URL.
    """

    has_content = True

    @override
    def run(self) -> list[nodes.Node]:
        """Keep introduction markup for the composition container."""
        _require_parent(directive=self, parent=_Recipe)
        self.assert_has_content()
        return [_Declaration(value=StringList(initlist=self.content))]


class GuidelineSelect(SphinxDirective):
    """Declare a required or optional heading selection inside a group."""

    required_arguments = 1
    final_argument_whitespace = True
    position: ClassVar[Literal["before", "after"] | None] = None
    # Docutils defines option converter return values as Any.
    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {  # pyrefly: ignore[explicit-any]
        "alternatives": directives.unchanged_required,
        "optional": directives.flag,
        "include-heading": directives.flag,
    }

    @override
    def run(self) -> list[nodes.Node]:
        """Create a selection without reading or copying source
        content.
        """
        _require_parent(
            directive=self,
            parent=_GroupBody if self.position is None else _Recipe,
        )
        try:
            selection = _selection(directive=self)
        except ValueError as error:
            raise self.error(message=str(object=error)) from error
        if self.position is None:
            return [_SelectionNode(selection=selection)]
        return [
            _Declaration(
                value=_OuterSelection(
                    position=self.position, selection=selection
                )
            )
        ]


class GuidelineBefore(GuidelineSelect):
    """Select shared content to display before discovered parts."""

    position: ClassVar[Literal["before", "after"] | None] = "before"


class GuidelineAfter(GuidelineSelect):
    """Select closing content to display after discovered parts."""

    position: ClassVar[Literal["before", "after"] | None] = "after"


class GuidelineGroup(SphinxDirective):
    """Group selections under a caller-supplied display title."""

    required_arguments = 1
    final_argument_whitespace = True
    has_content = True

    @override
    def run(self) -> list[nodes.Node]:
        """Parse the selections declared for this part's group."""
        _require_parent(directive=self, parent=_PartBody)
        self.assert_has_content()
        body = _GroupBody()
        _ = self.state.nested_parse(
            block=self.content, input_offset=self.content_offset, node=body
        )
        selections: list[SectionSelection] = []
        for child in body.children:
            if not isinstance(child, _SelectionNode):
                raise self.error(
                    message="A guideline group only accepts "
                    "guideline-select declarations"
                )
            selections.append(child.selection)
        try:
            group = SectionGroup(
                title=self.arguments[0], sections=tuple(selections)
            )
        except ValueError as error:
            raise self.error(message=str(object=error)) from error
        return [_Declaration(value=group)]


class GuidelinePartDirective(SphinxDirective):
    """Declare one exact source part and its own groups."""

    required_arguments = 1
    final_argument_whitespace = True
    has_content = True

    @override
    def run(self) -> list[nodes.Node]:
        """Keep each part's selections independent of other parts."""
        _require_parent(directive=self, parent=_Recipe)
        self.assert_has_content()
        body = _PartBody()
        _ = self.state.nested_parse(
            block=self.content, input_offset=self.content_offset, node=body
        )
        groups: list[SectionGroup] = []
        for child in body.children:
            if not isinstance(child, _Declaration) or not isinstance(
                child.value, SectionGroup
            ):
                raise self.error(
                    message="A guideline part only accepts "
                    "guideline-group declarations"
                )
            groups.append(child.value)
        try:
            part = GuidelinePart(
                heading=self.arguments[0], groups=tuple(groups)
            )
        except ValueError as error:
            raise self.error(message=str(object=error)) from error
        return [_Declaration(value=part)]


def parse_recipe(
    *, directive: SphinxDirective
) -> tuple[GuidelineLayout, StringList]:
    """Read explicit RST parts before rendering a prepared guide."""
    recipe = _Recipe()
    _ = directive.state.nested_parse(
        block=directive.content,
        input_offset=directive.content_offset,
        node=recipe,
    )
    parts: list[GuidelinePart] = []
    leading: list[SectionSelection] = []
    trailing: list[SectionSelection] = []
    introductions: list[StringList] = []
    for child in recipe.children:
        if not isinstance(child, _Declaration):
            message = "A guideline recipe only accepts recipe declarations"
            raise TypeError(message)
        value = child.value
        if isinstance(value, GuidelinePart):
            parts.append(value)
        elif isinstance(value, _OuterSelection):
            destination = leading if value.position == "before" else trailing
            destination.append(value.selection)
        else:
            assert isinstance(value, StringList)
            introductions.append(value)
    if len(introductions) > 1:
        message = "Only one guideline-introduction is allowed"
        raise ValueError(message)
    introduction = introductions[0] if bool(introductions) else StringList()
    layout = GuidelineLayout(
        parts=tuple(parts),
        leading_sections=tuple(leading),
        trailing_sections=tuple(trailing),
    )
    return layout, introduction
