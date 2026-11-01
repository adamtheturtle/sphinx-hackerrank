"""Reuse parsed guide sections in language-specific Sphinx Interviewer
Guidelines.
"""

from docutils import nodes
from sphinx_section_include import copy_section
from sphinx_toolbox.collapse import CollapseNode, CollapseSummaryNode


def _rubric(title: nodes.Node) -> nodes.rubric:
    """Copy a section heading as an unnumbered rubric."""
    assert isinstance(title, nodes.title)
    rubric = nodes.rubric(rawsource=title.rawsource)
    rubric += title.deepcopy().children
    return rubric


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
    container = nodes.container()
    if include_heading:
        container += _rubric(title=section[0])
    container.extend(
        item=copy_section(
            section=section,
            include_heading=False,
            exclude_sections=exclude_sections,
        )
    )
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
