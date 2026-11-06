"""Structured export boundaries and their persistent Sphinx inventory."""

from collections.abc import Callable
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, ClassVar, override

from docutils import nodes
from sphinx.addnodes import pending_xref
from sphinx.builders import Builder
from sphinx.domains import Domain
from sphinx.environment import BuildEnvironment
from sphinx.util.docutils import SphinxDirective


@dataclass(frozen=True, kw_only=True)
class Export:
    """The destination and preview label for one content boundary."""

    output_path: str
    name: str

    def __post_init__(self) -> None:
        """Reject incomplete requests and unsafe output destinations."""
        if not bool(self.name.strip()) or not bool(self.output_path.strip()):
            message = "Export fields must not be empty"
            raise ValueError(message)
        path = PurePosixPath(self.output_path)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in self.output_path
            or ":" in self.output_path
        ):
            message = "Export paths must stay inside the build directory"
            raise ValueError(message)
        if path.suffix != ".html":
            message = "Export destination must be an HTML file"
            raise ValueError(message)


class GuidelineExportNode(nodes.container):
    """Content rendered both in its documentation page and as an
    export.
    """

    def __init__(
        self,
        *children: nodes.Node,
        output_path: str,
        name: str,
        rawsource: str = "",
        # Docutils copies nodes with their open-ended attributes.
        **attributes: object,
    ) -> None:
        """Associate ordinary document content with its export
        metadata.
        """
        export = Export(output_path=output_path, name=name)
        super().__init__(
            rawsource,
            *children,
            output_path=PurePosixPath(export.output_path).as_posix(),
            name=export.name,
            **attributes,
        )
        self["classes"] = list(
            dict.fromkeys(["hr-interviewer-guideline", *self["classes"]])
        )

    @property
    def export(self) -> Export:
        """Read the metadata retained by Docutils copies and pickles."""
        return Export(output_path=self["output_path"], name=self["name"])


class GuidelineExportDirective(SphinxDirective):
    """Declare an export boundary directly in ordinary RST."""

    required_arguments = 1
    has_content = True
    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {  # pyrefly: ignore[explicit-any]
        "name": str
    }

    @override
    def run(self) -> list[nodes.Node]:
        """Parse the content once for page rendering and portable
        export.
        """
        self.assert_has_content()
        try:
            node = GuidelineExportNode(
                output_path=self.arguments[0],
                name=self.options.get("name", ""),
            )
        except ValueError as error:
            raise self.error(message=str(object=error)) from error
        self.set_source_info(node=node)
        _ = self.state.nested_parse(
            block=self.content, input_offset=self.content_offset, node=node
        )
        return [node]


class ExportInventory(dict[str, list[Export]]):
    """Identify the typed metadata stored in Sphinx domain data."""


class HackerRankDomain(Domain):
    """Track export metadata across parallel and incremental builds."""

    name = "hackerrank"
    label = "HackerRank"
    initial_data: ClassVar[dict[str, object]] = {"exports": ExportInventory()}

    @property
    def exports(self) -> dict[str, list[Export]]:
        """Return the inventory stored in Sphinx's environment."""
        exports = self.data["exports"]
        assert isinstance(exports, ExportInventory)
        return exports

    @override
    def clear_doc(self, docname: str) -> None:
        """Discard a removed or changed document's previous exports."""
        _ = self.exports.pop(docname, None)

    @override
    def process_doc(
        self, env: BuildEnvironment, docname: str, document: nodes.document
    ) -> None:
        """Collect explicit nodes after all source directives have run."""
        self.exports[docname] = [
            node.export
            for node in document.findall(condition=GuidelineExportNode)
        ]

    @override
    def merge_domaindata(
        self,
        docnames: AbstractSet[str],
        # Sphinx supplies each domain's open-ended serialized state.
        otherdata: dict[str, Any],  # pyrefly: ignore[explicit-any]
    ) -> None:
        """Merge inventory entries owned by parallel Sphinx readers."""
        other = otherdata["exports"]
        assert isinstance(other, ExportInventory)
        self.exports.update(
            (docname, other[docname])
            for docname in docnames
            if docname in other
        )

    @override
    def resolve_any_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder: Builder,
        target: str,
        node: pending_xref,
        contnode: nodes.Element,
    ) -> list[tuple[str, nodes.reference]]:
        """Leave cross-reference resolution to content-bearing domains."""
        return []

    @override
    def check_consistency(self) -> None:
        """Reject duplicate exports and collisions with generated
        pages.
        """
        pages = {
            *(docname + ".html" for docname in self.env.found_docs),
            "interviewer-guidelines/index.html",
            "genindex.html",
            "search.html",
        }
        destinations: set[str] = set()
        for exports in self.exports.values():
            for export in exports:
                if export.output_path in pages:
                    message = "Export destination overlaps a generated page"
                    raise ValueError(message)
                if export.output_path in destinations:
                    message = (
                        f"Duplicate export destination: {export.output_path!r}"
                    )
                    raise ValueError(message)
                destinations.add(export.output_path)


def export_inventory(env: BuildEnvironment) -> dict[str, list[Export]]:
    """Read the extension's registered Sphinx domain."""
    domain = env.get_domain(domainname="hackerrank")
    assert isinstance(domain, HackerRankDomain)
    return domain.exports
