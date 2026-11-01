"""Caller-defined selection, presentation, and completeness contracts."""

from dataclasses import dataclass


def _names(*, values: tuple[str, ...], description: str) -> None:
    """Reject empty or duplicated names before a renderer reads
    content.
    """
    if not bool(values) or any(not bool(value.strip()) for value in values):
        message = f"{description} must contain nonempty names"
        raise ValueError(message)
    if len(values) != len(set(values)):
        message = f"{description} must not contain duplicates"
        raise ValueError(message)


@dataclass(frozen=True, kw_only=True)
class SectionSelection:
    """Select one source heading, allowing explicit alternative spellings.

    A required selection must exist and retain content after filtering.
    The single heading ``.`` selects the current part's own body.
    """

    headings: tuple[str, ...]
    required: bool = True
    include_heading: bool = False

    def __post_init__(self) -> None:
        """Reject ambiguous self-selection and invalid heading names."""
        _names(values=self.headings, description="Selection headings")
        if "." in self.headings and len(self.headings) != 1:
            message = "Self-selection cannot have alternative headings"
            raise ValueError(message)


@dataclass(frozen=True, kw_only=True)
class SectionGroup:
    """Source selections to combine under one disclosure."""

    title: str
    sections: tuple[SectionSelection, ...]

    def __post_init__(self) -> None:
        """Require a display title and at least one selection."""
        _names(values=(self.title,), description="Group title")
        if not bool(self.sections):
            message = "A section group must contain selections"
            raise ValueError(message)


@dataclass(frozen=True, kw_only=True)
class GroupRequirement:
    """Require rendered groups in explicitly selected parts."""

    groups: tuple[str, ...]
    part_headings: tuple[str, ...]

    def __post_init__(self) -> None:
        """Reject requirements which cannot describe a real part set."""
        _names(values=self.part_headings, description="Part headings")
        _names(values=self.groups, description="Required groups")


@dataclass(frozen=True, kw_only=True)
class GuidelineLayout:
    """A consumer's layout and explicit content-completeness
    expectations.
    """

    groups: tuple[SectionGroup, ...]
    part_headings: tuple[str, ...]
    leading_sections: tuple[SectionSelection, ...] = ()
    trailing_sections: tuple[SectionSelection, ...] = ()
    required_groups: tuple[GroupRequirement, ...] = ()
    introduction: str = ""

    def __post_init__(self) -> None:
        """Validate the recipe before optional selections could hide a
        typo.
        """
        _names(values=self.part_headings, description="Part headings")
        _names(
            values=tuple(group.title for group in self.groups),
            description="Group titles",
        )
        _names(
            values=tuple(
                heading
                for group in self.groups
                for selection in group.sections
                for heading in selection.headings
            ),
            description="Grouped headings",
        )
        outer = self.leading_sections + self.trailing_sections
        if bool(outer):
            _names(
                values=tuple(
                    heading
                    for selection in outer
                    for heading in selection.headings
                ),
                description="Outer headings",
            )
            if any("." in selection.headings for selection in outer):
                message = "Self-selection is only allowed within parts"
                raise ValueError(message)
        group_names = {group.title for group in self.groups}
        for requirement in self.required_groups:
            unknown = set(requirement.groups) - group_names
            if bool(unknown):
                message = f"Unknown required groups: {sorted(unknown)!r}"
                raise ValueError(message)
