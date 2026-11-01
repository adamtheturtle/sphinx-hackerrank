"""Invalid completeness policies fail when the consumer constructs
them.
"""

from collections.abc import Callable

import pytest

from sphinx_hackerrank.layout import (
    GroupRequirement,
    GuidelineLayout,
    SectionGroup,
    SectionSelection,
)


@pytest.mark.parametrize(
    argnames=("factory", "message"),
    argvalues=[
        (
            lambda: GroupRequirement(groups=("Work",), part_headings=()),
            "nonempty names",
        ),
        (
            lambda: GroupRequirement(
                groups=("Work",), part_headings=("One", "One")
            ),
            "duplicates",
        ),
        (
            lambda: GuidelineLayout(groups=(), part_headings=()),
            "nonempty names",
        ),
        (
            lambda: GroupRequirement(groups=(), part_headings=("One",)),
            "nonempty names",
        ),
        (lambda: SectionSelection(headings=()), "nonempty names"),
        (lambda: SectionSelection(headings=(" ",)), "nonempty names"),
        (lambda: SectionSelection(headings=("Brief", "Brief")), "duplicates"),
        (
            lambda: SectionSelection(headings=(".", "Brief")),
            "alternative headings",
        ),
        (
            lambda: SectionGroup(title="Work", sections=()),
            "contain selections",
        ),
        (
            lambda: GuidelineLayout(part_headings=("One",), groups=()),
            "nonempty names",
        ),
        (
            lambda: GuidelineLayout(
                part_headings=("One",),
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(SectionSelection(headings=("Brief",)),),
                    ),
                ),
                leading_sections=(SectionSelection(headings=(".",)),),
            ),
            "only allowed within parts",
        ),
        (
            lambda: GuidelineLayout(
                part_headings=("One",),
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(SectionSelection(headings=("Brief",)),),
                    ),
                ),
                required_groups=(
                    GroupRequirement(
                        part_headings=("One",), groups=("Unknown",)
                    ),
                ),
            ),
            "Unknown required groups",
        ),
    ],
)
def test_invalid_layout_contract(
    *, factory: Callable[[], object], message: str
) -> None:
    """Configuration mistakes cannot turn required content into
    omissions.
    """
    with pytest.raises(expected_exception=ValueError, match=message):
        _ = factory()
