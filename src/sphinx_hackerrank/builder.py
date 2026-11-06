"""Build HackerRank fragments using Sphinx's standard HTML renderer."""

import posixpath
from collections.abc import Iterator
from html import escape
from pathlib import Path
from typing import override
from urllib.parse import quote

from sphinx.builders.html import StandaloneHTMLBuilder

from sphinx_hackerrank.exports import Export, export_inventory
from sphinx_hackerrank.html import render_fragment


def _preview_link(*, export: Export) -> str:
    """Link to a caller-chosen output from the preview directory."""
    href = escape(
        s=posixpath.relpath(
            path=export.output_path,
            start="interviewer-guidelines",
        )
    )
    return f'<li><a href="{href}">{escape(s=export.name)}</a></li>'


class HackerRankBuilder(StandaloneHTMLBuilder):
    """Add standalone guideline fragments to the normal HTML output."""

    name = "hackerrank"
    format = "html"

    @override
    def get_outdated_docs(self) -> Iterator[str]:
        """Rebuild missing fragments and changed export requests or
        presentation.
        """
        exports = export_inventory(env=self.env)
        outdated = set(super().get_outdated_docs())
        if not (
            Path(self.outdir) / "interviewer-guidelines" / "index.html"
        ).is_file():
            outdated.update(exports)
        for docname, targets in exports.items():
            newest_dependency = max(
                path.stat().st_mtime_ns
                for path in (
                    Path(__file__),
                    Path(__file__).with_name(name="html.py"),
                    Path(__file__).with_name(name="exports.py"),
                    Path(__file__).with_name(name="writer.py"),
                    Path(__file__).parent
                    / "static"
                    / "interviewer_guideline.css",
                )
            )
            outputs = (
                Path(self.outdir) / target.output_path for target in targets
            )
            if any(
                not output.is_file()
                or output.stat().st_mtime_ns < newest_dependency
                for output in outputs
            ):
                outdated.add(docname)
        return iter(sorted(outdated))

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
        super().finish()
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
