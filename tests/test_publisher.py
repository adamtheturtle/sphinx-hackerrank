"""Verify explicit API publishing and credential-free ordinary builds."""

import json as jsonlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, override

import pytest
from hackerrank.api import api_operations
from hackerrank.transports import Transport, TransportResponse
from hackerrank.types import JSONValue
from sphinx.errors import SphinxError
from sphinx.testing.util import SphinxTestApp

from sphinx_hackerrank.publisher import publish_operations
from tests.builds import write_sources


@dataclass
class PublishingTransport(Transport):
    """Capture actual SDK writes without a live account."""

    status: int
    requests: list[
        tuple[str, str, dict[str, str], Mapping[str, JSONValue] | None]
    ]

    @override
    def __call__(
        self,
        *,
        method: str,
        url: str,
        headers: dict[str, str],
        params: dict[str, str | int] | None,
        json: Mapping[str, JSONValue] | None,
        files: Mapping[str, tuple[str, bytes | BinaryIO, str]] | None,
    ) -> TransportResponse:
        """Return a complete synthetic JSON response."""
        assert files is None
        assert params is not None
        self.requests.append((method, url, headers, json))
        return TransportResponse(
            status_code=self.status,
            headers={},
            content=b'{"message":"synthetic-secret"}',
        )


def test_every_operation_is_publishable(tmp_path: Path) -> None:
    """Every v3, ATS and SCIM operation reaches the documented transport
    route.
    """
    transport = PublishingTransport(status=200, requests=[])
    plans: list[dict[str, JSONValue]] = []
    for operation in api_operations().values():
        path: dict[str, JSONValue] = {
            str(object=item["name"]): "1"
            for item in operation.parameters
            if item["location"] == "path"
        }
        query: dict[str, JSONValue] = {
            str(object=item["name"]): "1"
            for item in operation.parameters
            if item["location"] == "query" and item["required"] is True
        }
        plan: dict[str, JSONValue] = {
            "operation": operation.id,
            "path_parameters": path,
            "query": query,
        }
        if operation.body_required:
            plan["body"] = dict[str, JSONValue]()
        plans.append(plan)
    results = publish_operations(
        operations=plans,
        export_root=tmp_path,
        transport=transport,
        environment={
            "HACKERRANK_API_TOKEN": "v3",
            "HACKERRANK_SCIM_API_TOKEN": "scim",
        },
    )
    assert len(results) == len(api_operations())
    for operation, request in zip(
        api_operations().values(), transport.requests, strict=True
    ):
        assert request[0] == operation.method
        assert request[2]["Authorization"] == (
            "Bearer scim" if operation.scim else "Bearer v3"
        )


def test_exported_guidelines_are_read_exactly_before_writes(
    tmp_path: Path,
) -> None:
    """Publish exported text while preserving its whitespace and other body
    fields.
    """
    content = "<p>Guidelines</p>\n  <pre>code</pre>\n"
    _ = (tmp_path / "guide.html").write_text(data=content, encoding="utf-8")
    transport = PublishingTransport(status=200, requests=[])
    results = publish_operations(
        operations=[
            {
                "operation": "api_update_question",
                "path_parameters": {"question_id": "1"},
                "body": {"name": "Example"},
                "body_files": {"internal_notes": "guide.html"},
            }
        ],
        export_root=tmp_path,
        environment={"HACKERRANK_API_TOKEN": "synthetic"},
        transport=transport,
    )
    assert transport.requests[0][3] == {
        "name": "Example",
        "internal_notes": content,
    }
    assert results[0]["status"] == transport.status


@pytest.mark.parametrize(
    argnames="plan",
    argvalues=[
        {"unknown": True},
        {"operation": 1},
        {"operation": "api_retrieve_user", "path_parameters": {"id": []}},
        {"operation": "api_retrieve_user", "path_parameters": {"id": True}},
        {"operation": "api_retrieve_user"},
        {"operation": "api_list_all_tests", "query": []},
        {"operation": "api_create_user"},
        {"operation": "api_create_user", "body_files": {"name": 1}},
        {
            "operation": "api_create_user",
            "body_files": {"name": "../outside.html"},
        },
    ],
)
def test_invalid_plan_prevents_all_requests(
    plan: dict[str, JSONValue], tmp_path: Path
) -> None:
    """Validate the whole plan before executing even its first valid
    operation.
    """
    transport = PublishingTransport(status=200, requests=[])
    with pytest.raises(expected_exception=(ValueError, TypeError)):
        _ = publish_operations(
            operations=[{"operation": "api_list_all_tests"}, plan],
            export_root=tmp_path,
            environment={"HACKERRANK_API_TOKEN": "synthetic"},
            transport=transport,
        )
    assert len(transport.requests) == 0


