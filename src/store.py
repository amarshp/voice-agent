"""Booking store. Repository pattern: JSONStore (dev) or SheetsStore (prod).

Both are append-only with idempotent IDs so a retried tool call never
double-books. ID = hash(phone + start_time) -> same reservation collapses.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path

from schemas import Booking, BookRequest


def booking_id(phone: str, start_time: str) -> str:
    raw = f"{phone.strip()}|{start_time.strip()}"
    return "bk_" + hashlib.sha256(raw.encode()).hexdigest()[:12]


class Store:
    def add(self, req: BookRequest, created_at: str) -> tuple[Booking, bool]:
        """Return (booking, created). created=False if it already existed."""
        raise NotImplementedError

    def list(self, phone: str | None = None, date: str | None = None) -> list[Booking]:
        raise NotImplementedError


class JSONStore(Store):
    """Local file store for dev/testing. No external creds needed."""

    def __init__(self, path: str = "data/bookings.json") -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text("[]", encoding="utf-8")

    def _read(self) -> list[dict]:
        return json.loads(self._path.read_text(encoding="utf-8") or "[]")

    def _write(self, rows: list[dict]) -> None:
        self._path.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    def add(self, req: BookRequest, created_at: str) -> tuple[Booking, bool]:
        bid = booking_id(req.phone, req.start_time)
        with self._lock:
            rows = self._read()
            for r in rows:
                if r["id"] == bid and r["status"] == "confirmed":
                    return Booking(**r), False
            booking = Booking(
                id=bid, name=req.name, phone=req.phone,
                party_size=req.party_size, start_time=req.start_time,
                notes=req.notes, created_at=created_at,
            )
            rows.append(booking.model_dump())
            self._write(rows)
            return booking, True

    def list(self, phone: str | None = None, date: str | None = None) -> list[Booking]:
        rows = self._read()
        out = []
        for r in rows:
            if r["status"] != "confirmed":
                continue
            if phone and r["phone"].strip() != phone.strip():
                continue
            if date and not r["start_time"].startswith(date):
                continue
            out.append(Booking(**r))
        return sorted(out, key=lambda b: b.start_time)


class SheetsStore(Store):
    """Google Sheets store (prod). Append-only. Requires a service account.

    Env:
      GOOGLE_SERVICE_ACCOUNT_JSON  path to the service-account key file
      SHEET_ID                     the target spreadsheet id (share it with the
                                   service account's client_email)
    """

    COLS = ["id", "name", "phone", "party_size", "start_time",
            "status", "notes", "created_at"]

    def __init__(self) -> None:
        import gspread  # imported lazily so dev doesn't need the dep

        key = os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
        sheet_id = os.environ["SHEET_ID"]
        self._lock = threading.Lock()
        gc = gspread.service_account(filename=key)
        self._ws = gc.open_by_key(sheet_id).sheet1
        # Ensure header row exists.
        if self._ws.row_values(1) != self.COLS:
            self._ws.update([self.COLS], "A1")

    def _rows(self) -> list[dict]:
        return self._ws.get_all_records()

    def add(self, req: BookRequest, created_at: str) -> tuple[Booking, bool]:
        bid = booking_id(req.phone, req.start_time)
        with self._lock:
            for r in self._rows():
                if str(r["id"]) == bid and r["status"] == "confirmed":
                    return Booking(**{k: r[k] for k in self.COLS}), False
            booking = Booking(
                id=bid, name=req.name, phone=req.phone,
                party_size=req.party_size, start_time=req.start_time,
                notes=req.notes, created_at=created_at,
            )
            d = booking.model_dump()
            self._ws.append_row([d[c] if d[c] is not None else "" for c in self.COLS])
            return booking, True

    def list(self, phone: str | None = None, date: str | None = None) -> list[Booking]:
        out = []
        for r in self._rows():
            if r["status"] != "confirmed":
                continue
            if phone and str(r["phone"]).strip() != phone.strip():
                continue
            if date and not str(r["start_time"]).startswith(date):
                continue
            out.append(Booking(**{k: r[k] for k in self.COLS}))
        return sorted(out, key=lambda b: b.start_time)


def get_store() -> Store:
    """Pick backend from env: STORE=sheets -> SheetsStore, else JSONStore."""
    if os.environ.get("STORE", "json").lower() == "sheets":
        return SheetsStore()
    return JSONStore(os.environ.get("BOOKINGS_PATH", "data/bookings.json"))
