"""The HackerRank builder uses Sphinx's standard HTML rendering."""

import textwrap
from base64 import b64decode
from collections.abc import Callable
from pathlib import Path
from typing import override

import pytest
from bs4 import BeautifulSoup
from docutils import nodes
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.ext.mathjax import html_visit_displaymath, html_visit_math
from sphinx.testing.util import SphinxTestApp
from sphinx.util.docutils import SphinxDirective

from sphinx_hackerrank import GuidelineExportNode
from sphinx_hackerrank.builder import HackerRankBuilder
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
    classes = "hr-interviewer-guideline"
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
                  :any:`widgets`
                  `External <https://example.org>`_
                  `Local <#local>`_
                  `PDF <data.pdf>`_

                  Inline :math:`x^2`.

                  .. math::

                     x^2

                  .. figure:: pixel.svg
                     :alt: Example image
                     :name: example-figure

                     A numbered diagram.

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
        confoverrides={
            "html_context": {"builder": "hackerrank"},
            "numfig": True,
        },
        docnames=["index", "topics/widgets", docname],
    )
    source = tmp_path / "actual"
    actual_files = {
        name: content.replace(
            f".. container:: {classes}",
            ".. hackerrank-export:: "
            "interviewer-guidelines/topics/widgets/guide.html\n"
            "   :name: Example",
        )
        for name, content in files.items()
    }
    write_sources(source=source, files=actual_files)
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        exception_on_warning=True,
        confoverrides={
            "extensions": ["sphinx_hackerrank", "sphinx_toolbox.collapse"],
            "numfig": True,
            "hackerrank_source_url": source_url,
            "hackerrank_source_suffix": ".rst",
            "hackerrank_source_anchors": anchors,
        },
    )
    app.build()
    assert not (Path(app.outdir) / (docname + ".html")).exists()
    assert not (Path(app.outdir) / "index.html").exists()
    # Export the independently built native page through the same public API.
    exported = (
        Path(app.outdir) / "interviewer-guidelines/topics/widgets/guide.html"
    ).read_text(encoding="utf-8")
    assert exported == render_fragment(
        html=str(
            object=BeautifulSoup(
                markup=expected[docname], features="html.parser"
            ).select_one(selector=".hr-interviewer-guideline")
        ),
        output_path="interviewer-guidelines/topics/widgets/guide.html",
        docname=docname,
        source_url=source_url,
        source_suffix=".rst",
        source_anchors=anchors,
        image_paths={"../_images/pixel.svg": source / "topics/pixel.svg"},
    )
    # The project IDE supplies native copy controls for exported code blocks.
    fragment_soup = BeautifulSoup(markup=exported, features="html.parser")
    assert [
        code.get_text() for code in fragment_soup.select(selector="pre > code")
    ] == ["if x < 3 && y > 0:\n"]
    assert not bool(fragment_soup.select(selector=".linenos, script, button"))

    # Editing only an image must refresh its embedded bytes incrementally.
    fragment = (
        Path(app.outdir) / "interviewer-guidelines/topics/widgets/guide.html"
    )
    previous = fragment.read_text(encoding="utf-8")
    image = source / "topics/pixel.svg"
    _ = image.write_text(
        data=image.read_text().replace("<rect", '<rect fill="red"')
    )
    app.build()
    updated = fragment.read_text(encoding="utf-8")
    assert updated != previous
    soup = BeautifulSoup(markup=updated, features="html.parser")
    picture = soup.select_one(selector="img")
    assert picture is not None
    assert (
        b64decode(s=str(object=picture["src"]).split(sep=",", maxsplit=1)[1])
        == image.read_bytes()
    )

    app.config.hackerrank_source_url = "https://new.example/source/"
    app.build()
    assert (
        "https://new.example/source/topics/widgets.rst" in fragment.read_text()
    )


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
            output_path="exports/review.html",
            image_paths={filename: image} if suffix is not None else None,
        )


class OutsideOnlyNode(nodes.General, nodes.Element):
    """An intentionally unsupported node outside the export boundary."""


class OutsideOnlyDirective(SphinxDirective):
    """Insert a node that would fail if the entire page were rendered."""

    @override
    def run(self) -> list[nodes.Node]:
        """Return an unsupported node without adding an HTML handler."""
        return [OutsideOnlyNode()]


