"""
Docukit — fixtures de test.

Les tests d'intégration lancent les VRAIS binaires (qpdf, poppler, tesseract,
pandoc) à travers l'application complète (TestClient) : aucun mock. Un test
dont le binaire est absent est SAUTÉ (pas en échec) via `need(...)`.
"""

import io
import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from workbench.products.docukit.api.app import create_app
from workbench.products.docukit.api.env import Settings

HOST = "127.0.0.1:8000"
WS_HEADERS = {"Host": HOST}   # le TestClient met « testserver » sur les WebSockets


def need(*binaries: str):
    """`pytestmark = need("qpdf")` : saute le module si un binaire manque."""
    missing = [b for b in binaries if shutil.which(b) is None]
    return pytest.mark.skipif(bool(missing), reason=f"binaire(s) absent(s) : {', '.join(missing)}")


# ─── PDF d'exemple ───────────────────────────────────────────────────────────

def make_pdf(name_label: str, pages: int, size=(595, 842)) -> bytes:
    """PDF de `pages` pages ; la page i contient « <label> PAGE i »."""
    reportlab = pytest.importorskip("reportlab")  # noqa: F841
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=size)
    for i in range(1, pages + 1):
        c.setFont("Helvetica", 28)
        c.drawString(72, size[1] - 120, f"{name_label} PAGE {i}")
        c.setFont("Helvetica", 14)
        c.drawString(72, size[1] - 160, "Bonjour le monde. Texte extractible.")
        c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture(scope="session")
def pdf3() -> bytes:
    return make_pdf("ALPHA", 3)


@pytest.fixture(scope="session")
def pdf2() -> bytes:
    return make_pdf("BRAVO", 2)


@pytest.fixture(scope="session")
def stamp_pdf() -> bytes:
    return make_pdf("CONFIDENTIEL", 1)


# ─── Outils d'inspection (hors application : on vérifie avec les binaires) ───

def run_tool(*cmd: str, stdin: bytes | None = None) -> str:
    result = subprocess.run(cmd, input=stdin, capture_output=True, timeout=60)
    return (result.stdout + result.stderr).decode("utf-8", "replace")


def page_count(pdf: bytes, tmp_path: Path) -> int:
    path = tmp_path / "inspect.pdf"
    path.write_bytes(pdf)
    return int(run_tool("qpdf", "--show-npages", str(path)).strip())


def pdf_text(pdf: bytes, tmp_path: Path) -> str:
    path = tmp_path / "inspect_text.pdf"
    path.write_bytes(pdf)
    return run_tool("pdftotext", str(path), "-")


# ─── Application & exécution de jobs ─────────────────────────────────────────

@dataclass
class Job:
    job_id: str
    workdir: str
    output_files: list
    messages: list = field(default_factory=list)
    client: TestClient | None = None

    @property
    def result(self) -> dict:
        return next(m for m in self.messages if m["type"] == "job_result")["result"]

    @property
    def error(self) -> dict | None:
        return next((m for m in self.messages if m["type"] == "job_error"), None)

    @property
    def ok(self) -> bool:
        return self.result.get("success") is True and self.error is None

    @property
    def final_file(self) -> str:
        return next(f["file"] for f in self.output_files if f["last"])

    def download(self, path: str | None = None) -> bytes:
        r = self.client.get("/api/download", params={
            "workdir": self.workdir, "path": path or self.result_file(),
        })
        assert r.status_code == 200, f"download {path!r} : {r.status_code} {r.text}"
        return r.content

    def result_file(self) -> str:
        """Nom du fichier final (résolu après exécution pour les pipelines)."""
        for f in self.output_files:
            if f["last"] and f["file"]:
                return f["file"]
        return next(v for k, v in self.result.items() if k.startswith("step_") and v)


class Api:
    def __init__(self, client: TestClient):
        self.client = client

    def create(self, spec_id: str, user_input: dict, uploads: list[tuple[str, bytes]] | None = None,
               timeout: float = 60):
        """POST /api/job/create. `uploads` : [(nom, contenu)] dans l'ordre des champs UploadRef."""
        files = [("files", (name, content, "application/octet-stream")) for name, content in (uploads or [])]
        return self.client.post(
            "/api/job/create",
            data={"data": json.dumps({"id": spec_id, "user_input": user_input, "timeout": timeout})},
            files=files or [],
        )

    def run(self, spec_id: str, user_input: dict, uploads=None, timeout: float = 60) -> Job:
        r = self.create(spec_id, user_input, uploads, timeout)
        assert r.status_code == 200, f"création refusée : {r.status_code} {r.text}"
        body = r.json()
        job = Job(body["job_id"], body["workdir"], body["output_files"], client=self.client)

        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.client.get("/api/job/status", params={"job_id": job.job_id}).json()["status"]
            if status != "running":
                break
            time.sleep(0.05)
        else:
            raise TimeoutError(f"job {spec_id} non terminé après {timeout}s")

        with self.client.websocket_connect(f"/api/job/ws/logs?job_id={job.job_id}", headers=WS_HEADERS) as ws:
            while True:
                msg = ws.receive_json()
                job.messages.append(msg)
                if msg["type"] == "job_end":
                    break
        return job


@pytest.fixture
def client(tmp_path):
    settings = Settings(config_path=tmp_path / "config.toml")
    with TestClient(create_app(settings), base_url=f"http://{HOST}") as c:
        yield c


@pytest.fixture
def api(client) -> Api:
    return Api(client)
