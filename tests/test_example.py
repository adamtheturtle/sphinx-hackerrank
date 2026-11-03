"""The public sample composes and exports one prepared document."""

import shutil
from collections.abc import Callable
from pathlib import Path

from bs4 import BeautifulSoup
from sphinx.testing.util import SphinxTestApp


def test_independent_example(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A standalone consumer needs no question mapping or language
    registry.
    """
    example = Path(__file__).resolve().parents[1] / "sample/source"
    source = tmp_path / "source"
    _ = shutil.copytree(src=example, dst=source)
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        exception_on_warning=True,
    )
    app.build()
    assert app.warning.getvalue() == ""
    output = Path(app.outdir)
    html = (
        output / "interviewer-guidelines/topics/widgets/guide.html"
    ).read_text()
    fragment = BeautifulSoup(markup=html, features="html.parser")
    assert fragment.find(name="script") is None
    assert "const copyText" not in html
    preview_path = (
        output / "interviewer-guidelines/topics/widgets/guide.preview.html"
    )
    preview = BeautifulSoup(
        markup=preview_path.read_text(), features="html.parser"
    )
    assert preview.select_one(selector="script[data-hr-copy-code]") is not None
    assert [node.get_text() for node in preview.select(selector="pre")] == [
        node.get_text() for node in fragment.select(selector="pre")
    ]
    index = (output / "interviewer-guidelines/index.html").read_text()
    assert "topics/widgets/guide.preview.html" in index
    preview_path.unlink()
    app.build()
    assert preview_path.is_file()
    assert "Print a widget" in html
    assert "print('widget')" in html
    assert "Ask the participant" in html
    assert (
        "Widget review"
        in (output / "interviewer-guidelines/index.html").read_text()
    )
    assert not bool(list(source.rglob(pattern="*.yml")))
