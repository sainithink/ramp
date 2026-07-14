"""
Interactive script to create / update your encrypted personal profile.
Run: python scripts/setup_profile.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.profile import save_profile, load_profile, PROFILE_ENC
import json

FIELDS = [
    ("name",            "Your full name"),
    ("location",        "Where you live (city, country)"),
    ("occupation",      "Your job / role"),
    ("interests",       "Hobbies and interests (comma separated)"),
    ("daily_routine",   "Typical daily schedule (optional)"),
    ("preferences",     "Personal preferences — food, music, etc. (optional)"),
    ("family",          "People close to you — family, partner, friends (optional)"),
    ("goals",           "Things you're working toward or want help with (optional)"),
    ("notes",           "Anything else Jarvis should know about you (optional)"),
]

print("\n=== Jarvis Personal Profile Setup ===")
print("This data is encrypted and stored only on your machine.\n")

existing = {}
if PROFILE_ENC.exists():
    try:
        from cryptography.fernet import Fernet
        from core.profile import _get_or_create_key, PROFILE_ENC
        key = _get_or_create_key()
        existing = json.loads(Fernet(key).decrypt(PROFILE_ENC.read_bytes()))
        print("Existing profile found. Press Enter to keep current value.\n")
    except Exception:
        pass

data = {}
for field, label in FIELDS:
    current = existing.get(field, "")
    prompt  = f"{label}"
    if current:
        prompt += f" [{current}]"
    prompt += ": "
    value = input(prompt).strip()
    data[field] = value if value else current

save_profile(data)
print("\nProfile saved and encrypted. Jarvis will use this context in all conversations.")
