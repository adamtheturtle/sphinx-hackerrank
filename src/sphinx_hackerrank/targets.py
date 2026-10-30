"""Read rendering metadata without depending on an API client."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Target:
    """One language and its interviewer-facing title."""

    language: str
    name: str
    metadata_path: Path


def load_targets(*, source_dir: Path, pattern: str) -> dict[str, list[Target]]:
    """Read adjacent mapping files; publishing metadata stays with the consumer."""
    targets: dict[str, list[Target]] = {}
    for path in sorted(source_dir.glob(pattern)):
        source = path.with_suffix(".rst")
        if not source.is_file():
            raise ValueError(f"Missing RST source beside {path}")
        metadata = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict) or metadata.get("version") != 1:
            raise ValueError(f"Expected version: 1 in {path}")
        questions = metadata.get("questions")
        if not isinstance(questions, list) or not questions:
            raise ValueError(f"Expected nonempty questions list in {path}")
        document: list[Target] = []
        seen: set[str] = set()
        for question in questions:
            if not isinstance(question, dict):
                raise ValueError(f"Expected a question mapping in {path}")
            language, name = question.get("language"), question.get("name")
            if not isinstance(language, str) or re.fullmatch(r"[a-z][a-z0-9]*", language) is None:
                raise ValueError(f"Invalid language in {path}: {language!r}")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"Expected a question name in {path}")
            if language in seen:
                raise ValueError(f"Duplicate language {language!r} in {path}")
            seen.add(language)
            document.append(Target(language, name, path))
        targets[source.relative_to(source_dir).with_suffix("").as_posix()] = document
    return targets
