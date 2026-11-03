"""Exercise upstream copy controls in pages and self-contained exports."""

import textwrap
from base64 import b64decode
from pathlib import Path
from tempfile import TemporaryDirectory

from bs4 import BeautifulSoup
from playwright.sync_api import Page, expect, sync_playwright
from sphinx.application import Sphinx
from sphinx.util.docutils import docutils_namespace

from sphinx_hackerrank import GuidelineExport


def _check_page(*, page: Page, path: Path) -> None:
    """Copy every block with upstream newline handling and keyboard access."""
    _ = page.goto(url=path.as_uri())
    _ = page.locator(selector="details").evaluate_all(
        expression="nodes => nodes.forEach(node => { node.open = true; })"
    )
    for image in page.locator(selector="img").all():
        assert image.evaluate(
            expression="image => image.complete && image.naturalWidth > 0"
        )
    blocks = page.locator(selector=".hr-interviewer-guideline pre")
    buttons = page.locator(selector=".copybtn")
    assert blocks.count() > 0
    expect(actual=buttons).to_have_count(count=blocks.count())
    for index in range(blocks.count()):
        displayed = blocks.nth(index=index).text_content()
        assert displayed is not None
        buttons.nth(index=index).click()
        expect(actual=buttons.nth(index=index)).to_have_attribute(
            name="data-tooltip", value="Copied!"
        )
        assert page.evaluate(
            expression="navigator.clipboard.readText()"
        ) == displayed.removesuffix("\n")
    # Displayed line numbers must not enter the clipboard.
    displayed = blocks.first.text_content()
    assert displayed is not None
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
    assert page.evaluate(
        expression="navigator.clipboard.readText()"
    ) == displayed.removesuffix("\n")
    _ = blocks.first.locator(selector_or_locator=".linenos").evaluate(
        expression="node => node.remove()"
    )
    # Change the clipboard first so an unchanged value cannot mask a failure.
    _ = page.evaluate(
        expression="navigator.clipboard.writeText('keyboard sentinel')"
    )
    buttons.first.focus()
    buttons.first.press(key="Enter")
    assert page.evaluate(
        expression="navigator.clipboard.readText()"
    ) == displayed.removesuffix("\n")


def _build_fixture(
    *, directory: Path, code: str, prompt: str
) -> tuple[Path, Path]:
    """Build with only this extension enabled, using upstream settings."""
    source = directory / "source"
    source.mkdir(parents=True)
    (source / "conf.py").touch()
    _ = (source / "code.txt").write_text(data=code, encoding="utf-8")
    _ = (source / "pixel.png").write_bytes(
        data=b64decode(
            s="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a2ioAAAAASUVORK5CYII="
        )
    )
    _ = (source / "index.rst").write_text(
        data=textwrap.dedent(
            text="""\
            Interviewer Guideline
            =====================

            .. container:: hr-interviewer-guideline selected-guide

               .. literalinclude:: code.txt
                  :language: text

               .. code-block:: text

                  A different block.

               .. image:: pixel.png
                  :alt: Example pixel
            """
        ),
        encoding="utf-8",
    )
    fixture_output = directory / "output"
    with docutils_namespace():
        app = Sphinx(
            srcdir=source,
            confdir=source,
            outdir=fixture_output,
            doctreedir=directory / "doctrees",
            buildername="hackerrank",
            confoverrides={
                "extensions": ["sphinx_hackerrank"],
                "copybutton_prompt_text": prompt,
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
    return fixture, fixture_output / "index.html"


def main() -> None:
    """Check offline exports, ordinary pages, settings, and plain HTML."""
    root = Path(__file__).resolve().parents[1]
    output = root / "sample/build"
    code = '  if x < 3 && y > 0:\n\tprint("\u03bb & </script>")\n\n'
    with TemporaryDirectory() as directory, sync_playwright() as automation:
        fixture, website = _build_fixture(
            directory=Path(directory), code=code, prompt=""
        )
        browser = automation.chromium.launch()
        context = browser.new_context(
            permissions=["clipboard-read", "clipboard-write"],
            offline=True,
        )
        page = context.new_page()
        errors: list[str] = []
        page.on(
            event="pageerror", f=lambda error: errors.append(str(object=error))
        )
        for path in (
            website,
            output / "interviewer-guidelines/topics/widgets/guide.html",
            fixture,
        ):
            _check_page(page=page, path=path)
        rendered_code = page.locator(selector="pre").first.text_content()
        soup = BeautifulSoup(
            markup=fixture.read_text(encoding="utf-8"), features="html.parser"
        )
        script = soup.select_one(selector="script[data-sphinx-copybutton]")
        assert script is not None
        # Repeated fragments and repeated assets must share one initialization.
        _ = page.add_script_tag(content=script.get_text())
        expect(actual=page.locator(selector=".copybtn")).to_have_count(count=4)
        configured, configured_website = _build_fixture(
            directory=Path(directory) / "configured",
            code=">>> print('configured')\n",
            prompt=">>> ",
        )
        for path in (configured, configured_website):
            _ = page.goto(url=path.as_uri())
            page.locator(selector=".copybtn").first.click()
            assert (
                page.evaluate(expression="navigator.clipboard.readText()")
                == "print('configured')"
            )
        assert not bool(errors)
        plain = browser.new_context(java_script_enabled=False).new_page()
        _ = plain.goto(url=fixture.as_uri())
        expect(actual=plain.get_by_role(role="button")).to_have_count(count=0)
        for image in plain.locator(selector="img").all():
            assert image.evaluate(
                expression="image => image.complete && image.naturalWidth > 0"
            )
        assert (
            plain.locator(selector="pre").first.text_content() == rendered_code
        )
        browser.close()
    print("Upstream code-copy browser checks passed.")


if __name__ == "__main__":
    main()
