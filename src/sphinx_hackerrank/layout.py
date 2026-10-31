"""Caller-defined selection and presentation for derived guide views."""

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class SectionGroup:
    """Headings to combine under one disclosure, in the caller's order."""

    title: str
    sections: tuple[str, ...]
    include_headings: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class GuidelineLayout:
    """A consumer's rules for recognizing, selecting, and grouping
    sections.
    """

    part_marker: str
    groups: tuple[SectionGroup, ...]
    trailing_sections: tuple[str, ...] = ()
    introduction: str = ""
