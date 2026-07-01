"""Offline test of SheetsStore logic using a fake in-memory gspread worksheet.

Proves the Sheets code path (header ensure, append, read-back, idempotency,
phone-as-text) without any Google credentials or network.
"""
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))


class FakeWorksheet:
    def __init__(self):
        self.rows = []  # list[list], row 0 = header once written

    def row_values(self, n):
        return self.rows[n - 1] if len(self.rows) >= n else []

    def update(self, values, range_name=None, value_input_option=None):
        # Only used to write the header at A1.
        if self.rows:
            self.rows[0] = values[0]
        else:
            self.rows.append(values[0])

    def append_row(self, row, value_input_option=None):
        assert value_input_option == "RAW"  # phones must not be parsed as formulas
        self.rows.append(row)

    def get_all_records(self, **kwargs):
        header = self.rows[0]
        return [dict(zip(header, r)) for r in self.rows[1:]]


@pytest.fixture()
def sheet_store(monkeypatch):
    ws = FakeWorksheet()
    fake_sheet = types.SimpleNamespace(sheet1=ws)
    fake_client = types.SimpleNamespace(open_by_key=lambda _id: fake_sheet)
    fake_gspread = types.ModuleType("gspread")
    fake_gspread.service_account = lambda filename: fake_client
    monkeypatch.setitem(sys.modules, "gspread", fake_gspread)
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "x.json")
    monkeypatch.setenv("SHEET_ID", "fake")
    for m in ("store", "schemas"):
        sys.modules.pop(m, None)
    from store import SheetsStore
    return SheetsStore(), ws


def _future(hour=20):
    return (datetime.now() + timedelta(days=1)).replace(
        hour=hour, minute=0, second=0, microsecond=0).isoformat(timespec="seconds")


def test_header_written(sheet_store):
    _, ws = sheet_store
    assert ws.rows[0] == ["id", "name", "phone", "party_size", "start_time",
                          "status", "notes", "created_at"]


def test_append_and_read(sheet_store):
    from schemas import BookRequest
    store, _ = sheet_store
    bk, created = store.add(
        BookRequest(name="A", phone="+919812345678", party_size=4,
                    start_time=_future()), created_at="now")
    assert created
    rows = store.list(phone="+919812345678")
    assert len(rows) == 1 and rows[0].id == bk.id


def test_idempotent_no_duplicate(sheet_store):
    from schemas import BookRequest
    store, ws = sheet_store
    req = BookRequest(name="A", phone="+919812345678", party_size=4,
                      start_time=_future())
    store.add(req, created_at="now")
    store.add(req, created_at="now")  # retry
    assert len(ws.rows) == 2  # header + exactly one booking
