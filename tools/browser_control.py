"""Browser automation via Playwright — lets SAIRA control Chrome."""
from __future__ import annotations

import asyncio
import logging
from urllib.parse import quote_plus

log = logging.getLogger(__name__)

_pw = None
_browser = None
_context = None
_page = None
_lock = asyncio.Lock()


async def _get_page():
    """Return a shared Playwright page, launching browser on first call."""
    global _pw, _browser, _context, _page
    async with _lock:
        if _page and not _page.is_closed():
            return _page
        from playwright.async_api import async_playwright
        _pw = await async_playwright().start()
        _browser = await _pw.chromium.launch(headless=False, args=["--start-maximized"])
        _context = await _browser.new_context(viewport=None)
        _page = await _context.new_page()
        log.info("Browser launched")
    return _page


async def play_youtube(query: str) -> str:
    """Search YouTube and play the first result."""
    try:
        page = await _get_page()
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        # Click the first video thumbnail (not an ad)
        await page.wait_for_selector("ytd-video-renderer a#thumbnail", timeout=8000)
        first = page.locator("ytd-video-renderer a#thumbnail").first
        await first.click()
        await page.wait_for_load_state("domcontentloaded", timeout=8000)
        title = await page.title()
        log.info("Playing: %s", title)
        return f"Playing on YouTube: {title.replace(' - YouTube', '').strip()}"
    except Exception as exc:
        log.warning("play_youtube error: %s", exc)
        return f"Opened YouTube search for '{query}' — click a video to play."


async def open_website(url: str) -> str:
    """Open any URL in the browser."""
    try:
        if not url.startswith("http"):
            url = "https://" + url
        page = await _get_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        title = await page.title()
        return f"Opened: {title or url}"
    except Exception as exc:
        log.warning("open_website error: %s", exc)
        return f"Tried to open {url} — check the browser."


async def google_search(query: str) -> str:
    """Search Google and show results."""
    try:
        page = await _get_page()
        url = f"https://www.google.com/search?q={quote_plus(query)}"
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return f"Searched Google for: {query}"
    except Exception as exc:
        log.warning("google_search error: %s", exc)
        return f"Searched for '{query}' — check the browser."
