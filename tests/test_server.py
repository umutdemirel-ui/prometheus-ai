"""Integration tests for FastAPI server & WebSocket HUD endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from prometheus.server import app


client = TestClient(app)


def test_health_and_state():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["name"] == "Prometheus"
    assert "mode" in r.json()

    s = client.get("/api/state")
    assert s.status_code == 200
    body = s.json()
    assert "telemetry" in body
    assert "config" in body


def test_pwa_and_vercel_entrypoint():
    from api.index import app as vercel_app
    from prometheus.desktop import _find_free_port

    assert vercel_app is app
    assert _find_free_port() > 0

    m = client.get("/manifest.json")
    assert m.status_code == 200
    assert m.json()["short_name"] == "Prometheus AI"

    sw = client.get("/sw.js")
    assert sw.status_code == 200

    ic = client.get("/static/icon-192.png")
    assert ic.status_code == 200


def test_command_endpoint_and_wake_word():
    r_ignored = client.post(
        "/api/command",
        json={"text": "merhaba dünya", "check_wake_word": True},
    )
    assert r_ignored.status_code == 200
    assert r_ignored.json()["ignored"] is True

    r_ok = client.post(
        "/api/command",
        json={"text": "Prometheus 12 artı 8 kaç", "check_wake_word": True},
    )
    assert r_ok.status_code == 200
    data = r_ok.json()
    assert data["ignored"] is False
    assert data["intent"] == "calculate"
    assert data["data"]["result"] == 20


def test_custom_crud_and_websocket():
    add_res = client.post(
        "/api/custom/site",
        json={"name": "testpanel", "target": "https://example.org"},
    )
    assert add_res.status_code == 200
    assert add_res.json()["custom_sites"]["testpanel"] == "https://example.org"

    del_res = client.delete("/api/custom/site/testpanel")
    assert del_res.status_code == 200
    assert "testpanel" not in del_res.json()["custom_sites"]

    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "command", "text": "saat kaç"})
        msg = ws.receive_json()
        # First frame might be telemetry; read until command_result
        for _ in range(4):
            if msg.get("type") == "command_result":
                break
            msg = ws.receive_json()
        assert msg["type"] == "command_result"
        assert msg["intent"] == "time"
