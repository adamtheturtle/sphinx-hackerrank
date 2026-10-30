"""Portable HTML preserves code while resolving local and hosted links."""

import pytest
from bs4 import BeautifulSoup, Tag

from sphinx_hackerrank.html import render_fragment


@pytest.mark.parametrize(
    argnames="source_url", argvalues=[None, "https://example.org/source/"]
)
@pytest.mark.parametrize(argnames="anchors", argvalues=[False, True])
def test_portable_fragment(*, source_url: str | None, anchors: bool) -> None:
    """Preserve code and rewrite links according to the source
    settings.
    """
    line_number = '<span class="linenos">1</span>'
    html = f"""<nav>Theme</nav><script src="theme.js"></script>
<div class="hr-interviewer-guideline interviewer-guideline-python">
<details><summary>Part 1</summary>
<p>A participant\u2019s example.</p><a class="headerlink" href="#part">#</a>
<a href="widgets.html#part-1">Guide</a><a href="https://example.org">External</a>
<a href="#local">Local</a><a href="data.pdf">PDF</a>
<pre>{line_number}<span>if x &lt; 3 &amp;&amp; y &gt; 0:</span>\n</pre>
</details></div>
<div class="interviewer-guideline-java">Other language</div>"""
    fragment = render_fragment(
        html=html,
        language="python",
        docname="topics/widgets-interviewer-guideline",
        source_url=source_url,
        source_suffix=".rst",
        source_anchors=anchors,
    )
    soup = BeautifulSoup(markup=fragment, features="html.parser")
    code = soup.select_one(selector="pre code")
    assert code is not None
    assert code.get_text() == "if x < 3 && y > 0:\n"
    assert not bool(
        soup.select(
            selector="nav,link,.interviewer-guideline-java,"
            ".headerlink,pre span"
        )
    )
    assert soup.style is not None
    script = soup.select_one(selector="script[data-hr-copy-code]")
    assert script is not None
    assert "src" not in script.attrs
    assert len(soup.select(selector="script")) == 1
    assert fragment.isascii()
    assert "participant\u2019s" in soup.get_text()
    target = (
        "../../../topics/widgets.html"
        if source_url is None
        else "https://example.org/source/topics/widgets.rst"
    )
    if anchors:
        target += "#part-1"
    expected_links = {
        "Guide": target,
        "External": "https://example.org",
        "Local": "#local",
        "PDF": "data.pdf",
    }
    for label, href in expected_links.items():
        link = soup.find(name="a", string=label)
        assert isinstance(link, Tag)
        assert link["href"] == href


@pytest.mark.parametrize(
    argnames="html",
    argvalues=[
        "<p>Missing</p>",
        '<div class="interviewer-guideline-python"></div>' * 2,
    ],
)
def test_invalid_container(*, html: str) -> None:
    """Reject fragments without exactly one matching language
    container.
    """
    with pytest.raises(
        expected_exception=ValueError,
        match="Expected one Interviewer Guideline",
    ):
        _ = render_fragment(html=html, language="python")
