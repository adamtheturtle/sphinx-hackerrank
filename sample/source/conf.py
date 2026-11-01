"""A standalone consumer with custom paths and Jinja context names."""

from sphinx_hackerrank.layout import (
    GuidelineLayout,
    SectionGroup,
    SectionSelection,
)

extensions = ["sphinx_hackerrank"]
project = "Widget exercise"
exclude_patterns: list[str] = []
jinja2_contexts = {
    "snippets": {
        "variants": [
            {"name": "Python", "lexer": "python", "prompt": "print('widget')"},
            {
                "name": "JavaScript",
                "lexer": "javascript",
                "prompt": "console.log('widget');",
            },
        ]
    }
}
hackerrank_jinja_context = "snippets"
hackerrank_languages = {
    variant["lexer"]: {
        "name": variant["name"],
        "context": {"variants": [variant]},
    }
    for variant in jinja2_contexts["snippets"]["variants"]
}

hackerrank_guideline_layouts = {
    "widgets": GuidelineLayout(
        part_pattern=r"Part [1-9]\d*",
        groups=tuple(
            SectionGroup(
                title=heading,
                sections=(SectionSelection(headings=(heading,)),),
            )
            for heading in ("Prompt", "Follow up questions", "FAQ")
        ),
        introduction="See the `full guide <{source_url}>`_.",
    ),
}
