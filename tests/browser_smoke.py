"""Check preview assets and actual clipboard copying in Chromium."""

import textwrap
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import expect, sync_playwright
from sphinx.application import Sphinx

from sphinx_hackerrank import GuidelineExport


def main() -> None:
    """Follow the preview index and copy code from native disclosures."""
    code = '  if x < 3 && y > 0:\n\n\tprint("λ & </script>")\n'
    with TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "source"
        source.mkdir()
        (source / "conf.py").touch()
        _ = (source / "code.txt").write_text(data=code, encoding="utf-8")
        _ = (source / "index.rst").write_text(
            data=textwrap.dedent(
                text="""\
                Guide
                =====

                .. container:: hr-interviewer-guideline

                   .. collapse:: Example

                      .. literalinclude:: code.txt
                         :language: text
                         :linenos:
                """
            ),
            encoding="utf-8",
        )
        target = GuidelineExport(
            docname="index",
            selector=".hr-interviewer-guideline",
            output_path="exports/nested/guide.html",
            name="Example",
        )
        app = Sphinx(
            srcdir=source,
            confdir=source,
            outdir=root / "output",
            doctreedir=root / "doctrees",
            buildername="hackerrank",
            confoverrides={
                "extensions": [
                    "sphinx_hackerrank",
                    "sphinx_copybutton",
                    "sphinx_toolbox.collapse",
                ],
                "hackerrank_exports": [target],
            },
            warningiserror=True,
        )
        app.build()
        assert app.statuscode == 0
        with sync_playwright() as automation:
            browser = automation.chromium.launch()
            context = browser.new_context(
                permissions=["clipboard-read", "clipboard-write"]
            )
            page = context.new_page()
            errors: list[str] = []
            page.on(
                event="pageerror",
                f=lambda error: errors.append(str(object=error)),
            )
            _ = page.goto(
                url=(
                    root / "output/interviewer-guidelines/index.html"
                ).as_uri()
            )
            page.get_by_role(role="link", name="Example").click()
            assert page.url.endswith(target.preview_path)
            page.locator(selector="summary").click()
            buttons = page.locator(selector=".copybtn")
            expect(actual=buttons).to_have_count(count=1)
            assert page.locator(selector="pre").text_content() == code
            for keyboard in (False, True):
                if keyboard:
                    buttons.focus()
                    buttons.press(key="Enter")
                else:
                    buttons.click()
                expect(actual=buttons).to_have_attribute(
                    name="data-tooltip", value="Copied!"
                )
                # The copy extension removes one final newline by default.
                assert page.evaluate(
                    expression="navigator.clipboard.readText()"
                ) == code.removesuffix("\n")
            assert not bool(errors)
            _ = page.goto(url=(root / "output" / target.output_path).as_uri())
            expect(actual=page.locator(selector="script")).to_have_count(
                count=0
            )
            assert page.locator(selector="pre").text_content() == code
            context.close()
            context = browser.new_context(java_script_enabled=False)
            page = context.new_page()
            _ = page.goto(url=(root / "output" / target.preview_path).as_uri())
            page.locator(selector="summary").click()
            expect(actual=page.locator(selector="pre")).to_be_visible()
            browser.close()


if __name__ == "__main__":
    main()
