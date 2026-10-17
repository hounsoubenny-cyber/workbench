"""
Mediakit — API et sécurité : garde Host/Origin, traversée de chemin, mode manuel confiné,
écoute locale uniquement.
"""

import asyncio
import json

import pytest

from workbench.products.mediakit.tests import harness as H
from workbench.products.mediakit.tests.conftest import need


# ─── Contrat ─────────────────────────────────────────────────────────────────

def test_catalog_and_spec_info(client):
    catalog = client.get("/api/catalog")
    assert catalog.status_code == 200 and catalog.json()
    info = client.get("/api/spec/ffmpeg_crop_video/info").json()
    assert info["success"] and info["input"]["input_file"]["is_upload"] is True
    assert client.get("/api/spec/inexistante/info").json() == {"success": False}


@need("ffmpeg")
def test_binary_check_reports_installed_tools(client):
    assert client.get("/api/binary/ffmpeg/check").json() == {"find": True}


def test_binary_check_refuses_unknown_tools(client):
    """Seuls les outils du catalogue sont sondables : pas d'exécution de noms arbitraires."""
    r = client.get("/api/binary/rm/check")
    assert r.status_code >= 400 and r.json()["detail"]["error_code"] == "TOOL_MISSING"


# ─── Écoute locale uniquement ────────────────────────────────────────────────

def test_server_listens_on_loopback_only():
    from workbench.api.config import StartConfig
    from workbench.products.mediakit.api import main_api
    assert main_api.start_config.host == "127.0.0.1"
    assert StartConfig(server=None).host == "127.0.0.1"


# ─── Garde Host / Origin ─────────────────────────────────────────────────────

def test_cross_site_request_is_refused(client):
    r = client.post("/api/job/create", headers={"Origin": "https://evil.example"}, data={"data": "{}"}, files=[])
    assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN_ORIGIN"


def test_dns_rebinding_is_refused(client):
    assert client.get("/api/catalog", headers={"Host": "evil.example:8799"}).status_code == 403


def test_cross_site_websocket_is_refused(client):
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/job/ws/logs?job_id=x", headers={"Host": H.HOST, "Origin": "https://evil.example"}):
            pass


def test_the_apps_own_origin_is_accepted(client):
    assert client.get("/api/catalog", headers={"Origin": f"http://{H.HOST}"}).status_code == 200


# ─── Traversée de chemin sur le service du frontend ──────────────────────────

def _raw_get(path: str) -> tuple[int, bytes]:
    """GET en ASGI brut : le TestClient (httpx) normaliserait les « .. » avant l'envoi."""
    from workbench.products.mediakit.api.main_api import app
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET", "scheme": "http",
             "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
             "headers": [(b"host", H.HOST.encode())], "server": ("127.0.0.1", 8799), "client": ("127.0.0.1", 50000)}
    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    asyncio.run(app(scope, receive, send))
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    return status, b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")


@pytest.mark.parametrize("path", [
    "/../../api/env.py", "/../../../../../../../../etc/passwd", "//etc/passwd",
    "/assets/../../../api/env.py", "/..%2f..%2fapi/env.py", "/%2e%2e/%2e%2e/api/env.py",
])
def test_frontend_route_cannot_read_files_outside_dist(path):
    """Régression : `os.path.join(DIST_DIR, chemin)` laissait lire /etc/passwd et le code source."""
    status, body = _raw_get(path)
    assert b"root:x:0:0" not in body and b"Created on" not in body and b"StartAppError" not in body
    assert status in (200, 404)          # 200 = repli sur index.html (comportement SPA)


def test_frontend_still_serves_real_files_and_the_spa_fallback():
    status, body = _raw_get("/")
    assert status == 200 and b"<!doctype html>" in body.lower()
    status, body = _raw_get("/une/route/cote/client")
    assert status == 200 and b"<!doctype html>" in body.lower()


# ─── Confinement des fichiers ────────────────────────────────────────────────

def test_download_refuses_a_workdir_outside_the_temp_folder(client):
    r = client.get("/api/download", params={"workdir": "/etc", "path": "passwd"})
    assert r.status_code >= 400 and b"root:x:0:0" not in r.content


@need("sox")
def test_download_cannot_leave_the_job_folder(api, media, client):
    from workbench.products.mediakit.specs.utils import ACTION_ALL_CAT
    spec = ACTION_ALL_CAT["sox_reverse_audio"]
    ui, up = H.build_request(spec, media, "audio")
    job = api.run("sox_reverse_audio", ui, up)
    assert job.ok
    for escape in ("../../../../etc/passwd", "/etc/passwd", "..%2f..%2fetc%2fpasswd"):
        r = client.get("/api/download", params={"workdir": job.workdir, "path": escape})
        assert r.status_code >= 400 and b"root:x:0:0" not in r.content, escape


# ─── Mode manuel (activé dans Mediakit) : confiné au dossier de travail ──────

def _advanced(client, payload: dict):
    return client.post("/api/job/advanced/create", data={"data": json.dumps(payload)}, files=[])


def test_manual_mode_rejects_unknown_tools(client):
    r = _advanced(client, {"tool": "rm", "args": [], "output_filename": "out.txt"})
    assert r.status_code >= 400 or not r.json().get("job_id")


@need("ffmpeg")
def test_manual_mode_cannot_read_a_path_outside_the_workdir(api, client):
    """Même en mode manuel, un chemin hors du dossier de travail doit faire échouer le job."""
    payload = {"tool": "ffmpeg", "output_filename": "out.mp4", "check_version": False, "timeout": 20,
               "args": [{"flag": "-i", "type": "path", "value": "/etc/passwd", "must_exist": False},
                        {"flag": "", "type": "path", "value": "out.mp4"}]}
    r = _advanced(client, payload)
    if r.status_code != 200 or not r.json().get("job_id"):
        return                                           # refusé dès la création : parfait
    body = r.json()
    job = H.Job(body["job_id"], body["workdir"], body["output_files"], client)
    import time
    for _ in range(200):
        if client.get("/api/job/status", params={"job_id": job.job_id}).json()["status"] != "running":
            break
        time.sleep(0.05)
    with client.websocket_connect(f"/api/job/ws/logs?job_id={job.job_id}", headers=H.WS_HEADERS) as ws:
        while True:
            m = ws.receive_json()
            job.messages.append(m)
            if m["type"] == "job_end":
                break
    assert not job.ok, "un chemin hors du dossier de travail ne doit JAMAIS être lu"
