"""Render standalone HTML without a theme or external assets."""

import posixpath
from importlib.resources import files
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


def fragment_path(*, output_dir: Path, docname: str, language: str) -> Path:
    """Locate a language fragment in a builder output directory."""
    return (
        output_dir
        / "interviewer-guidelines"
        / docname.removesuffix("-interviewer-guideline")
        / f"{language}.html"
    )


def render_fragment(
    *,
    html: str,
    language: str,
    docname: str = "interviewer-guideline",
    source_url: str | None = None,
    source_suffix: str = ".html",
    source_anchors: bool = True,
) -> str:
    """Extract a language view, retaining exact code and portable
    links.
    """
    soup = BeautifulSoup(markup=html, features="html.parser")
    containers = soup.select(selector=f".interviewer-guideline-{language}")
    if len(containers) != 1:
        message = (
            f"Expected one Interviewer Guideline for {language}, "
            f"found {len(containers)}"
        )
        raise ValueError(message)
    container = containers[0]
    for link in container.select(selector="a.headerlink"):
        link.decompose()
    output = fragment_path(
        output_dir=Path(), docname=docname, language=language
    )
    for link in container.select(selector="a[href]"):
        url = urlsplit(url=str(object=link["href"]))
        if (
            not bool(url.scheme)
            and not bool(url.netloc)
            and url.path.endswith(".html")
        ):
            target = posixpath.normpath(
                path=posixpath.join(posixpath.dirname(docname), url.path)
            )
            if source_url is None:
                destination = posixpath.relpath(
                    path=target, start=output.parent.as_posix()
                )
            else:
                destination = urljoin(
                    base=source_url.rstrip("/") + "/",
                    url=target.removesuffix(".html") + source_suffix,
                )
            if source_anchors and bool(url.fragment):
                destination += "#" + url.fragment
            link["href"] = destination
    for line_number in container.select(selector=".linenos"):
        line_number.decompose()
    for pre in container.find_all(name="pre"):
        code = soup.new_tag(name="code")
        code.string = pre.get_text()
        pre.clear()
        _ = pre.append(tag=code)
    fragment = (
        str(object=container)
        .encode(encoding="ascii", errors="xmlcharrefreplace")
        .decode(encoding="ascii")
    )
    style = (
        files(anchor="sphinx_hackerrank")
        .joinpath("static/interviewer_guideline.css")
        .read_text(encoding="utf-8")
    )
    script = (
        files(anchor="sphinx_hackerrank")
        .joinpath("static/interviewer_guideline.js")
        .read_text(encoding="utf-8")
    )
    return (
        f'<style type="text/css">{style}</style>\n{fragment}\n'
        f'<script data-hr-copy-code="">{script}</script>\n'
    )
