"""
Docukit — tests de l'API : défenses en profondeur (Host/Origin, taille, en-têtes,
mode manuel coupé) et contrat consommé par l'interface.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from workbench.products.docukit.api.app import create_app
from workbench.products.docukit.api.env import Settings
from workbench.products.docukit.api.limits import MaxBodySizeMiddleware
from workbench.products.docukit.tests.conftest import HOST, need


# ─── Contrat de l'API ────────────────────────────────────────────────────────

def test_status_catalog_and_tools(client):
    assert client.get("/api/status").json()["product"] == "Docukit"
    catalog = client.get("/api/catalog").json()
    assert catalog["product"]["id"] == "docukit" and len(catalog["specs"]) == 21
    tools = client.get("/api/tools").json()
    assert set(tools) == {"qpdf", "pdfinfo", "pdftotext", "pdftoppm", "pdfimages", "tesseract", "pandoc"}
    assert all("find" in t and t["install"] for t in tools.values())


def test_unknown_tool_is_404(client):
    assert client.get("/api/binary/rm/check").status_code == 404
    assert client.get("/api/binary/../etc/passwd/check").status_code == 404


@need("qpdf")
def test_single_tool_check_reports_version(client):
    body = client.get("/api/binary/qpdf/check").json()
    assert body["find"] is True and body["version"][0].isdigit()


def test_spec_info_exposes_the_form(client):
    info = client.get("/api/spec/qpdf_rotate/info").json()
    assert info["success"] and info["input"]["angle"]["choices"] == ["90", "180", "270"]
    assert info["input"]["input_file"]["is_upload"] is True


# ─── Défense : Host / Origin ─────────────────────────────────────────────────

def test_cross_site_post_cannot_create_a_job(client, pdf3):
    """CSRF : une page web quelconque ne doit pas pouvoir lancer de job."""
    r = client.post(
        "/api/job/create", headers={"Origin": "https://evil.example"},
        data={"data": '{"id": "qpdf_check", "user_input": {"input_file": "a.pdf"}}'},
        files=[("files", ("a.pdf", pdf3, "application/pdf"))],
    )
    assert r.status_code == 403 and r.json()["error_code"] == "FORBIDDEN_ORIGIN"


def test_dns_rebinding_is_refused(client):
    assert client.get("/api/catalog", headers={"Host": "evil.example:8000"}).status_code == 403


def test_the_apps_own_origin_is_accepted(client):
    assert client.get("/api/catalog", headers={"Origin": f"http://{HOST}"}).status_code == 200


def test_foreign_host_is_accepted_only_when_declared(tmp_path):
    settings = Settings(config_path=tmp_path / "c.toml", allowed_hosts=("mon-pc.local",))
    with TestClient(create_app(settings), base_url="http://mon-pc.local:8000") as c:
        assert c.get("/api/status").status_code == 200


# ─── Défense : mode manuel, docs, en-têtes ───────────────────────────────────

def test_manual_mode_is_disabled(client):
    """Le client ne choisit jamais les drapeaux passés aux binaires."""
    r = client.post("/api/job/advanced/create", data={"data": "{}"}, files=[])
    assert r.status_code == 404 and r.json()["detail"]["error_code"] == "ADVANCED_JOBS_DISABLED"


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_no_public_api_docs(client, path):
    assert client.get(path).status_code == 404


def test_security_headers_on_every_response(client):
    for path in ("/api/status", "/api/catalog", "/nexiste-pas"):
        h = client.get(path).headers
        assert "default-src 'self'" in h["content-security-policy"] and "frame-ancestors 'none'" in h["content-security-policy"]
        assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
        assert "script-src 'self'" in h["content-security-policy"] and "unsafe-inline" not in h["content-security-policy"]


# ─── Défense : taille des uploads ────────────────────────────────────────────

def test_oversized_upload_is_refused_with_413(tmp_path):
    settings = Settings(config_path=tmp_path / "c.toml", max_upload_mb=1)
    with TestClient(create_app(settings), base_url=f"http://{HOST}") as c:
        r = c.post(
            "/api/job/create", data={"data": '{"id": "qpdf_check", "user_input": {"input_file": "a.pdf"}}'},
            files=[("files", ("a.pdf", b"%PDF-" + b"0" * (2 * 1024 * 1024), "application/pdf"))],
        )
        assert r.status_code == 413 and r.json()["error_code"] == "REQUEST_TOO_LARGE"
        assert c.get("/api/status").status_code == 200, "le serveur reste utilisable"


def test_streamed_body_without_content_length_is_still_limited():
    """Un client peut omettre/falsifier Content-Length : on compte les octets réellement reçus."""
    seen = {}

    async def downstream(scope, receive, send):
        while (await receive()).get("more_body"):
            pass
        seen["reached_end"] = True

    chunks = [{"type": "http.request", "body": b"x" * 600, "more_body": True} for _ in range(3)]
    sent = []

    async def receive():
        return chunks.pop(0) if chunks else {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    app = MaxBodySizeMiddleware(downstream, max_bytes=1000)
    asyncio.run(app({"type": "http", "headers": []}, receive, send))
    assert sent[0]["status"] == 413 and "reached_end" not in seen


# ─── Fichiers statiques : pas de traversée de chemin ─────────────────────────

def test_static_route_cannot_escape_the_frontend_folder(tmp_path):
    front = tmp_path / "front"
    front.mkdir()
    (front / "index.html").write_text("<html>Docukit</html>")
    (front / "app.js").write_text("ok")
    (tmp_path / "secret.txt").write_text("TOP-SECRET")
    settings = Settings(config_path=tmp_path / "c.toml")
    with TestClient(create_app(settings, frontend_dir=front), base_url=f"http://{HOST}") as c:
        assert c.get("/").status_code == 200 and c.get("/static/app.js").text == "ok"
        for attack in ("/static/../secret.txt", "/static/%2e%2e/secret.txt", "/static/..%2fsecret.txt",
                       "/static//etc/passwd", "/../secret.txt"):
            r = c.get(attack)
            assert "TOP-SECRET" not in r.text and "root:" not in r.text, attack


# ─── Interface servie par l'application ──────────────────────────────────────

def test_the_real_frontend_is_served(client):
    page = client.get("/")
    assert page.status_code == 200 and "Docukit" in page.text
    assert "script-src 'self'" in page.headers["content-security-policy"]
    assert "<script>" not in page.text and " onclick=" not in page.text and "style=" not in page.text, \
        "la CSP interdit le code et les styles inline"
    js, css = client.get("/static/app.js"), client.get("/static/style.css")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    assert css.status_code == 200 and "text/css" in css.headers["content-type"]
    import re
    code = re.sub(r"/\*.*?\*/", "", js.text, flags=re.S)             # sans commentaires
    code = re.sub(r"^\s*//.*$", "", code, flags=re.M)
    assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(", code)
