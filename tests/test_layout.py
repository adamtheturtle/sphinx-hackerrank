"""Invalid explicit layouts fail before any content is selected."""

from collections.abc import Callable

import pytest

from sphinx_hackerrank.layout import (
    GuidelineLayout,
    GuidelinePart,
    SectionGroup,
    SectionSelection,
)

_GROUP = SectionGroup(
    title="Work", sections=(SectionSelection(headings=("Brief",)),)
)


@pytest.mark.parametrize(
    argnames=("factory", "message"),
    argvalues=[
        (lambda: GuidelineLayout(parts=()), "nonempty names"),
        (
            lambda: GuidelinePart(heading=" ", groups=(_GROUP,)),
            "nonempty names",
        ),
        (lambda: GuidelinePart(heading="One", groups=()), "nonempty names"),
        (
            lambda: GuidelinePart(heading="One", groups=(_GROUP, _GROUP)),
            "duplicates",
        ),
        (
            lambda: GuidelinePart(
                heading="One",
                groups=(
                    _GROUP,
                    SectionGroup(title="Other", sections=_GROUP.sections),
                ),
            ),
            "duplicates",
        ),
        (
            lambda: GuidelineLayout(
                parts=(
                    GuidelinePart(heading="One", groups=(_GROUP,)),
                    GuidelinePart(heading="One", groups=(_GROUP,)),
                )
            ),
            "duplicates",
        ),
        (
            lambda: SectionSelection(headings=("Brief\nCases",)),
            "single-line names",
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
            lambda: GuidelineLayout(
                parts=(GuidelinePart(heading="One", groups=(_GROUP,)),),
                leading_sections=(SectionSelection(headings=(".",)),),
            ),
            "only allowed within parts",
        ),
    ],
)
def test_invalid_layout_contract(
    *, factory: Callable[[], object], message: str
) -> None:
    """Typos cannot turn mandatory selections into silent omissions."""
    with pytest.raises(expected_exception=ValueError, match=message):
        _ = factory()