@pytest.mark.parametrize(
    argnames="operation",
    argvalues=["api_list_all_tests", "api_scim_list_users"],
)
def test_missing_credentials(operation: str, tmp_path: Path) -> None:
    """Report the required credential kind without making a request."""
    transport = PublishingTransport(status=200, requests=[])
    with pytest.raises(expected_exception=SphinxError, match="TOKEN"):
        _ = publish_operations(
            operations=[{"operation": operation}],
            export_root=tmp_path,
            environment={},
            transport=transport,
        )
    assert len(transport.requests) == 0


def test_scim_only_and_api_failure(tmp_path: Path) -> None:
    """Provisioning works independently and failed responses do not expose
    bodies.
    """
    transport = PublishingTransport(status=200, requests=[])
    _ = publish_operations(
        operations=[{"operation": "api_scim_list_users"}],
        export_root=tmp_path,
        environment={"HACKERRANK_SCIM_API_TOKEN": "scim-only"},
        transport=transport,
    )
    assert transport.requests[0][2]["Authorization"] == "Bearer scim-only"
    failing = PublishingTransport(status=403, requests=[])
    with pytest.raises(expected_exception=SphinxError) as error:
        _ = publish_operations(
            operations=[{"operation": "api_list_all_tests"}],
            export_root=tmp_path,
            environment={"HACKERRANK_API_TOKEN": "synthetic-secret"},
            transport=failing,
        )
    assert "synthetic-secret" not in str(object=error.value)


def test_empty_plan_is_offline(tmp_path: Path) -> None:
    """An explicit publish build with no operations needs no
    credentials.
    """
    result = publish_operations(
        operations=[], export_root=tmp_path, environment={}, transport=None
    )
    assert len(result) == 0


@pytest.mark.parametrize(
    argnames="question_type", argvalues=["code", "whiteboard", "mcq"]
)
@pytest.mark.parametrize(argnames="from_export", argvalues=[False, True])
def test_invalid_question_prompt_prevents_all_publishing(
    *, tmp_path: Path, question_type: str, from_export: bool
) -> None:
    """The SDK validates question capabilities before any plan is sent."""
    transport = PublishingTransport(status=200, requests=[])
    plan: dict[str, JSONValue] = {
        "operation": "api_update_question",
        "path_parameters": {"question_id": "1"},
        "body": {"type": question_type, "custom_system_prompt": "Hints"},
    }
    if from_export:
        _ = (tmp_path / "prompt.md").write_text(data="Hints", encoding="utf-8")
        plan["body"] = {"type": question_type}
        plan["body_files"] = {"custom_system_prompt": "prompt.md"}
    with pytest.raises(expected_exception=ValueError, match="not supported"):
        _ = publish_operations(
            operations=[
                {"operation": "api_list_all_tests"},
                plan,
            ],
            export_root=tmp_path,
            environment={},
            transport=transport,
        )
    assert len(transport.requests) == 0


def test_normal_and_publish_builders(tmp_path: Path) -> None:
    """Ordinary exports ignore API plans; the explicit builder writes
    catalogue/results.
    """
    source = tmp_path / "source"
    write_sources(
        source=source,
        files={
            "index.rst": (
                "Example\n=======\n\n"
                ".. hackerrank-export:: guide.html\n"
                "   :name: Example\n\n   Instructions.\n"
            )
        },
    )
    for builder, plan in [
        ("hackerrank", [{"operation": "not-an-operation"}]),
        ("hackerrank-publish", list[dict[str, JSONValue]]()),
    ]:
        app = SphinxTestApp(
            srcdir=source,
            buildername=builder,
            builddir=tmp_path / builder,
            confoverrides={
                "extensions": ["sphinx_hackerrank"],
                "hackerrank_api_operations": plan,
            },
        )
        try:
            app.build()
            assert app.statuscode == 0
            output = Path(app.outdir)
            assert (output / "guide.html").exists()
            if builder == "hackerrank-publish":
                assert (
                    jsonlib.loads(
                        s=(output / "hackerrank-api-results.json").read_text()
                    )
                    == []
                )
                catalogue = jsonlib.loads(
                    s=(output / "hackerrank-api-catalogue.json").read_text()
                )
                assert len(catalogue["operations"]) == len(api_operations())
        finally:
            app.cleanup()


def test_builder_rejects_non_list_plan(tmp_path: Path) -> None:
    """Reject malformed configuration instead of interpreting object keys
    as operations.
    """
    source = tmp_path / "source"
    write_sources(source=source, files={"index.rst": "Example\n=======\n"})
    app = SphinxTestApp(
        srcdir=source,
        buildername="hackerrank-publish",
        confoverrides={"extensions": ["sphinx_hackerrank"]},
    )
    try:
        app.config.hackerrank_api_operations = {}
        with pytest.raises(
            expected_exception=SphinxError, match="must be a list"
        ):
            app.build()
    finally:
        app.cleanup()
