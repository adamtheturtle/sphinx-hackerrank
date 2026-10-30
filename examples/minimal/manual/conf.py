"""A standalone consumer with custom paths and Jinja context names."""

extensions = ["sphinx_hackerrank"]
project = "Widget exercise"
exclude_patterns = []
jinja2_contexts = {
    "snippets": {
        "variants": [
            {"name": "Python", "lexer": "python", "prompt": "print('widget')"},
            {"name": "JavaScript", "lexer": "javascript", "prompt": "console.log('widget');"},
        ]
    }
}
hackerrank_jinja_context = "snippets"
hackerrank_languages = {
    variant["lexer"]: {"name": variant["name"], "context": {"variants": [variant]}}
    for variant in jinja2_contexts["snippets"]["variants"]
}
