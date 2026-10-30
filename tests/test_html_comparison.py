"""Saved HTML tolerates serialization changes but preserves content."""

import pytest

from sphinx_hackerrank.html import html_equivalent, normalize_html


@pytest.mark.parametrize(
    argnames=("left", "right"),
    argvalues=[
        ("<p>Driver&#8217;s rate</p>", "<p>Driver\u2019s rate</p>"),
        (
            "<details><summary>Q1</summary><p>Hello world</p></details>",
            (
                "<details>\n<summary>Q1</summary>\n"
                "<p> Hello   world </p>\n</details>"
            ),
        ),
        (
            '<table><colgroup><col style="width: 50.0%"/></colgroup></table>',
            (
                '<table>\n<colgroup><col style="width:50.0%;"/>'
                "</colgroup>\n</table>"
            ),
        ),
        ("<p>Hello  <em>world</em></p>", "<p>Hello <em>world</em></p>"),
        ("<p>Hello <!--keep-->world</p>", "<p>Hello <!--keep-->world</p>"),
    ],
)
def test_equivalent_serializations(*, left: str, right: str) -> None:
    """Entities, formatting indentation, and column style spacing may vary."""
    assert html_equivalent(left, right)
    assert normalize_html(html=left) == normalize_html(html=right)


@pytest.mark.parametrize(
    argnames=("left", "right"),
    argvalues=[
        ("<pre>  x\n</pre>", "<pre>x\n</pre>"),
        ("<code>a  b</code>", "<code>a b</code>"),
        (
            '<script>const x = "a  b";</script>',
            '<script>const x = "a b";</script>',
        ),
        ("<style>p { color: red; }</style>", "<style>p{color:red;}</style>"),
        ("<textarea>  x</textarea>", "<textarea>x</textarea>"),
        ("<p>Hello <em>world</em></p>", "<p>Hello<em>world</em></p>"),
        (
            "<p><em>one</em> <em>two</em></p>",
            "<p><em>one</em><em>two</em></p>",
        ),
        ("<p>one</p>", "<p>two</p>"),
        ("<details>x</details>", "<details open>x</details>"),
        ('<col style="width:50%">', '<col style="width:40%">'),
        (
            '<col style="width:50%;color:red">',
            '<col style="width:50%;color:blue">',
        ),
        ("<!--one--><p>x</p>", "<!--two--><p>x</p>"),
    ],
)
def test_meaningful_changes_are_different(*, left: str, right: str) -> None:
    """Literal whitespace, inline spacing, attributes, and text stay
    strict.
    """
    assert not html_equivalent(left, right)
