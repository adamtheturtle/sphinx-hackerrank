"""A separate consumer exercises custom layout, contexts, and rendering policies."""

import shutil
from importlib.metadata import version
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from sphinx_hackerrank import __version__


@pytest.mark.parametrize("retain_notes", [False, True])
def test_independent_example(make_app, tmp_path, retain_notes):
    source = tmp_path / "unrelated-documentation"
    example = Path(__file__).resolve().parents[1] / "examples/minimal/manual"
    shutil.copytree(example, source)
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        confoverrides={
            "hackerrank_exclude_admonitions": not retain_notes,
        },
    )
    app.build()
    assert app.statuscode == 0
    assert not app.warning.getvalue()
    assert __version__ == version("sphinx-hackerrank")
    output = Path(app.outdir)
    full = BeautifulSoup((output / "topics/widgets.html").read_text(encoding="utf-8"), "html.parser")
    assert full.select(".admonition")
    index = output / "mini-maps/index.html"
    links = BeautifulSoup(index.read_text(encoding="utf-8"), "html.parser").select("li a")
    assert len(links) == 2
    for link in links:
        path = index.parent / link["href"]
        assert path.is_file()
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        assert bool(soup.select(".admonition")) == retain_notes
        assert soup.find("summary", string="Alternate inputs")
        assert not soup.find("summary", string="Python")
        assert not soup.find("summary", string="JavaScript")
        assert soup.find("a", string="full guide")["href"] == "../../../topics/widgets.html"
    python = BeautifulSoup((output / "mini-maps/topics/widgets/python.html").read_text(encoding="utf-8"), "html.parser")
    assert "print('widget')" in python.get_text()
    assert "console.log" not in python.get_text()
