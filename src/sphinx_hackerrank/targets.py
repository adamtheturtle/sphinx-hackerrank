"""Read rendering metadata without depending on an API client."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard

import yaml


@dataclass(frozen=True)
class Target:
    """One language and its interviewer-facing title."""

    language: str
    name: str
    metadata_path: Path


def _is_mapping(value: object, /) -> TypeGuard[dict[object, object]]:
    """Narrow an arbitrary YAML value to an object-valued mapping."""
    return isinstance(value, dict)


def _is_list(value: object, /) -> TypeGuard[list[object]]:
    """Narrow an arbitrary YAML value to an object-valued list."""
    return isinstance(value, list)


def load_targets(*, source_dir: Path, pattern: str) -> dict[str, list[Target]]:
    """Read adjacent mapping files; publishing metadata stays with the
    consumer.
    """
    targets: dict[str, list[Target]] = {}
    for path in sorted(source_dir.glob(pattern=pattern)):
        source = path.with_suffix(suffix=".rst")
        if not source.is_file():
            message = f"Missing RST source beside {path}"
            raise ValueError(message)
        metadata: object = yaml.safe_load(
            stream=path.read_text(encoding="utf-8")
        )
        if not _is_mapping(metadata) or metadata.get("version") != 1:
            message = f"Expected version: 1 in {path}"
            raise ValueError(message)
        questions = metadata.get("questions")
        if not _is_list(questions) or not bool(questions):
            message = f"Expected nonempty questions list in {path}"
            raise ValueError(message)
        document: list[Target] = []
        seen: set[str] = set()
        for question in questions:
            if not _is_mapping(question):
                message = f"Expected a question mapping in {path}"
                raise ValueError(message)
            language, name = question.get("language"), question.get("name")
            if (
                not isinstance(language, str)
                or re.fullmatch(pattern=r"[a-z][a-z0-9]*", string=language)
                is None
            ):
                message = f"Invalid language in {path}: {language!r}"
                raise ValueError(message)
            if not isinstance(name, str) or not bool(name.strip()):
                message = f"Expected a question name in {path}"
                raise ValueError(message)
            if language in seen:
                message = f"Duplicate language {language!r} in {path}"
                raise ValueError(message)
            seen.add(language)
            document.append(
                Target(language=language, name=name, metadata_path=path)
            )
        targets[
            source.relative_to(source_dir).with_suffix(suffix="").as_posix()
        ] = document
    return targets
