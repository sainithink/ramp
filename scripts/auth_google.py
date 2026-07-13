"""
One-time Google OAuth flow. Run this before starting the server:
    python scripts/auth_google.py

It opens a browser for consent and saves google_token.json.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google_auth_oauthlib.flow import InstalledAppFlow
from config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar"]

client_config = {
    "installed": {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
creds = flow.run_local_server(port=0)

with open(settings.google_token_json_path, "w") as f:
    f.write(creds.to_json())

print(f"Token saved to {settings.google_token_json_path}")
