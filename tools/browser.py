"""Open the app in headless Chrome (the installed Google Chrome, software
WebGL), for check.py and shot.py. Page errors and console errors are
collected in `page.errors`."""

from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from paths import INDEX_HTML


@contextmanager
def app(width=1400, height=900):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True,
                                    args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": width, "height": height})
        page.errors = []
        page.on("pageerror", lambda e: page.errors.append(f"page error: {e}"))
        page.on("console", lambda m: m.type == "error" and page.errors.append(f"console: {m.text}"))
        page.goto(INDEX_HTML.as_uri())
        page.wait_for_function("window.ANATOMY_DEBUG", timeout=60000)
        try:
            yield page
        finally:
            browser.close()
