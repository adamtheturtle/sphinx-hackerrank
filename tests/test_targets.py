"""Mapping errors are rejected before a builder can write any fragments."""

import pytest

from sphinx_hackerrank.targets import load_targets


@pytest.mark.parametrize(
    "body,message",
    [
        ("[]", "Expected version"),
        ("version: 2", "Expected version"),
        ("version: 1\nquestions: []", "nonempty questions"),
        ("version: 1\nquestions: [null]", "question mapping"),
        ("version: 1\nquestions: [{language: ../unsafe, name: Widget}]", "Invalid language"),
        ("version: 1\nquestions: [{language: python}]", "question name"),
        ("version: 1\nquestions: [{language: python, name: A}, {language: python, name: B}]", "Duplicate language"),
    ],
)
def test_invalid_targets(tmp_path, body, message):
    (tmp_path / "example.rst").write_text("Example\n=======\n", encoding="utf-8")
    (tmp_path / "example.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_targets(source_dir=tmp_path, pattern="*.yaml")


def test_missing_source(tmp_path):
    (tmp_path / "missing.yml").write_text("version: 1", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing RST source"):
        load_targets(source_dir=tmp_path, pattern="*.yml")


def test_nested_sources_and_publishing_metadata(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "example.rst").write_text("Example\n=======\n", encoding="utf-8")
    metadata = nested / "example.yaml"
    metadata.write_text(
        "version: 1\nquestions: [{language: python, name: Widget, question_id: '123'}]", encoding="utf-8"
    )
    (target,) = load_targets(source_dir=tmp_path, pattern="**/*.yaml")["nested/example"]
    assert target.language == "python"
    assert target.name == "Widget"
    assert target.metadata_path == metadata
