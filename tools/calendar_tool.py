import asyncio
import os
from datetime import datetime, timezone

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _load_credentials() -> Credentials:
    token_path = settings.google_token_json_path
    if not os.path.exists(token_path):
        raise FileNotFoundError(
            f"Google token not found at {token_path}. "
            "Run: python scripts/auth_google.py"
        )
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


def _list_events_sync(max_results: int) -> str:
    creds = _load_credentials()
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)
    now = datetime.now(timezone.utc).isoformat()
    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    items = result.get("items", [])
    if not items:
        return "You have no upcoming events."

    lines = []
    for event in items:
        start = event["start"].get("dateTime", event["start"].get("date", ""))
        summary = event.get("summary", "Untitled event")
        try:
            dt = datetime.fromisoformat(start)
            formatted = dt.strftime("%A %B %-d at %-I:%M %p")
        except Exception:
            formatted = start
        lines.append(f"{summary} on {formatted}")

    return "Your upcoming events: " + "; ".join(lines) + "."


def _create_event_sync(title: str, start_iso: str, end_iso: str, description: str) -> str:
    creds = _load_credentials()
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    local_tz = datetime.now().astimezone().tzname()

    def _ensure_tz(iso: str) -> str:
        if "+" not in iso and "Z" not in iso and iso.count("-") < 3:
            return datetime.fromisoformat(iso).astimezone().isoformat()
        return iso

    event_body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": _ensure_tz(start_iso)},
        "end": {"dateTime": _ensure_tz(end_iso)},
    }
    created = service.events().insert(calendarId="primary", body=event_body).execute()
    link = created.get("htmlLink", "")
    return f"Event '{title}' created successfully."


async def list_events(max_results: int = 5) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _list_events_sync, max_results)


async def create_event(title: str, start_iso: str, end_iso: str, description: str = "") -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _create_event_sync, title, start_iso, end_iso, description)
