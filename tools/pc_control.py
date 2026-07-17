"""macOS system control — open apps, volume, screenshots."""
from __future__ import annotations

import asyncio
import logging
import subprocess
import time

log = logging.getLogger(__name__)

# Common app name aliases so voice commands like "open spotify" just work
_APP_ALIASES: dict[str, str] = {
    "spotify":      "Spotify",
    "chrome":       "Google Chrome",
    "firefox":      "Firefox",
    "safari":       "Safari",
    "terminal":     "Terminal",
    "vscode":       "Visual Studio Code",
    "code":         "Visual Studio Code",
    "finder":       "Finder",
    "notes":        "Notes",
    "calendar":     "Calendar",
    "messages":     "Messages",
    "facetime":     "FaceTime",
    "mail":         "Mail",
    "photos":       "Photos",
    "maps":         "Maps",
    "music":        "Music",
    "podcasts":     "Podcasts",
    "whatsapp":     "WhatsApp",
    "zoom":         "zoom.us",
    "slack":        "Slack",
    "calculator":   "Calculator",
    "settings":     "System Preferences",
    "system preferences": "System Preferences",
    "activity monitor":   "Activity Monitor",
}


def _run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    return result.stdout.strip()


async def open_app(app_name: str) -> str:
    """Open a macOS application by name."""
    resolved = _APP_ALIASES.get(app_name.lower().strip(), app_name)
    try:
        proc = await asyncio.create_subprocess_exec(
            "open", "-a", resolved,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            return f"Couldn't find '{resolved}'. Is it installed?"
        return f"Opened {resolved}."
    except Exception as exc:
        log.warning("open_app error: %s", exc)
        return f"Couldn't open {app_name}."


async def set_volume(level: int) -> str:
    """Set system volume 0–100."""
    level = max(0, min(100, level))
    script = f"set volume output volume {level}"
    await asyncio.to_thread(subprocess.run, ["osascript", "-e", script])
    return f"Volume set to {level}%."


async def mute_volume() -> str:
    await asyncio.to_thread(subprocess.run, ["osascript", "-e", "set volume with output muted"])
    return "Muted."


async def unmute_volume() -> str:
    await asyncio.to_thread(subprocess.run, ["osascript", "-e", "set volume without output muted"])
    return "Unmuted."


async def take_screenshot() -> str:
    """Take a screenshot and save to Desktop."""
    path = f"/Users/{_run(['whoami'])}/Desktop/saira_screenshot_{int(time.time())}.png"
    await asyncio.to_thread(subprocess.run, ["screencapture", "-x", path])
    return f"Screenshot saved to Desktop."


async def get_now_playing() -> str:
    """Get currently playing track from Music/Spotify."""
    script = '''
    tell application "System Events"
        set procs to name of every process
    end tell
    if procs contains "Spotify" then
        tell application "Spotify"
            if player state is playing then
                return "Spotify: " & name of current track & " by " & artist of current track
            else
                return "Spotify is paused."
            end if
        end tell
    else if procs contains "Music" then
        tell application "Music"
            if player state is playing then
                return "Apple Music: " & name of current track & " by " & artist of current track
            end if
        end tell
    end if
    return "Nothing is playing."
    '''
    result = await asyncio.to_thread(_run, ["osascript", "-e", script])
    return result or "Nothing is playing."
