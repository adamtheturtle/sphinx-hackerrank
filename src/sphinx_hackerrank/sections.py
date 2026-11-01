"""Reuse parsed guide sections in language-specific Sphinx Interviewer
Guidelines.
"""

from docutils import nodes
from sphinx_toolbox.collapse import CollapseNode, CollapseSummaryNode


def find_sections(
    *, document: nodes.document | nodes.section, selector: str
) -> list[nodes.section]:
    """Find literal headings, heading paths, or standard RST labels."""
    sections: list[nodes.section] = list(
        document.findall(condition=nodes.section)
    )
    literal = [
        section for section in sections if section[0].astext() == selector
    ]
    if bool(literal):
        return literal
    matches: list[nodes.section]
    if selector.startswith("#"):
        label = nodes.fully_normalize_name(name=selector[1:])
        matches = [
            section
            for section in sections
            if label in section["names"] or label in section["ids"]
        ]
    else:
        parts = [part.strip() for part in selector.split(sep="/")]
        matches = [
            section for section in sections if section[0].astext() == parts[0]
        ]
        for part in parts[1:]:
            matches = [
                child
                for section in matches
                for child in section.children
                if isinstance(child, nodes.section)
                and child[0].astext() == part
            ]
    return matches


def _rubric(title: nodes.Node) -> nodes.rubric:
    """Copy a section heading as an unnumbered rubric."""
    assert isinstance(title, nodes.title)
    rubric = nodes.rubric(rawsource=title.rawsource)
    rubric += title.deepcopy().children
    return rubric


def _copy_without_sections(
    *, section: nodes.section, exclude_sections: tuple[nodes.section, ...]
) -> nodes.section:
    """Copy a section while omitting validated descendant selections."""
    copied = section.deepcopy()
    excluded_ids = {id(target) for target in exclude_sections}
    originals = list(section.findall(condition=nodes.section))
    copies = list(copied.findall(condition=nodes.section))
    for original, target in zip(originals, copies, strict=True):
        if id(original) in excluded_ids:
            assert target.parent is not None
            _ = target.parent.remove(item=target)
    return copied


def section_content(
    *,
    section: nodes.section,
    guide: str,
    language: str,
    include_heading: bool,
    exclude_sections: tuple[nodes.section, ...],
) -> list[nodes.Node]:
    """Copy selected nodes without importing the guide's anchors or
    language selectors.
    """
    copied = _copy_without_sections(
        section=section, exclude_sections=exclude_sections
    )
    container = nodes.container()
    if include_heading:
        container += _rubric(title=copied[0])
    container += copied.children[1:]
    for subsection in list(container.findall(condition=nodes.section)):
        subsection.replace_self(
            new=[_rubric(title=subsection[0]), *subsection.children[1:]]
        )
    for target in list(container.findall(condition=nodes.target)):
        assert target.parent is not None
        _ = target.parent.remove(item=target)
    for element in container.findall(condition=nodes.Element):
        element["ids"] = []
        element["names"] = []
        if isinstance(element, nodes.reference) and "refid" in element:
            element["refuri"] = f"{guide}.html#{element['refid']}"
            del element["refid"]
    for collapse in list(container.findall(condition=CollapseNode)):
        if collapse["label"] == language:
            collapse.replace_self(
                new=[
                    child
                    for child in collapse.children
                    if not isinstance(child, CollapseSummaryNode)
                ]
            )
    return container.children
