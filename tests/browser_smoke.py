"""Exercise code copying in a real browser, outside the pytest matrix."""

import textwrap
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import Page, expect, sync_playwright
from sphinx.application import Sphinx

from sphinx_hackerrank import GuidelineExport


def _check_page(*, page: Page, path: Path) -> None:
    """Copy every code block, checking exact clipboard contents."""
    _ = page.goto(url=path.as_uri())
    _ = page.locator(selector="details").evaluate_all(
        expression="nodes => nodes.forEach(node => { node.open = true; })"
    )
    blocks = page.locator(selector=".hr-interviewer-guideline pre")
    buttons = page.get_by_role(role="button", name="Copy code")
    assert blocks.count() > 0
    expect(actual=buttons).to_have_count(count=blocks.count())
    for index in range(blocks.count()):
        expected = blocks.nth(index=index).text_content()
        buttons.nth(index=index).click()
        expect(
            actual=page.get_by_role(role="status").nth(index=index)
        ).to_have_text(expected="Copied")
        copied = page.evaluate(expression="navigator.clipboard.readText()")
        assert copied == expected
    # Displayed line numbers must not enter the clipboard.
    expected = blocks.first.text_content()
    _ = blocks.first.evaluate(
        expression=textwrap.dedent(
            text="""\
            pre => {
                const number = document.createElement('span');
                number.className = 'linenos';
                number.textContent = '1';
                pre.prepend(number);
            }
            """
        )
    )
    buttons.first.click()
    expect(actual=page.get_by_role(role="status").first).to_have_text(
        expected="Copied"
    )
    assert (
        page.evaluate(expression="navigator.clipboard.readText()") == expected
    )
    _ = blocks.first.locator(selector_or_locator=".linenos").evaluate(
        expression="node => node.remove()"
    )
    buttons.first.focus()
    buttons.first.press(key="Enter")
    expect(actual=page.get_by_role(role="status").first).to_have_text(
        expected="Copied"
    )
    assert (
        page.evaluate(expression="navigator.clipboard.readText()")
        == blocks.first.text_content()
    )


def _build_fixture(*, directory: Path, code: str) -> Path:
    """Generate clipboard examples from native RST and included files."""
    source = directory / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "code.txt").write_text(data=code, encoding="utf-8")
    (source / "empty.txt").touch()
    classes = "hr-interviewer-guideline selected-guide"
    _ = (source / "index.rst").write_text(
        data=textwrap.dedent(
            text=f"""\
            Interviewer Guideline
            =====================

            .. container:: {classes}

               .. literalinclude:: code.txt
                  :language: text

               .. literalinclude:: empty.txt
                  :language: text
            """
        ),
        encoding="utf-8",
    )
    fixture_output = directory / "output"
    app = Sphinx(
        srcdir=source,
        confdir=source,
        outdir=fixture_output,
        doctreedir=directory / "doctrees",
        buildername="hackerrank",
        confoverrides={
            "extensions": ["sphinx_hackerrank"],
            "hackerrank_exports": [
                GuidelineExport(
                    docname="index",
                    selector=".selected-guide",
                    output_path="interviewer-guidelines/index/guide.html",
                    name="Example",
                )
            ],
        },
        warningiserror=True,
    )
    app.build()
    assert app.statuscode == 0
    fragment = (
        fixture_output / "interviewer-guidelines/index/guide.html"
    ).read_text(encoding="utf-8")
    fixture = directory / "guidelines.html"
    _ = fixture.write_text(data=fragment + fragment, encoding="utf-8")
    return fixture


def main() -> None:
    """Check clipboard APIs, fallback copying, and script-free
    rendering.
    """
    root = Path(__file__).resolve().parents[1]
    output = root / "sample/build"
    script = root / "src/sphinx_hackerrank/static/interviewer_guideline.js"
    code = '  if x < 3 && y > 0:\n\tprint("\u03bb & </script>")\n\n'
    with TemporaryDirectory() as directory, sync_playwright() as automation:
        fixture = _build_fixture(directory=Path(directory), code=code)
        browser = automation.chromium.launch()
        context = browser.new_context(
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = context.new_page()
        for path in (
            output / "interviewer-guidelines/topics/widgets/guide.html",
            output / "topics/widgets-interviewer-guideline.html",
            fixture,
        ):
            _check_page(page=page, path=path)
        rendered_code = page.locator(selector="pre").first.text_content()
        # Loading the asset again must not add duplicate controls.
        _ = page.add_script_tag(path=script)
        expect(
            actual=page.get_by_role(role="button", name="Copy code")
        ).to_have_count(count=4)
        _ = page.evaluate(
            expression=textwrap.dedent(
                text="""\
                () => {
                    window.readClipboard = navigator.clipboard.readText.bind(
                        navigator.clipboard,
                    );
                    Object.defineProperty(navigator, 'clipboard', {
                        configurable: true,
                        value: {
                            writeText: () => Promise.reject(
                                new Error('Denied'),
                            ),
                        },
                    });
                }
                """
            )
        )
        button = page.get_by_role(role="button", name="Copy code").first
        button.click()
        expect(actual=page.get_by_role(role="status").first).to_have_text(
            expected="Copied"
        )
        assert (
            page.evaluate(expression="window.readClipboard()") == rendered_code
        )
        _ = page.evaluate(
            expression="Object.defineProperty(navigator, 'clipboard', "
            "{value: undefined})"
        )
        button.click()
        expect(actual=page.get_by_role(role="status").first).to_have_text(
            expected="Copied"
        )
        assert (
            page.evaluate(expression="window.readClipboard()") == rendered_code
        )
        expect(actual=button).to_be_focused()
        _ = page.evaluate(expression="document.execCommand = () => false")
        button.click()
        expect(actual=page.get_by_role(role="status").first).to_have_text(
            expected="Copy failed. Select and copy the code manually."
        )
        expect(actual=button).to_be_enabled()
        assert button.get_attribute(name="aria-busy") is None
        expect(actual=button).to_be_focused()
        assert page.locator(selector="textarea").count() == 0
        assert (
            page.locator(selector="pre").first.text_content() == rendered_code
        )
        plain = browser.new_context(java_script_enabled=False).new_page()
        _ = plain.goto(url=fixture.as_uri())
        expect(actual=plain.get_by_role(role="button")).to_have_count(count=0)
        assert (
            plain.locator(selector="pre").first.text_content() == rendered_code
        )
        browser.close()
    print("Code-copy browser checks passed.")


if __name__ == "__main__":
    main()
