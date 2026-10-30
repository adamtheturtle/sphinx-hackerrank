"""Build native RST expectations with Sphinx's standard HTML builder."""

from collections.abc import Callable
from pathlib import Path

from sphinx.testing.util import SphinxTestApp

import sphinx_hackerrank


def write_sources(*, source: Path, files: dict[str, str]) -> None:
    """Write a small documentation project with an empty configuration."""
    source.mkdir(parents=True)
    (source / "conf.py").touch()
    for name, content in files.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(data=content, encoding="utf-8")


def build_expected(
    *,
    make_app: Callable[..., SphinxTestApp],
    source: Path,
    files: dict[str, str],
    confoverrides: dict[str, object],
    docnames: list[str],
) -> dict[str, str]:
    """Render hand-expanded RST without loading the extension under
    test.
    """
    write_sources(source=source, files=files)
    app = make_app(
        srcdir=source,
        buildername="html",
        exception_on_warning=True,
        confoverrides={
            **confoverrides,
            "extensions": ["sphinx_jinja2", "sphinx_toolbox.collapse"],
            "html_static_path": [
                str(object=Path(sphinx_hackerrank.__file__).parent / "static")
            ],
            "html_css_files": ["interviewer_guideline.css"],
            "html_js_files": ["interviewer_guideline.js"],
        },
    )
    app.build()
    assert app.statuscode == 0
    assert app.warning.getvalue() == ""
    outputs = {
        docname: (Path(app.outdir) / f"{docname}.html").read_text(
            encoding="utf-8"
        )
        for docname in docnames
    }
    app.cleanup()
    return outputs
