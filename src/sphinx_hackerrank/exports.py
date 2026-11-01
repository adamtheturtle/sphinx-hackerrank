"""Explicit output requests supplied by the consuming project."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True, kw_only=True)
class GuidelineExport:
    """Export one selected guide to a caller-chosen HTML destination."""

    docname: str
    selector: str
    output_path: str
    name: str

    def __post_init__(self) -> None:
        """Reject incomplete requests and paths outside the build
        directory.
        """
        for value in (
            self.docname,
            self.selector,
            self.output_path,
            self.name,
        ):
            if not bool(value.strip()):
                message = "Export fields must not be empty"
                raise ValueError(message)
        for value in (self.docname, self.output_path):
            path = PurePosixPath(value)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in value
                or ":" in value
            ):
                message = "Export paths must stay inside the build directory"
                raise ValueError(message)
        if PurePosixPath(self.output_path).suffix != ".html":
            message = "Export destination must be an HTML file"
            raise ValueError(message)
        if PurePosixPath(self.output_path).as_posix() in {
            self.docname + ".html",
            "interviewer-guidelines/index.html",
        }:
            message = "Export destination overlaps a generated page"
            raise ValueError(message)


def group_exports(
    *,
    source_dir: Path,
    exports: list[GuidelineExport],
) -> dict[str, list[GuidelineExport]]:
    """Validate explicit source documents and unique destinations."""
    grouped: dict[str, list[GuidelineExport]] = {}
    paths: set[str] = set()
    for export in exports:
        if not (source_dir / (export.docname + ".rst")).is_file():
            message = f"Missing RST source for {export.docname!r}"
            raise ValueError(message)
        destination = PurePosixPath(export.output_path).as_posix()
        if destination in paths:
            message = f"Duplicate export destination: {destination!r}"
            raise ValueError(message)
        paths.add(destination)
        grouped.setdefault(export.docname, []).append(export)
    return grouped
