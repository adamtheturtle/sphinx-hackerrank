"""The public sample composes and exports one prepared document."""

import shutil
from collections.abc import Callable
from pathlib import Path

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
    assert "Print a widget" in html
    assert "print('widget')" in html
    assert "Ask the participant" in html
    assert (
        "Widget review"
        in (output / "interviewer-guidelines/index.html").read_text()
    )
    assert not bool(list(source.rglob(pattern="*.yml")))
