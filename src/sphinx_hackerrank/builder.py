"""Build HackerRank fragments using Sphinx's standard HTML renderer."""

from collections.abc import Iterator
from html import escape
from pathlib import Path
from typing import Any, override

from sphinx.builders.html import StandaloneHTMLBuilder

from sphinx_hackerrank.html import fragment_path, render_fragment
from sphinx_hackerrank.targets import Target, load_targets


class HackerRankBuilder(StandaloneHTMLBuilder):
    """Add standalone language fragments to the normal HTML output."""

    # Sphinx calls init() from its builder constructor.
    interviewer_guideline_targets: dict[str, list[Target]]  # pyrefly: ignore[uninitialized-instance-variable]

    name = "hackerrank"
    format = "html"

    @override
    def init(self) -> None:
        """Validate all question mappings before writing any output."""
        super().init()
        self.interviewer_guideline_targets = load_targets(
            source_dir=Path(self.srcdir),
            pattern=self.config.hackerrank_manifest_pattern,
        )

    @override
    def get_outdated_docs(self) -> Iterator[str]:
        """Rebuild missing fragments and changed mappings or
        presentation.
        """
        self.interviewer_guideline_targets = load_targets(
            source_dir=Path(self.srcdir),
            pattern=self.config.hackerrank_manifest_pattern,
        )
        outdated = set(super().get_outdated_docs())
        if not (
            Path(self.outdir) / "interviewer-guidelines" / "index.html"
        ).is_file():
            outdated.update(self.interviewer_guideline_targets)
        for docname, targets in self.interviewer_guideline_targets.items():
            newest_dependency = max(
                path.stat().st_mtime_ns
                for path in (
                    targets[0].metadata_path,
                    Path(__file__),
                    Path(__file__).with_name(name="html.py"),
                    Path(__file__).parent
                    / "static"
                    / "interviewer_guideline.css",
                    Path(__file__).parent
                    / "static"
                    / "interviewer_guideline.js",
                )
            )
            outputs = (
                fragment_path(
                    output_dir=Path(self.outdir),
                    docname=docname,
                    language=target.language,
                )
                for target in targets
            )
            if any(
                not output.is_file()
                or output.stat().st_mtime_ns < newest_dependency
                for output in outputs
            ):
                outdated.add(docname)
        return iter(sorted(outdated))

    @override
    def handle_page(
        self,
        pagename: str,
        # Sphinx supplies an open-ended template context.
        addctx: dict[str, Any],  # pyrefly: ignore[explicit-any]
        templatename: str = "page.html",
        *,
        outfilename: Path | None = None,
        event_arg: object = None,
    ) -> None:
        """Export the rendered body before the HTML theme adds chrome."""
        for target in self.interviewer_guideline_targets.get(pagename, []):
            output_path = fragment_path(
                output_dir=Path(self.outdir),
                docname=pagename,
                language=target.language,
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            _ = output_path.write_text(
                data=render_fragment(
                    html=addctx["body"],
                    language=target.language,
                    docname=pagename,
                    source_url=self.config.hackerrank_source_url,
                    source_suffix=self.config.hackerrank_source_suffix,
                    source_anchors=self.config.hackerrank_source_anchors,
                ),
                encoding="utf-8",
            )
        super().handle_page(
            pagename=pagename,
            addctx=addctx,
            templatename=templatename,
            outfilename=outfilename,
            event_arg=event_arg,
        )

    @override
    def finish(self) -> None:
        """Add a local preview index linking to each Interviewer Guideline."""
        super().finish()
        preview_dir = Path(self.outdir) / "interviewer-guidelines"
        preview_dir.mkdir(parents=True, exist_ok=True)
        suffix = "-interviewer-guideline"
        links = "\n".join(
            f'<li><a href="{escape(s=docname.removesuffix(suffix))}/'
            f'{target.language}.html">'
            f"{escape(s=target.name)}</a></li>"
            for docname, targets in self.interviewer_guideline_targets.items()
            for target in targets
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
                "<p>Choose a question and language to preview"
                " its Interviewer Guideline.</p>"
                "<p>These previews use the same HTML published as "
                "HackerRank Interviewer Guidelines.</p>"
                f"<ul>{links}</ul></main></body></html>\n"
            ),
            encoding="utf-8",
        )
