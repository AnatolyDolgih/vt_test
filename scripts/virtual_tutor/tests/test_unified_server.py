import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from unified_server import app


@pytest.fixture()
def client():
    return TestClient(app)


def test_root_serves_theme_selector(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "select_theme" in resp.text


def test_static_mounts(client):
    new_resp = client.get("/new/index.html")
    legacy_resp = client.get("/legacy/index.html")
    assert new_resp.status_code == 200
    assert legacy_resp.status_code == 200


def test_theme_roundtrip(client):
    client.post("/set_theme", json={"topic": "Physics"})
    assert client.get("/get_theme").json()["theme"] == "Physics"
    assert client.get("/get_theme_to_bica").json()["theme"] == "Physics"


def test_chat_storage(client):
    payload = {"role": "user", "text": "hello", "ts": 1}
    client.post("/chat/messages", json=payload)
    resp = client.get("/chat/messages")
    assert resp.status_code == 200
    assert payload in resp.json()


def test_essay_queue(client):
    submit_resp = client.post("/essay_data/", json={"text": "Essay text", "language": "ru"})
    assert submit_resp.status_code == 200
    fetch_resp = client.get("/get_data/")
    data = fetch_resp.json()
    assert data["status"] == "success"
    assert data["data"]["text"] == "Essay text"


def test_voice_processing_flag(client):
    assert client.get("/is_processing_done").json()["done"] is True
    with client.websocket_connect("/wss/web") as ws:
        ws.send_text("recording_started")
        assert client.get("/is_processing_done").json()["done"] is False
        ws.send_text("recording_finished")
    assert client.get("/is_processing_done").json()["done"] is True


def test_legacy_websocket_echo(client):
    with client.websocket_connect("/legacy/wss/demo") as ws:
        msg = {"type": "chat", "content": "Hi there", "timestamp": "1"}
        ws.send_text(json.dumps(msg))
        reply = ws.receive_json()
        assert reply["type"] == "chat"
        assert reply["content"].startswith("Tutor: Hi there")
