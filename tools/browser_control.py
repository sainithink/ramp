"""Browser control — opens pages in the user's real browser.

YouTube search runs in a headless Playwright page purely to resolve the first
result's URL; the video itself is then handed to the user's own browser via
`open`, so it plays with their session, logins and extensions.
"""
from __future__ import annotations

import asyncio
import logging
import re
from urllib.parse import quote_plus

log = logging.getLogger(__name__)

# Spoken browser name → macOS application name
_BROWSERS: dict[str, str] = {
    "firefox": "Firefox",
    "chrome":  "Google Chrome",
    "google chrome": "Google Chrome",
    "safari":  "Safari",
    "brave":   "Brave Browser",
    "edge":    "Microsoft Edge",
    "opera":   "Opera",
}

_pw = None
_browser = None
_lock = asyncio.Lock()


def _resolve_browser(name: str | None) -> str | None:
    """Map a spoken browser name to a macOS app name, or None for the default."""
    if not name:
        return None
    return _BROWSERS.get(name.lower().strip())


async def _open_in_browser(url: str, browser: str | None = None) -> None:
    """Hand a URL to the user's real browser."""
    app = _resolve_browser(browser)
    cmd = ["open", "-a", app, url] if app else ["open", url]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError((stderr or b"").decode().strip() or f"could not open {url}")


async def _get_headless_page():
    """Shared headless page, used only to resolve search results to a URL."""
    global _pw, _browser
    async with _lock:
        if _browser is None or not _browser.is_connected():
            from playwright.async_api import async_playwright
            _pw = await async_playwright().start()
            _browser = await _pw.chromium.launch(headless=True)
            log.info("Headless resolver browser launched")
    return await _browser.new_page()


async def _first_youtube_result(query: str) -> tuple[str, str] | None:
    """Return (video_url, title) for the first non-ad result, or None."""
    page = None
    try:
        page = await _get_headless_page()
        await page.goto(
            f"https://www.youtube.com/results?search_query={quote_plus(query)}",
            wait_until="domcontentloaded", timeout=15000,
        )
        await page.wait_for_selector("ytd-video-renderer a#video-title", timeout=8000)
        link = page.locator("ytd-video-renderer a#video-title").first
        href = await link.get_attribute("href")
        title = (await link.get_attribute("title")) or query
        if not href:
            return None
        # Strip playlist/index params so it opens as a plain video
        video_id = re.search(r"v=([\w-]+)", href)
        url = f"https://www.youtube.com/watch?v={video_id.group(1)}" if video_id \
            else f"https://www.youtube.com{href}"
        return url, title
    except Exception as exc:
        log.warning("YouTube resolve failed: %s", exc)
        return None
    finally:
        if page:
            try:
                await page.close()
            except Exception:
                pass


async def play_youtube(query: str, browser: str | None = None) -> str:
    """Find a song/video on YouTube and play it in the user's browser."""
    found = await _first_youtube_result(query)
    where = _resolve_browser(browser) or "your browser"
    try:
        if found:
            url, title = found
            await _open_in_browser(f"{url}&autoplay=1", browser)
            return f"Playing {title} in {where}."
        # Fall back to the search page so the user still gets somewhere useful
        await _open_in_browser(
            f"https://www.youtube.com/results?search_query={quote_plus(query)}", browser
        )
        return f"Opened YouTube search for {query} in {where}."
    except Exception as exc:
        log.warning("play_youtube error: %s", exc)
        return f"Couldn't open {where}. Is it installed?"


async def open_website(url: str, browser: str | None = None) -> str:
    """Open any URL in the user's browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    where = _resolve_browser(browser) or "your browser"
    try:
        await _open_in_browser(url, browser)
        return f"Opened {url} in {where}."
    except Exception as exc:
        log.warning("open_website error: %s", exc)
        return f"Couldn't open {where}. Is it installed?"


async def google_search(query: str, browser: str | None = None) -> str:
    """Search Google in the user's browser."""
    where = _resolve_browser(browser) or "your browser"
    try:
        await _open_in_browser(
            f"https://www.google.com/search?q={quote_plus(query)}", browser
        )
        return f"Searched Google for {query}."
    except Exception as exc:
        log.warning("google_search error: %s", exc)
        return f"Couldn't open {where}. Is it installed?"
