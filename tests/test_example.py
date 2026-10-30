"""A separate consumer exercises custom layout, contexts, and rendering
policies.
"""

import shutil
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path

import pytest
from bs4 import BeautifulSoup, Tag
from sphinx.testing.util import SphinxTestApp

from sphinx_hackerrank import __version__


@pytest.mark.parametrize(argnames="retain_notes", argvalues=[False, True])
def test_independent_example(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    retain_notes: bool,
) -> None:
    """Build portable fragments from the independently copied sample."""
    source = tmp_path / "unrelated-documentation"
    example = Path(__file__).resolve().parents[1] / "sample/source"
    _ = shutil.copytree(src=example, dst=source)
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        confoverrides={
            "hackerrank_exclude_admonitions": not retain_notes,
        },
    )
    app.build()
    assert app.statuscode == 0
    assert app.warning.getvalue() == ""
    assert __version__ == version(distribution_name="sphinx-hackerrank")
    output = Path(app.outdir)
    full = BeautifulSoup(
        markup=(output / "topics/widgets.html").read_text(encoding="utf-8"),
        features="html.parser",
    )
    assert bool(full.select(selector=".admonition"))
    index = output / "interviewer-guidelines/index.html"
    links = BeautifulSoup(
        markup=index.read_text(encoding="utf-8"), features="html.parser"
    ).select(selector="li a")
    expected_languages = 2
    assert len(links) == expected_languages
    for link in links:
        href = link["href"]
        assert isinstance(href, str)
        path = index.parent / href
        assert path.is_file()
        soup = BeautifulSoup(
            markup=path.read_text(encoding="utf-8"), features="html.parser"
        )
        assert bool(soup.select(selector=".admonition")) == retain_notes
        assert soup.find(name="summary", string="Alternate inputs") is not None
        assert soup.find(name="summary", string="Python") is None
        assert soup.find(name="summary", string="JavaScript") is None
        prompt = soup.find(name="summary", string="Prompt")
        follow_up = soup.find(name="summary", string="Follow up questions")
        assert isinstance(prompt, Tag)
        assert isinstance(prompt.parent, Tag)
        assert isinstance(follow_up, Tag)
        assert isinstance(follow_up.parent, Tag)
        question = "How would you handle an empty widget name?"
        assert question not in prompt.parent.get_text()
        assert question in follow_up.parent.get_text()
        assert soup.get_text().count(question) == 1
        guide = soup.find(name="a", string="full guide")
        assert isinstance(guide, Tag)
        assert guide["href"] == "../../../topics/widgets.html"
    python = BeautifulSoup(
        markup=(
            output / "interviewer-guidelines/topics/widgets/python.html"
        ).read_text(encoding="utf-8"),
        features="html.parser",
    )
    assert "print('widget')" in python.get_text()
    assert "console.log" not in python.get_text()
