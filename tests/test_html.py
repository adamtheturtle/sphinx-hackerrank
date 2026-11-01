"""The HackerRank builder uses Sphinx's standard HTML rendering."""

import textwrap
from base64 import b64decode
from collections.abc import Callable
from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from sphinx.testing.util import SphinxTestApp

from sphinx_hackerrank import GuidelineExport
from sphinx_hackerrank.html import render_fragment
from tests.builds import build_expected, write_sources


@pytest.mark.parametrize(
    argnames="source_url", argvalues=[None, "https://example.org/source/"]
)
@pytest.mark.parametrize(argnames="anchors", argvalues=[False, True])
def test_builder_matches_html_builder(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    source_url: str | None,
    anchors: bool,
) -> None:
    """Compare pages and exported fragments to a native HTML build."""
    docname = "topics/widgets-interviewer-guideline"
    classes = "hr-interviewer-guideline selected-guide"
    files = {
        "index.rst": textwrap.dedent(
            text="""\
            Index
            =====

            .. toctree::

               topics/widgets-interviewer-guideline
               topics/widgets
            """
        ),
        "topics/widgets.rst": "Widgets\n=======\n\nPart 1\n------\n",
        "topics/pixel.svg": (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="1" height="1"><rect width="1" height="1"/></svg>'
        ),
        f"{docname}.rst": textwrap.dedent(
            text=f"""\
            Interviewer Guideline
            =====================

            .. container:: {classes}

               .. collapse:: Part 1

                  A participant\u2019s example.

                  `Guide <widgets.html#part-1>`_
                  `External <https://example.org>`_
                  `Local <#local>`_
                  `PDF <data.pdf>`_

                  .. image:: pixel.svg
                     :alt: Example image

                  .. code-block:: text
                     :linenos:
                     :caption: Example
                     :name: example-code

                     if x < 3 && y > 0:

            .. container:: other-guide

               Other language.
            """
        ),
    }
    expected = build_expected(
        make_app=make_app,
        source=tmp_path / "expected",
        files=files,
        confoverrides={"html_context": {"builder": "hackerrank"}},
        docnames=["index", "topics/widgets", docname],
    )
    source = tmp_path / "actual"
    write_sources(source=source, files=files)
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        exception_on_warning=True,
        confoverrides={
            "extensions": ["sphinx_hackerrank", "sphinx_toolbox.collapse"],
            "hackerrank_exports": [
                GuidelineExport(
                    docname=docname,
                    selector=".selected-guide",
                    output_path="interviewer-guidelines/topics/widgets/guide.html",
                    name="Example",
                )
            ],
            "hackerrank_source_url": source_url,
            "hackerrank_source_suffix": ".rst",
            "hackerrank_source_anchors": anchors,
        },
    )
    app.build()
    for name, html in expected.items():
        assert (Path(app.outdir) / f"{name}.html").read_text(
            encoding="utf-8"
        ) == html
    # Export the independently built native page through the same public API.
    assert (
        Path(app.outdir) / "interviewer-guidelines/topics/widgets/guide.html"
    ).read_text(encoding="utf-8") == render_fragment(
        html=expected[docname],
        selector=".selected-guide",
        output_path="interviewer-guidelines/topics/widgets/guide.html",
        docname=docname,
        source_url=source_url,
        source_suffix=".rst",
        source_anchors=anchors,
        image_paths={"../_images/pixel.svg": source / "topics/pixel.svg"},
    )


@pytest.mark.parametrize(argnames="containers", argvalues=[0, 2])
def test_invalid_container(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    containers: int,
) -> None:
    """Reject RST without exactly one matching language container."""
    source = tmp_path / "source"
    write_sources(
        source=source,
        files={
            "index.rst": "Index\n=====\n",
            "index-interviewer-guideline.rst": (
                "Interviewer Guideline\n=====================\n\n"
                + textwrap.dedent(
                    text="""\
                    .. container:: selected-guide

                       Example.

                    """
                )
                * containers
            ),
        },
    )
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
            "suppress_warnings": ["toc.not_included"],
            "hackerrank_exports": [
                GuidelineExport(
                    docname="index-interviewer-guideline",
                    selector=".selected-guide",
                    output_path="interviewer-guidelines/example.html",
                    name="Example",
                )
            ],
        },
    )
    with pytest.raises(
        expected_exception=ValueError,
        match="Expected one Interviewer Guideline",
    ):
        app.build()


@pytest.mark.parametrize(
    argnames="uri", argvalues=["picture.svg", "picture.svg#part"]
)
def test_embedded_images_preserve_bytes_and_fragments(
    *, tmp_path: Path, uri: str
) -> None:
    """Images and their links retain their bytes outside the build
    tree.
    """
    image = tmp_path / "picture.svg"
    content = (
        b'<svg xmlns="http://www.w3.org/2000/svg"><rect id="part"/></svg>'
    )
    _ = image.write_bytes(data=content)
    html = (
        f'<div class="guide"><a href="{uri}">'
        f'<img src="{uri}" alt="Diagram"></a>'
        '<img src="picture.svg">'
        '<img src="https://example.org/remote.png">'
        '<img src="//example.org/other.png"></div>'
    )
    result = BeautifulSoup(
        markup=render_fragment(
            html=html,
            selector=".guide",
            output_path="exports/review.html",
            image_paths={"picture.svg": image},
        ),
        features="html.parser",
    )
    embedded = result.select_one(selector="img")
    assert embedded is not None
    data = str(object=embedded["src"])
    assert data.startswith("data:image/svg+xml;base64,")
    assert (
        b64decode(
            s=data.split(sep=",", maxsplit=1)[1].split(sep="#", maxsplit=1)[0]
        )
        == content
    )
    assert data.endswith("#part") is uri.endswith("#part")
    link = result.select_one(selector="a")
    assert link is not None
    assert link["href"] == data
    assert embedded["alt"] == "Diagram"
    assert (
        result.select(selector="img")[2]["src"]
        == "https://example.org/remote.png"
    )
    assert result.select(selector="img")[3]["src"] == "//example.org/other.png"


@pytest.mark.parametrize(
    argnames="suffix", argvalues=[None, ".unknown", ".txt"]
)
def test_missing_or_unsupported_image_fails(
    *, tmp_path: Path, suffix: str | None
) -> None:
    """A fragment cannot silently retain a broken local image URL."""
    filename = "picture" + (".unknown" if suffix is None else suffix)
    image = tmp_path / filename
    _ = image.write_bytes(data=b"unrecognized image")
    with pytest.raises(
        expected_exception=ValueError,
        match=r"Unsupported image|No local image",
    ):
        _ = render_fragment(
            html=f'<div class="guide"><img src="{filename}"></div>',
            selector=".guide",
            output_path="exports/review.html",
            image_paths={filename: image} if suffix is not None else None,
        )
