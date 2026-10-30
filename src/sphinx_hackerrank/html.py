"""Render standalone HTML without a theme or external assets."""

from __future__ import annotations

import posixpath
from importlib.resources import files
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


def fragment_path(*, output_dir: Path, docname: str, language: str) -> Path:
    """Locate a language fragment in a builder output directory."""
    return output_dir / "mini-maps" / docname.removesuffix("-mini-map") / f"{language}.html"


def render_fragment(
    *,
    html: str,
    language: str,
    docname: str = "mini-map",
    source_url: str | None = None,
    source_suffix: str = ".html",
    source_anchors: bool = True,
) -> str:
    """Extract a language view, retaining exact code and portable links."""
    soup = BeautifulSoup(html, "html.parser")
    containers = soup.select(f".mini-map-{language}")
    if len(containers) != 1:
        raise ValueError(f"Expected one mini-map for {language}, found {len(containers)}")
    container = containers[0]
    for link in container.select("a.headerlink"):
        link.decompose()
    output = fragment_path(output_dir=Path(), docname=docname, language=language)
    for link in container.select("a[href]"):
        url = urlsplit(str(link["href"]))
        if not url.scheme and not url.netloc and url.path.endswith(".html"):
            target = posixpath.normpath(posixpath.join(posixpath.dirname(docname), url.path))
            if source_url is None:
                destination = posixpath.relpath(target, output.parent.as_posix())
            else:
                destination = urljoin(source_url.rstrip("/") + "/", target.removesuffix(".html") + source_suffix)
            if source_anchors and url.fragment:
                destination += "#" + url.fragment
            link["href"] = destination
    for pre in container.find_all("pre"):
        code = soup.new_tag("code")
        code.string = pre.get_text()
        pre.clear()
        pre.append(code)
    fragment = str(container).encode("ascii", errors="xmlcharrefreplace").decode("ascii")
    style = files("sphinx_hackerrank").joinpath("static/mini_map.css").read_text(encoding="utf-8")
    return f'<style type="text/css">{style}</style>\n{fragment}\n'
