"""Move the old single-user data into a user account.

Before multi-tenancy there was one profile, one memory and one preference file
at the project root, each with its own key. Those files are not read any more,
so without this their contents would simply be stranded.

    .venv/bin/python3.14 scripts/migrate_to_multiuser.py --email you@example.com

Reads memory.enc / preferences.enc / profile.enc with the original per-file
keys, then writes them into the named account, re-encrypted under that user's
derived key. The old files are left untouched so this can be re-run or undone.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.fernet import Fernet
from sqlalchemy import select

from core.db import User, get_session, init_db
from core.userdata import _write_blob

OLD = {
    "memory":      (Path(".memory.key"),  Path("memory.enc")),
    "preferences": (Path(".prefs.key"),   Path("preferences.enc")),
    "profile":     (Path(".profile.key"), Path("profile.enc")),
}


def read_old(kind: str):
    key_file, data_file = OLD[kind]
    if not key_file.exists() or not data_file.exists():
        return None
    try:
        raw = Fernet(key_file.read_bytes()).decrypt(data_file.read_bytes())
        return json.loads(raw)
    except Exception as exc:
        print(f"  ! could not read {data_file}: {exc}")
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True, help="account to migrate into")
    ap.add_argument("--write", action="store_true", help="actually write (default is a dry run)")
    args = ap.parse_args()

    init_db()
    with get_session() as s:
        user = s.scalar(select(User).where(User.email == args.email.strip().lower()))
        if not user:
            sys.exit(f"No account for {args.email}. Register it first at /register.")
        user_id, wake = user.id, user.wake_name

    print(f"Target: {args.email}  ({user_id[:8]}, calls it {wake})\n")

    found = {}
    for kind in OLD:
        data = read_old(kind)
        if data is None:
            print(f"  {kind:12} — nothing to migrate")
            continue
        if kind == "memory":
            print(f"  {kind:12} — {len(data)} exchanges")
        elif kind == "preferences":
            for rule in data.values():
                print(f"  {kind:12} — {rule.get('text','')}")
        else:
            print(f"  {kind:12} — {', '.join(data.keys())}")
        found[kind] = data

    if not found:
        print("\nNothing found to migrate.")
        return
    if not args.write:
        print("\nDry run. Re-run with --write to import.")
        return

    for kind, data in found.items():
        _write_blob(user_id, kind, json.dumps(data, ensure_ascii=False))
    print(f"\nImported {', '.join(found)} into {args.email}.")
    print("The old .enc files were left in place — delete them once you've "
          "confirmed everything is there.")


if __name__ == "__main__":
    main()
