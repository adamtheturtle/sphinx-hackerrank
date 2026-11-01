"""The public sample composes and exports one prepared document."""

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from sphinx.testing.util import SphinxTestApp


@pytest.mark.parametrize(argnames="retain_notes", argvalues=[False, True])
def test_independent_example(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    retain_notes: bool,
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
        confoverrides={"hackerrank_exclude_admonitions": not retain_notes},
    )
    app.build()
    assert app.warning.getvalue() == ""
    output = Path(app.outdir)
    html = (
        output / "interviewer-guidelines/topics/widgets/guide.html"
    ).read_text()
    assert "Print a widget" in html
    assert "print('widget')" in html
    assert ("Ask the participant" in html) is retain_notes
    assert (
        "Widget review"
        in (output / "interviewer-guidelines/index.html").read_text()
    )
    assert not bool(list(source.rglob(pattern="*.yml")))
