"""Tests for the tool service. Uses a temp JSON store — no external creds."""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STORE", "json")
    monkeypatch.setenv("BOOKINGS_PATH", str(tmp_path / "b.json"))
    # Import app fresh so it binds the temp store.
    for m in ("app", "store", "tools", "schemas"):
        sys.modules.pop(m, None)
    from fastapi.testclient import TestClient
    import app as app_module
    return TestClient(app_module.app)


def _future(hour=20, days=1):
    d = (datetime.now() + timedelta(days=days)).replace(
        hour=hour, minute=0, second=0, microsecond=0)
    return d.isoformat(timespec="seconds")


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["ok"]


def test_book_success(client):
    r = client.post("/tools/book_appointment", json={
        "name": "Amarsh", "phone": "+919000000000",
        "party_size": 4, "start_time": _future()})
    body = r.json()
    assert body["ok"] and body["data"]["id"].startswith("bk_")


def test_book_idempotent(client):
    payload = {"name": "Amarsh", "phone": "+919000000000",
               "party_size": 4, "start_time": _future()}
    a = client.post("/tools/book_appointment", json=payload).json()
    b = client.post("/tools/book_appointment", json=payload).json()
    assert a["data"]["id"] == b["data"]["id"]        # same reservation
    assert "already" in b["message"].lower()


def test_book_rejects_past(client):
    r = client.post("/tools/book_appointment", json={
        "name": "X", "phone": "+91900", "party_size": 2,
        "start_time": _future(days=-1)}).json()
    assert not r["ok"] and "past" in r["message"].lower()


def test_book_rejects_big_party(client):
    r = client.post("/tools/book_appointment", json={
        "name": "X", "phone": "+91900", "party_size": 50,
        "start_time": _future()}).json()
    assert not r["ok"]


def test_book_rejects_closed_hours(client):
    r = client.post("/tools/book_appointment", json={
        "name": "X", "phone": "+91900", "party_size": 2,
        "start_time": _future(hour=3)}).json()
    assert not r["ok"] and "hours" in r["message"].lower()


def test_list_filters_by_phone(client):
    client.post("/tools/book_appointment", json={
        "name": "A", "phone": "+919111111111", "party_size": 2, "start_time": _future()})
    client.post("/tools/book_appointment", json={
        "name": "B", "phone": "+919122222222", "party_size": 2, "start_time": _future(hour=21)})
    r = client.post("/tools/list_bookings", json={"phone": "+919111111111"}).json()
    assert r["ok"] and len(r["data"]) == 1 and r["data"][0]["name"] == "A"


def test_transfer_returns_number(client):
    r = client.post("/tools/transfer_call", json={"reason": "wants manager"}).json()
    assert r["ok"] and "transfer_to" in r["data"]


def test_dispatch_shape(client):
    r = client.post("/tools/dispatch", json={
        "name": "book_appointment",
        "arguments": {"name": "Z", "phone": "+919199999999", "party_size": 3,
                      "start_time": _future()}}).json()
    assert r["ok"] and r["data"]["party_size"] == 3
