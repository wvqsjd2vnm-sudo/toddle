"""Opens Toddle with a saved login and returns the visible text of the pages we care about.

We deliberately capture page text instead of relying on CSS selectors: Toddle's markup
differs per school/version, and Claude is far more robust at reading text than we are at
guessing selectors.
"""
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


def fetch_pages(headless: bool = True) -> dict[str, str]:
    if not config.STATE_FILE.exists():
        raise SystemExit("Not logged in. Run: python -m toddle_agent login")
    texts: dict[str, str] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        ctx = browser.new_context(storage_state=str(config.STATE_FILE))
        page = ctx.new_page()
        for path in config.PAGES:
            page.goto(config.TODDLE_URL.rstrip("/") + path, wait_until="networkidle")
            page.wait_for_timeout(1500)
            # scroll to trigger lazy loading
            for _ in range(5):
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(400)
            texts[path] = page.inner_text("body")
        ctx.storage_state(path=str(config.STATE_FILE))  # refresh session
        browser.close()
    return texts
