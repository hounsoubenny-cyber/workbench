"""Tests du garde Host/Origin pour serveurs locaux."""

import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from workbench.wb_utils.local_guard import LocalOnlyGuard


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    @app.post("/act")
    async def act():
        return {"done": True}

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        await socket.accept()
        await socket.send_json({"hello": 1})
        await socket.close()

    app.add_middleware(LocalOnlyGuard)
    return app


@pytest.fixture
def client():
    return TestClient(_app(), base_url="http://127.0.0.1:8000")


def test_local_clients_without_origin_are_accepted(client):
    assert client.get("/ping").status_code == 200
    assert client.post("/act").status_code == 200


@pytest.mark.parametrize("origin", [
    "http://127.0.0.1:8000", "http://localhost:3000", "http://[::1]:5173",
    "tauri://localhost", "http://tauri.localhost",
])
def test_local_origins_are_accepted(client, origin):
    assert client.post("/act", headers={"Origin": origin}).status_code == 200


@pytest.mark.parametrize("origin", [
    "https://evil.example", "http://localhost.evil.example", "null",
    "http://127.0.0.1.evil.example", "file://",
])
def test_cross_origin_requests_are_refused(client, origin):
    """CSRF : une page web quelconque ne doit pas pouvoir déclencher d'action."""
    r = client.post("/act", headers={"Origin": origin})
    assert r.status_code == 403
    assert r.json()["error_code"] == "FORBIDDEN_ORIGIN"


@pytest.mark.parametrize("host", ["evil.example", "evil.example:8000", "192.168.1.20:8000"])
def test_foreign_host_header_is_refused(host):
    """DNS rebinding : un nom de domaine re-résolu vers 127.0.0.1 est refusé."""
    c = TestClient(_app(), base_url="http://127.0.0.1:8000")
    assert c.get("/ping", headers={"Host": host}).status_code == 403


def test_websocket_origin_is_checked(client):
    # Le TestClient met `Host: testserver` sur les WebSockets : on le fixe.
    local = {"Host": "127.0.0.1:8000"}
    with client.websocket_connect("/ws", headers={**local, "Origin": "http://localhost:3000"}) as ws:
        assert ws.receive_json() == {"hello": 1}
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws", headers={**local, "Origin": "https://evil.example"}):
            pass
    with pytest.raises(WebSocketDisconnect):   # rebinding : mauvais Host
        with client.websocket_connect("/ws", headers={"Host": "evil.example"}):
            pass


def test_extra_hosts_can_be_allowed_explicitly():
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    app.add_middleware(LocalOnlyGuard, extra_hosts=["mon-pc.local"])
    c = TestClient(app, base_url="http://mon-pc.local:8000")
    assert c.get("/ping").status_code == 200
