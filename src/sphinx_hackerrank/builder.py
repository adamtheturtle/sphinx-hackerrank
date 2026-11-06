"""Build HackerRank fragments using Sphinx's standard HTML renderer."""

import posixpath
from collections.abc import Iterator
from collections.abc import Set as AbstractSet
from hashlib import sha256
from html import escape
from pathlib import Path
from typing import ClassVar, override
from urllib.parse import quote

from docutils import nodes
from docutils.frontend import get_default_settings
from sphinx.builders import Builder
from sphinx.highlighting import PygmentsBridge
from sphinx.util.inspect import object_description
from sphinx.util.osutil import relative_uri
from sphinx.writers.html import HTMLWriter
from sphinx.writers.html5 import HTML5Translator

from sphinx_hackerrank.exports import (
    Export,
    GuidelineExportNode,
    export_inventory,
)
from sphinx_hackerrank.html import render_fragment
from sphinx_hackerrank.writer import render_export


def _preview_link(*, export: Export) -> str:
    """Link to a caller-chosen output from the preview directory."""
    href = escape(
        s=posixpath.relpath(
            path=export.output_path,
            start="interviewer-guidelines",
        )
    )
    return f'<li><a href="{href}">{escape(s=export.name)}</a></li>'


class HackerRankBuilder(Builder):
    """Render explicit document nodes without building a website."""

    name = "hackerrank"
    format = "html"

    default_translator_class: ClassVar[type[nodes.NodeVisitor]] = (
        HTML5Translator
    )
    allow_parallel = True
    supported_image_types: ClassVar[list[str]] = [
        "image/svg+xml",
        "image/png",
        "image/gif",
        "image/jpeg",
    ]
    supported_remote_images = True
    supported_data_uri_images = True
    download_support = True
    add_permalinks = True

    # Initialized by Sphinx's init() and writing hooks.
    current_docname: str = ""
    dlpath: str = ""
    imgpath: str = ""
    secnumbers: dict[str, tuple[int, ...]]  # pyrefly: ignore[uninitialized-instance-variable]
    fignumbers: dict[str, dict[str, tuple[int, ...]]]  # pyrefly: ignore[uninitialized-instance-variable]
    highlighter: PygmentsBridge  # pyrefly: ignore[uninitialized-instance-variable]

    @override
    def init(self) -> None:
        """Initialize only the context required by the HTML translator."""
        self.imagedir = "_images"
        self.current_docname = ""
        self.dlpath = ""
        self.secnumbers: dict[str, tuple[int, ...]] = {}
        self.fignumbers: dict[str, dict[str, tuple[int, ...]]] = {}
        self.highlighter = PygmentsBridge(
            dest="html", stylename=self.config.pygments_style or "sphinx"
        )

    @property
    def math_renderer_name(self) -> str | None:
        """Use Sphinx's configured or unambiguous HTML math renderer."""
        configured = self.config.html_math_renderer
        if isinstance(configured, str):
            return configured
        registered = list(self._registry.html_inline_math_renderers)
        candidates = [name for name in registered if name != "mathjax"]
        if not bool(candidates):
            candidates = registered
        return candidates[0] if len(candidates) == 1 else None

    def _render_signature(self) -> str:
        """Fingerprint rendering options without loading an HTML theme."""
        settings = {
            value.name: value.value
            for value in self.config.filter(rebuild={"env", "html"})
        }
        description = object_description(obj=(settings, sorted(self.tags)))
        digest = sha256()
        digest.update(description.encode(encoding="utf-8"))
        return digest.hexdigest()

    @override
    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        """Resolve document links independently of fragment
        destinations.
        """
        return quote(string=docname) + ".html"

    @override
    def get_outdated_docs(self) -> Iterator[str]:
        """Refresh changed sources, rendering options, and missing exports."""
        exports = export_inventory(env=self.env)
        try:
            previous = (
                Path(self.doctreedir) / "hackerrank-rendering.sha256"
            ).read_text(encoding="utf-8")
        except OSError:
            previous = None
        rebuild = previous is None or previous != self._render_signature()
        index_missing = not (
            Path(self.outdir) / "interviewer-guidelines" / "index.html"
        ).is_file()
        for docname, targets in sorted(exports.items()):
            if not bool(targets):
                continue
            dependencies = [
                Path(__file__),
                Path(__file__).with_name(name="html.py"),
                Path(__file__).with_name(name="exports.py"),
                Path(__file__).with_name(name="writer.py"),
                Path(__file__).parent / "static" / "interviewer_guideline.css",
                Path(self.env.doc2path(docname=docname)),
                *(
                    Path(self.srcdir) / path
                    for path in self.env.dependencies[docname]
                ),
            ]
            newest_dependency = max(
                path.stat().st_mtime_ns
                for path in dependencies
                if path.is_file()
            )
            outputs = [
                Path(self.outdir) / target.output_path for target in targets
            ]
            if (
                rebuild
                or index_missing
                or any(
                    not output.is_file()
                    or output.stat().st_mtime_ns < newest_dependency
                    for output in outputs
                )
            ):
                yield docname

    @override
    def write_documents(self, docnames: AbstractSet[str]) -> None:
        """Resolve and write only documents with explicit export nodes."""
        exports = export_inventory(env=self.env)
        selected = {
            docname for docname in docnames if bool(exports.get(docname))
        }
        if bool(selected):
            super().write_documents(docnames=selected)

    @override
    def write_doc_serialized(
        self, docname: str, doctree: nodes.document
    ) -> None:
        """Select image candidates only from exported content."""
        for node in doctree.findall(condition=GuidelineExportNode):
            self.post_process_images(doctree=node)

    @override
    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        """Render each resolved export boundary using Sphinx's
        translator.
        """
        settings = get_default_settings(HTMLWriter)
        settings.__dict__.update(self.env.settings)
        settings.compact_lists = bool(self.config.html_compact_lists)
        doctree.settings = settings
        self.current_docname = docname
        self.secnumbers = self.env.toc_secnumbers.get(docname, {})
        self.fignumbers = self.env.toc_fignumbers.get(docname, {})
        self.imgpath = relative_uri(
            base=self.get_target_uri(docname=docname), to=self.imagedir
        )
        self.dlpath = relative_uri(
            base=self.get_target_uri(docname=docname), to="_downloads"
        )
        for node in doctree.findall(condition=GuidelineExportNode):
            self.write_fragment(
                export=node.export,
                html=render_export(builder=self, document=doctree, node=node),
            )

    def write_fragment(self, *, export: Export, html: str) -> None:
        """Write a node captured by Sphinx's native HTML translator."""
        output_path = Path(self.outdir) / export.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _ = output_path.write_text(
            data=render_fragment(
                html=html,
                output_path=export.output_path,
                docname=self.current_docname,
                source_url=self.config.hackerrank_source_url,
                source_suffix=self.config.hackerrank_source_suffix,
                source_anchors=self.config.hackerrank_source_anchors,
                image_paths={
                    posixpath.join(self.imgpath, quote(string=filename)): Path(
                        self.srcdir
                    )
                    / source
                    for source, filename in self.images.items()
                },
            ),
            encoding="utf-8",
        )

    @override
    def finish(self) -> None:
        """Add a local preview index linking to each Interviewer Guideline."""
        _ = (Path(self.doctreedir) / "hackerrank-rendering.sha256").write_text(
            data=self._render_signature(), encoding="utf-8"
        )
        preview_dir = Path(self.outdir) / "interviewer-guidelines"
        preview_dir.mkdir(parents=True, exist_ok=True)
        exports = export_inventory(env=self.env)
        links = "\n".join(
            _preview_link(export=target)
            for docname in sorted(exports)
            for target in exports[docname]
        )
        _ = (preview_dir / "index.html").write_text(
            data=(
                '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
                '<meta name="viewport" '
                'content="width=device-width, initial-scale=1">'
                "<title>HackerRank Interviewer Guidelines</title>"
                "<style>body{font:16px/1.5 Arial,sans-serif;"
                "margin:2rem;max-width:60rem}"
                "li{margin:.5rem 0}</style></head><body><main>"
                "<h1>HackerRank Interviewer Guidelines</h1>"
                "<p>Choose a guide to preview"
                " its Interviewer Guideline.</p>"
                "<p>These previews use the same HTML published as "
                "HackerRank Interviewer Guidelines.</p>"
                f"<ul>{links}</ul></main></body></html>\n"
            ),
            encoding="utf-8",
        )
