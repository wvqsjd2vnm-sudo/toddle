"""Opens Toddle with a saved login and returns the visible text of the pages we care about.

We deliberately capture page text instead of relying on CSS selectors: Toddle's markup
differs per school/version, and Claude is far more robust at reading text than we are at
guessing selectors.
"""
import os

from playwright.sync_api import sync_playwright

from . import config


def login_interactive() -> None:
    """Open a visible browser so a parent logs in themselves (handles OTP/Google/MFA).
    The session is saved locally; no password is ever stored by this tool."""
    config.SESSION_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.goto(config.TODDLE_URL)
        input("Log in to Toddle in the browser window, open your son's profile, then press Enter here...")
        ctx.storage_state(path=str(config.STATE_FILE))
        browser.close()
    print(f"Session saved to {config.STATE_FILE}")


def _page_text(page) -> str:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)
    for _ in range(5):  # scroll to trigger lazy loading
        page.mouse.wheel(0, 3000)
        page.wait_for_timeout(400)
    return page.inner_text("body")


def _links(page) -> list[dict]:
    return page.eval_on_selector_all(
        "a[href], [role=link], nav *, [role=tab], [role=menuitem]",
        """els => els.map(e => ({text: (e.innerText||'').trim().slice(0,60),
                               href: e.getAttribute('href')||''}))
                    .filter(x => x.text)""",
    )


def discover_pages(page, pick) -> list[str]:
    """Look at the home page's menu and let `pick(links)` choose which link texts to open."""
    seen, uniq = set(), []
    for l in _links(page):
        if l["text"] not in seen:
            seen.add(l["text"])
            uniq.append(l)
    return pick(uniq)


def fetch_pages(headless: bool = True, pick=None) -> dict[str, str]:
    if not config.STATE_FILE.exists():
        raise SystemExit("Not logged in. Run: python -m toddle_agent login")
    texts: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, executable_path=os.getenv("CHROMIUM_PATH") or None)
        ctx = browser.new_context(storage_state=str(config.STATE_FILE))
        page = ctx.new_page()
        page.goto(config.TODDLE_URL, wait_until="networkidle")
        texts["home"] = _page_text(page)
        if pick and not config.PAGES_EXPLICIT:
            for name in discover_pages(page, pick):
                try:
                    page.goto(config.TODDLE_URL, wait_until="networkidle")
                    page.get_by_text(name, exact=True).first.click(timeout=5000)
                    texts[name] = _page_text(page)
                except Exception as e:  # a menu item that won't open shouldn't kill the run
                    print(f"skipped '{name}': {e}")
        else:
            for path in config.PAGES:
                page.goto(config.TODDLE_URL.rstrip("/") + path, wait_until="networkidle")
                texts[path] = _page_text(page)
        ctx.storage_state(path=str(config.STATE_FILE))  # refresh session
        browser.close()
    return texts
