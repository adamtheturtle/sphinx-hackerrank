"""Execute explicitly configured API operations after exporting guidelines."""

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import override

from hackerrank.api import api_catalogue, parse_api_object, prepare_operation
from hackerrank.client import HackerRank
from hackerrank.exceptions import HackerRankError
from hackerrank.transports import Transport
from hackerrank.types import JSONValue
from sphinx.errors import SphinxError

from sphinx_hackerrank.builder import HackerRankBuilder


@dataclass(frozen=True, kw_only=True)
class PublishOperation:
    """A validated operation, prepared before credentials or network
    access.
    """

    operation: str
    path_parameters: dict[str, str | int]
    query: dict[str, JSONValue]
    body: dict[str, JSONValue] | None
    scim: bool


def _object(*, value: JSONValue) -> dict[str, JSONValue]:
    """Validate a configuration object through the SDK's JSON boundary."""
    return parse_api_object(text=json.dumps(obj=value))


def _prepare(
    *, value: Mapping[str, JSONValue], export_root: Path
) -> PublishOperation:
    """Resolve exported text files and validate every request before
    publishing.
    """
    allowed = {"operation", "path_parameters", "query", "body", "body_files"}
    if bool(set(value).difference(allowed)):
        message = "Unknown key in hackerrank_api_operations."
        raise ValueError(message)
    operation = value.get("operation")
    if not isinstance(operation, str):
        message = "Each API operation needs an operation name."
        raise TypeError(message)
    path_values = _object(value=value.get("path_parameters", {}))
    path_parameters: dict[str, str | int] = {}
    for key, item in path_values.items():
        if isinstance(item, bool) or not isinstance(item, str | int):
            message = "Path parameters must be strings or integers."
            raise TypeError(message)
        path_parameters[key] = item
    query = _object(value=value.get("query", {}))
    raw_body = value.get("body")
    body = None if raw_body is None else _object(value=raw_body)
    body_files = _object(value=value.get("body_files", {}))
    if bool(body_files):
        body = dict[str, JSONValue]() if body is None else body
        root = export_root.resolve()
        for field, relative in body_files.items():
            if not isinstance(relative, str):
                message = "body_files values must be export paths."
                raise TypeError(message)
            source = (root / relative).resolve()
            if not source.is_relative_to(root):
                message = (
                    "body_files paths must stay inside the export directory."
                )
                raise ValueError(message)
            body[field] = source.read_text(encoding="utf-8")
    selected, _, _ = prepare_operation(
        operation=operation,
        path_parameters=path_parameters,
        query=query,
        body=body,
    )
    return PublishOperation(
        operation=operation,
        path_parameters=path_parameters,
        query=query,
        body=body,
        scim=selected.scim,
    )


def publish_operations(
    *,
    operations: Sequence[Mapping[str, JSONValue]],
    export_root: Path,
    environment: Mapping[str, str],
    transport: Transport | None = None,
) -> list[dict[str, JSONValue]]:
    """Execute any documented operations, in configuration order, without
    logging credentials.
    """
    plans = [
        _prepare(value=value, export_root=export_root) for value in operations
    ]
    if not bool(plans):
        return []
    api_key = environment.get("HACKERRANK_API_TOKEN", "")
    scim_key = environment.get("HACKERRANK_SCIM_API_TOKEN", "")
    if any(not item.scim for item in plans) and not bool(api_key.strip()):
        message = "Set HACKERRANK_API_TOKEN before publishing v3 operations."
        raise SphinxError(message)
    if any(item.scim for item in plans) and not bool(scim_key.strip()):
        message = (
            "Set HACKERRANK_SCIM_API_TOKEN before publishing SCIM operations."
        )
        raise SphinxError(message)
    results: list[dict[str, JSONValue]] = []
    with HackerRank(
        api_key=api_key if bool(api_key) else "scim-only", transport=transport
    ) as client:
        for item in plans:
            try:
                response = client.api.call(
                    operation=item.operation,
                    path_parameters=item.path_parameters,
                    query=item.query,
                    body=item.body,
                    scim_api_key=scim_key if bool(scim_key) else None,
                )
            except HackerRankError as error:
                message = (
                    f"HackerRank operation {item.operation} failed "
                    f"(HTTP {error.status_code})."
                )
                raise SphinxError(message) from None
            results.append(
                parse_api_object(text=json.dumps(obj=asdict(obj=response)))
            )
    return results


class HackerRankPublishBuilder(HackerRankBuilder):
    """Export guidelines, then execute the explicitly configured API plan
    once.
    """

    name = "hackerrank-publish"
    allow_parallel = False

    @override
    def finish(self) -> None:
        """Publish only for this explicitly selected builder, retaining
        complete results.
        """
        super().finish()
        configured = parse_api_object(
            text=json.dumps(
                obj={"operations": self.config.hackerrank_api_operations}
            )
        )
        raw = configured["operations"]
        if not isinstance(raw, list):
            message = "hackerrank_api_operations must be a list."
            raise SphinxError(message)
        operations = [_object(value=value) for value in raw]
        root = Path(self.outdir)
        results = publish_operations(
            operations=operations, export_root=root, environment=os.environ
        )
        _ = (root / "hackerrank-api-results.json").write_text(
            data=json.dumps(obj=results, indent=2), encoding="utf-8"
        )
        _ = (root / "hackerrank-api-catalogue.json").write_text(
            data=json.dumps(obj=api_catalogue(), indent=2), encoding="utf-8"
        )
