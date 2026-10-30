"""Mapping errors are rejected before a builder can write any
fragments.
"""

from pathlib import Path

import pytest

from sphinx_hackerrank.targets import load_targets


@pytest.mark.parametrize(
    argnames=("body", "message"),
    argvalues=[
        ("[]", "Expected version"),
        ("version: 2", "Expected version"),
        ("version: 1\nquestions: []", "nonempty questions"),
        ("version: 1\nquestions: [null]", "question mapping"),
        (
            "version: 1\nquestions: [{language: ../unsafe, name: Widget}]",
            "Invalid language",
        ),
        ("version: 1\nquestions: [{language: python}]", "question name"),
        (
            (
                "version: 1\n"
                "questions: [{language: python, name: A}, "
                "{language: python, name: B}]"
            ),
            "Duplicate language",
        ),
    ],
)
def test_invalid_targets(*, tmp_path: Path, body: str, message: str) -> None:
    """Reject invalid or unsafe question mappings."""
    _ = (tmp_path / "example.rst").write_text(
        data="Example\n=======\n", encoding="utf-8"
    )
    _ = (tmp_path / "example.yaml").write_text(data=body, encoding="utf-8")
    with pytest.raises(expected_exception=ValueError, match=message):
        _ = load_targets(source_dir=tmp_path, pattern="*.yaml")


def test_missing_source(*, tmp_path: Path) -> None:
    """Reject mappings without an adjacent RST source."""
    _ = (tmp_path / "missing.yml").write_text(
        data="version: 1", encoding="utf-8"
    )
    with pytest.raises(
        expected_exception=ValueError, match="Missing RST source"
    ):
        _ = load_targets(source_dir=tmp_path, pattern="*.yml")


def test_nested_sources_and_publishing_metadata(*, tmp_path: Path) -> None:
    """Read nested mappings while allowing publishing metadata."""
    nested = tmp_path / "nested"
    nested.mkdir()
    _ = (nested / "example.rst").write_text(
        data="Example\n=======\n", encoding="utf-8"
    )
    metadata = nested / "example.yaml"
    _ = metadata.write_text(
        data="version: 1\n"
        "questions: [{language: python, name: Widget, "
        "question_id: '123'}]",
        encoding="utf-8",
    )
    (target,) = load_targets(source_dir=tmp_path, pattern="**/*.yaml")[
        "nested/example"
    ]
    assert target.language == "python"
    assert target.name == "Widget"
    assert target.metadata_path == metadata
