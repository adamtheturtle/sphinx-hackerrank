"""Portable HTML preserves code while resolving local and hosted links."""

import pytest
from bs4 import BeautifulSoup

from sphinx_hackerrank.html import render_fragment


@pytest.mark.parametrize("source_url", [None, "https://example.org/source/"])
@pytest.mark.parametrize("anchors", [False, True])
def test_portable_fragment(source_url, anchors):
    html = """<nav>Theme</nav><script src="theme.js"></script>
<div class="hr-mini-map mini-map-python"><details><summary>Part 1</summary>
<p>A participant\u2019s example.</p><a class="headerlink" href="#part">#</a>
<a href="widgets.html#part-1">Guide</a><a href="https://example.org">External</a>
<a href="#local">Local</a><a href="data.pdf">PDF</a>
<pre><span>if x &lt; 3 &amp;&amp; y &gt; 0:</span>\n</pre></details></div>
<div class="mini-map-java">Other language</div>"""
    fragment = render_fragment(
        html=html,
        language="python",
        docname="topics/widgets-mini-map",
        source_url=source_url,
        source_suffix=".rst",
        source_anchors=anchors,
    )
    soup = BeautifulSoup(fragment, "html.parser")
    assert soup.select_one("pre code").get_text() == "if x < 3 && y > 0:\n"
    assert not soup.select("nav,script,link,.mini-map-java,.headerlink,pre span")
    assert soup.style and fragment.isascii()
    assert "participant\u2019s" in soup.get_text()
    target = "../../../topics/widgets.html" if source_url is None else "https://example.org/source/topics/widgets.rst"
    if anchors:
        target += "#part-1"
    assert soup.find("a", string="Guide")["href"] == target
    assert soup.find("a", string="External")["href"] == "https://example.org"
    assert soup.find("a", string="Local")["href"] == "#local"
    assert soup.find("a", string="PDF")["href"] == "data.pdf"


@pytest.mark.parametrize("html", ["<p>Missing</p>", '<div class="mini-map-python"></div>' * 2])
def test_invalid_container(html):
    with pytest.raises(ValueError, match="Expected one mini-map"):
        render_fragment(html=html, language="python")
