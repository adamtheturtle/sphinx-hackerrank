"""A consumer supplies a template context and explicit export
destination.
"""

from sphinx_hackerrank import GuidelineExport

extensions = ["sphinx_hackerrank"]
project = "Widget exercise"
jinja2_contexts = {"snippets": {"example": "print('widget')"}}
hackerrank_exports = [
    GuidelineExport(
        docname="topics/widgets-interviewer-guideline",
        selector=".hr-interviewer-guideline",
        output_path="interviewer-guidelines/topics/widgets/guide.html",
        name="Widget review",
    )
]
