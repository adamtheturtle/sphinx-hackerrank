"""Render standalone HTML without a theme or external assets."""

import posixpath
from base64 import b64encode
from collections.abc import Mapping
from importlib.resources import files
from mimetypes import guess_type
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup, Tag


def render_fragment(
    *,
    html: str,
    output_path: str,
    docname: str = "interviewer-guideline",
    source_url: str | None = None,
    source_suffix: str = ".html",
    source_anchors: bool = True,
    image_paths: Mapping[str, Path] | None = None,
) -> str:
    """Make an already-rendered export portable, retaining exact code."""
    soup = BeautifulSoup(markup=html, features="html.parser")
    container = soup
    _embed_images(
        container=container,
        image_paths={} if image_paths is None else image_paths,
    )
    for link in container.select(selector="a.headerlink"):
        link.decompose()
    output = Path(output_path)
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
        .strip()
        .encode(encoding="ascii", errors="xmlcharrefreplace")
        .decode(encoding="ascii")
    )
    style = (
        files(anchor="sphinx_hackerrank")
        .joinpath("static/interviewer_guideline.css")
        .read_text(encoding="utf-8")
    )
    return f'<style type="text/css">{style}</style>\n{fragment}\n'


def _embed_images(*, container: Tag, image_paths: Mapping[str, Path]) -> None:
    """Bundle local images without fetching externally hosted media."""
    encoded: dict[Path, str] = {}

    def image_url(*, uri: str) -> str:
        """Keep URL fragments while reusing each file's encoded bytes."""
        url = urlsplit(url=uri)
        if bool(url.scheme) or bool(url.netloc):
            return uri
        path = image_paths.get(url.path)
        if path is None:
            message = f"No local image asset supplied for {uri!r}"
            raise ValueError(message)
        if path not in encoded:
            mime, _encoding = guess_type(url=str(object=path))
            if mime is None or not mime.startswith("image/"):
                message = f"Unsupported image format: {path}"
                raise ValueError(message)
            encoded[path] = (
                "data:"
                + mime
                + ";base64,"
                + b64encode(s=path.read_bytes()).decode(encoding="ascii")
            )
        return encoded[path] + (
            "#" + url.fragment if bool(url.fragment) else ""
        )

    for image in container.select(selector="img[src]"):
        image["src"] = image_url(uri=str(object=image["src"]))
    for link in container.select(selector="a[href]"):
        url = urlsplit(url=str(object=link["href"]))
        if (
            not bool(url.scheme)
            and not bool(url.netloc)
            and url.path in image_paths
        ):
            link["href"] = image_url(uri=str(object=link["href"]))