def test_only_export_nodes_are_rendered(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path
) -> None:
    """No website, theme, asset bundle, or outside HTML visitor is
    needed.
    """
    source = tmp_path / "source"
    write_sources(
        source=source,
        files={
            "index.rst": (
                "Index\n=====\n\n.. toctree::\n\n   outside\n\n"
                ".. outside-only::\n\n"
                ".. hackerrank-export:: exports/review.html\n"
                "   :name: Review\n\n   Exported content.\n"
            ),
            "outside.rst": "Outside\n=======\n\n.. outside-only::\n",
        },
    )
    app = make_app(
        srcdir=source,
        buildername="hackerrank",
        exception_on_warning=True,
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
            "html_theme": "missing-theme",
        },
    )
    app.add_node(node=OutsideOnlyNode)
    app.add_directive(name="outside-only", cls=OutsideOnlyDirective)
    app.build()
    output = Path(app.outdir)
    assert "Exported content" in (output / "exports/review.html").read_text()
    files = {
        path.relative_to(output).as_posix()
        for path in output.rglob(pattern="*")
        if path.is_file()
    }
    assert files == {
        "exports/review.html",
        "interviewer-guidelines/index.html",
    }
    assert app.warning.getvalue() == ""


class SectionExportDirective(SphinxDirective):
    """Prepare identical section content for native and export writers."""

    has_content = True
    required_arguments = 1

    @override
    def run(self) -> list[nodes.Node]:
        """Allow nested section nodes inside the explicit boundary."""
        wrapper = (
            GuidelineExportNode(output_path="exports/inner.html", name="Inner")
            if self.arguments[0] == "hackerrank"
            else nodes.container(classes=["hr-interviewer-guideline"])
        )
        _ = self.state.nested_parse(
            block=self.content,
            input_offset=self.content_offset,
            node=wrapper,
            match_titles=True,
        )
        return [wrapper]


def test_section_context_matches_native_html(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path
) -> None:
    """An isolated section retains its original heading depth and
    anchors.
    """
    outputs: list[str] = []
    for builder in ("html", "hackerrank"):
        source = tmp_path / builder
        write_sources(
            source=source,
            files={
                "index.rst": (
                    "Document\n========\n\nOuter\n-----\n\n"
                    f".. section-export:: {builder}\n\n"
                    "   Inner\n   ~~~~~\n\n   Section content.\n"
                )
            },
        )
        app = make_app(
            srcdir=source,
            buildername=builder,
            exception_on_warning=True,
            confoverrides={"extensions": ["sphinx_hackerrank"]},
        )
        app.add_directive(name="section-export", cls=SectionExportDirective)
        app.build()
        output = Path(app.outdir)
        if builder == "html":
            soup = BeautifulSoup(
                markup=(output / "index.html").read_text(),
                features="html.parser",
            )
            node = soup.select_one(selector=".hr-interviewer-guideline")
            assert node is not None
            outputs.append(
                render_fragment(
                    html=str(object=node),
                    output_path="exports/inner.html",
                    docname="index",
                )
            )
        else:
            outputs.append((output / "exports/inner.html").read_text())
        app.cleanup()
    assert outputs[0] == outputs[1]
    assert "<h3>Inner" in outputs[1]


@pytest.mark.parametrize(
    argnames=("configured", "extra"),
    argvalues=[(None, 0), (None, 1), (None, 2), ("mathjax", 1)],
)
def test_math_renderer_selection_matches_sphinx(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    configured: str | None,
    extra: int,
) -> None:
    """HTML math extensions receive the same renderer selection as
    Sphinx.
    """
    renderers: list[str | None] = []
    for builder in ("html", "hackerrank"):
        source = tmp_path / builder
        write_sources(source=source, files={"index.rst": "Index\n=====\n"})
        app = make_app(
            srcdir=source,
            buildername=builder,
            confoverrides={
                "extensions": ["sphinx_hackerrank"],
                "html_math_renderer": configured,
            },
        )
        for index in range(extra):
            app.add_html_math_renderer(
                name=f"extra-{index}",
                inline_renderers=(html_visit_math, None),
                block_renderers=(html_visit_displaymath, None),
            )
        assert isinstance(
            app.builder, (StandaloneHTMLBuilder, HackerRankBuilder)
        )
        renderers.append(app.builder.math_renderer_name)
        app.cleanup()
    assert renderers[0] == renderers[1]
