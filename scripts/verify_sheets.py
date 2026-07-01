"""Smoke-test the Google Sheets store: connect, write a test booking, read it back.

Prereqs (see docs/GOOGLE_SHEETS_SETUP.md):
  export SHEET_ID=...                          # spreadsheet id from its URL
  export GOOGLE_SERVICE_ACCOUNT_JSON=./service-account.json
  # and share the sheet with the service account's client_email (Editor)

Run:  python scripts/verify_sheets.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> int:
    missing = [k for k in ("SHEET_ID", "GOOGLE_SERVICE_ACCOUNT_JSON")
               if not os.environ.get(k)]
    if missing:
        print(f"[x] Missing env: {', '.join(missing)}")
        print("    See docs/GOOGLE_SHEETS_SETUP.md")
        return 1

    os.environ["STORE"] = "sheets"
    from schemas import BookRequest
    from store import SheetsStore

    print("[..] Connecting to Google Sheets ...")
    try:
        store = SheetsStore()
    except Exception as e:  # noqa: BLE001 — surface the real cause to the user
        print(f"[x] Connect failed: {type(e).__name__}: {e}")
        _hint(e)
        return 1
    print("[ok] Connected, header row ensured.")

    # Idempotent test row (same id every run — won't pile up duplicates).
    when = (datetime.now() + timedelta(days=1)).replace(
        hour=20, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")
    req = BookRequest(name="SHEETS TEST", phone="+910000000001",
                      party_size=2, start_time=when, notes="verify script")

    bk, created = store.add(req, created_at=datetime.now().isoformat())
    print(f"[ok] Wrote booking {bk.id} (created={created}).")

    rows = store.list(phone="+910000000001")
    print(f"[ok] Read back {len(rows)} row(s) for the test phone.")
    if rows:
        r = rows[0]
        print(f"     -> {r.id} | {r.name} | party {r.party_size} | {r.start_time}")

    print("\n[done] Sheets store works. Run the app with STORE=sheets to go live.")
    print("       (You can delete the 'SHEETS TEST' row from the sheet.)")
    return 0


def _hint(e: Exception) -> None:
    msg = str(e).lower()
    if "permission" in msg or "403" in msg:
        print("    Hint: share the sheet with the service account's client_email "
              "(Editor). Find it inside the JSON key.")
    elif "not found" in msg or "404" in msg:
        print("    Hint: check SHEET_ID — it's the long id in the sheet URL "
              "(/spreadsheets/d/<THIS>/edit).")
    elif "api has not been" in msg or "disabled" in msg:
        print("    Hint: enable the Google Sheets API (and Drive API) in the "
              "Cloud project.")


if __name__ == "__main__":
    raise SystemExit(main())
