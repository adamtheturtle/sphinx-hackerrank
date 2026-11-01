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
            lambda: GroupRequirement(part_pattern="", groups=("Work",)),
            "must not be empty",
        ),
        (
            lambda: GroupRequirement(part_pattern="[", groups=("Work",)),
            "Invalid part pattern",
        ),
        (
            lambda: GroupRequirement(
                part_pattern=".*", groups=("Work",), minimum_parts=0
            ),
            "positive minimum_parts",
        ),
        (
            lambda: GuidelineLayout(
                part_pattern=".*", groups=(), minimum_parts=0
            ),
            "positive minimum_parts",
        ),
        (
            lambda: GuidelineLayout(part_pattern=".*", groups=()),
            "nonempty names",
        ),
        (
            lambda: GuidelineLayout(
                part_pattern=".*",
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
                part_pattern=".*",
                groups=(
                    SectionGroup(
                        title="Work",
                        sections=(SectionSelection(headings=("Brief",)),),
                    ),
                ),
                required_groups=(
                    GroupRequirement(part_pattern=".*", groups=("Unknown",)),
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
