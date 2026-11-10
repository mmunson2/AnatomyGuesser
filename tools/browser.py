"""Open the app in headless Chrome (the installed Google Chrome, software
WebGL), for check.py and shot.py. Page errors and console errors are
collected in `page.errors`."""

from contextlib import contextmanager

from playwright.sync_api import sync_playwright

from paths import INDEX_HTML


# A phone, for the notecards page (cards.html), where index.html sends phones.
PHONE = {"user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
                       "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
         "viewport": {"width": 390, "height": 844}, "is_mobile": True, "has_touch": True}


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
