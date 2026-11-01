"""A consumer authors ordinary RST and supplies explicit exports."""

from sphinx_hackerrank import GuidelineExport

extensions = [
    "sphinx_hackerrank",
    "sphinx_section_include",
    "sphinx_toolbox.collapse",
]
project = "Widget exercise"
hackerrank_exports = [
    GuidelineExport(
        docname="topics/widgets-interviewer-guideline",
        selector=".hr-interviewer-guideline",
        output_path="interviewer-guidelines/topics/widgets/guide.html",
        name="Widget review",
    )
]
