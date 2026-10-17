"""
Mediakit — harnais de test.

Principe : exécuter les VRAIES actions, à travers l'API complète, avec de vrais
médias générés à la volée, et vérifier le fichier produit avec un outil
indépendant (ffprobe, identify). Les entrées sont fabriquées à partir des
SCHÉMAS Pydantic (même introspection que l'interface) : un test couvre donc
automatiquement toute nouvelle action ajoutée au catalogue.

Variables d'environnement requises par `main_api` (lues à l'import) : posées ici
par défaut, pour que l'application soit importable sans configuration.
"""

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

_PKG = Path(__file__).resolve().parent.parent
os.environ.setdefault("WB_MEDIAKIT_CONFIG_FILE", str(_PKG / "configs" / "config.toml"))
os.environ.setdefault("WB_MEDIAKIT_PORT", "8799")
os.environ.setdefault("WB_MEDIAKIT_AUTO_CHOOSE", "0")

from workbench.specs.pipeline_spec import PipelineSpec  # noqa: E402
from workbench.wb_utils.model_parser import model_to_dict  # noqa: E402

HOST = "127.0.0.1:8799"
WS_HEADERS = {"Host": HOST}   # le TestClient met « testserver » sur les WebSockets

# ─── Médias d'exemple ────────────────────────────────────────────────────────

MEDIA_KINDS = ("video", "audio", "image", "logo", "subtitles")


def _run(*cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, cwd=cwd, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])}… a échoué : {r.stderr.decode()[-300:]}")


def build_media(folder: Path) -> dict[str, tuple[str, bytes]]:
    """Génère un jeu de médias minuscules. Retourne {kind: (nom d'upload, contenu)}."""
    folder.mkdir(parents=True, exist_ok=True)
    _run("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=320x240:rate=15",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(folder / "video.mp4"))
    _run("ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=330:duration=3",
         "-ac", "2", "-ar", "44100", str(folder / "audio.wav"))
    _run("convert", "-size", "320x240", "gradient:blue-red", str(folder / "image.png"))
    _run("convert", "-size", "64x64", "xc:none", "-fill", "white", "-draw", "circle 32,32 32,8", str(folder / "logo.png"))
    (folder / "subs.srt").write_text("1\n00:00:00,500 --> 00:00:02,000\nBonjour\n\n2\n00:00:02,000 --> 00:00:02,900\nMonde\n", encoding="utf-8")
    names = {"video": "video.mp4", "audio": "audio.wav", "image": "image.png", "logo": "logo.png", "subtitles": "subs.srt"}
    return {k: (n, (folder / n).read_bytes()) for k, n in names.items()}


# Rôle du champ d'upload -> type de média attendu (le champ `input_file` dépend de l'outil).
FIELD_KIND = {
    "music_file": "audio", "new_audio_file": "audio", "audio_file": "audio",
    "watermark_image": "logo", "watermark_file": "logo", "watermark_logo": "logo",
    "image_file": "image", "cover_image": "image",
    "subtitles_file": "subtitles", "video_file": "video",
}


def spec_tool(spec) -> str:
    return "pipeline" if isinstance(spec, PipelineSpec) else spec.tool


def upload_fields(spec) -> dict:
    return {n: f for n, f in model_to_dict(spec.input_cls).items() if f["is_upload"]}


def candidate_kinds(spec) -> list[str]:
    """Types à essayer, dans l'ordre, pour le champ principal `input_file`."""
    tool = spec_tool(spec)
    return {"ffmpeg": ["video", "audio"], "sox": ["audio"], "magick": ["image"]}.get(tool, ["video", "image", "audio"])


def sample_value(f: dict):
    """Valeur valide pour un champ non-upload, d'après son schéma (None = omettre)."""
    if f["default"] is not None:
        return f["default"]
    if not f["required"]:
        return None
    t, c = f["type"], f.get("constraints") or {}
    if t == "enum":
        return f["choices"][0]
    if t == "boolean":
        return False
    if t in ("integer", "float"):
        low = c.get("ge", (c["gt"] + 1) if "gt" in c else 1)
        return int(low) if t == "integer" else float(low)
    return "Mediakit"


def build_request(spec, media: dict, main_kind: str, overrides: dict | None = None):
    """(user_input, uploads) pour `spec`, en utilisant `main_kind` pour le champ principal."""
    overrides = overrides or {}
    form = model_to_dict(spec.input_cls)
    user_input, uploads = {}, []
    for name, f in form.items():
        if f["is_upload"]:
            kind = FIELD_KIND.get(name, main_kind)
            fname, content = media[kind]
            stem, _, ext = fname.rpartition(".")
            if f["type"].startswith("list"):                     # ex. concat de vidéos
                names = [f"{name}-{i}.{ext}" for i in (1, 2)]
                user_input[name] = names
                uploads += [(n, content) for n in names]
            else:
                user_input[name] = f"{name}.{ext}"
                uploads.append((user_input[name], content))
        elif name in overrides:
            user_input[name] = overrides[name]
        else:
            value = sample_value(f)
            if value is not None:
                user_input[name] = value
    return user_input, uploads


# ─── Exécution ───────────────────────────────────────────────────────────────

@dataclass
class Job:
    job_id: str
    workdir: str
    output_files: list
    client: object
    messages: list = field(default_factory=list)

    @property
    def result(self) -> dict:
        return next((m["result"] for m in self.messages if m["type"] == "job_result"), {})

    @property
    def error(self):
        return next((m for m in self.messages if m["type"] == "job_error"), None)

    @property
    def ok(self) -> bool:
        return self.result.get("success") is True and self.error is None

    def final_file(self) -> str | None:
        for f in self.output_files:
            if f["last"]:
                return f["file"] or self.result.get(f["id"])
        return None

    def download(self, path: str | None = None) -> bytes:
        r = self.client.get("/api/download", params={"workdir": self.workdir, "path": path or self.final_file()})
        assert r.status_code == 200, f"download : {r.status_code} {r.text[:200]}"
        return r.content


class Api:
    def __init__(self, client):
        self.client = client

    def create(self, spec_id, user_input, uploads, timeout=90):
        files = [("files", (n, c, "application/octet-stream")) for n, c in uploads]
        return self.client.post("/api/job/create", data={
            "data": json.dumps({"id": spec_id, "user_input": user_input, "timeout": timeout})}, files=files or [])

    def run(self, spec_id, user_input, uploads, timeout=90) -> Job:
        r = self.create(spec_id, user_input, uploads, timeout)
        assert r.status_code == 200, f"création refusée : {r.status_code} {r.text[:300]}"
        body = r.json()
        assert body.get("job_id"), f"pas de job_id : {body}"
        job = Job(body["job_id"], body["workdir"], body["output_files"], self.client)
        deadline = time.time() + timeout + 15
        while time.time() < deadline:
            status = self.client.get("/api/job/status", params={"job_id": job.job_id}).json()["status"]
            if status != "running":
                break
            time.sleep(0.05)
        with self.client.websocket_connect(f"/api/job/ws/logs?job_id={job.job_id}", headers=WS_HEADERS) as ws:
            while True:
                msg = ws.receive_json()
                job.messages.append(msg)
                if msg["type"] == "job_end":
                    break
        return job


# ─── Vérification du fichier produit (par un outil indépendant) ──────────────

TEXT_EXTS = {"txt", "json", "srt", "vtt", "csv", "md"}


def verify_output(data: bytes, filename: str, tmp: Path) -> str | None:
    """None si le fichier est valide, sinon la raison."""
    if not data:
        return "fichier de sortie vide"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext in TEXT_EXTS:
        return None
    path = tmp / f"check.{ext}"
    path.write_bytes(data)
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, timeout=60)
    if r.returncode == 0:
        return None
    if shutil.which("identify"):
        i = subprocess.run(["identify", str(path)], capture_output=True, timeout=60)
        if i.returncode == 0:
            return None
    return f"illisible par ffprobe/identify : {r.stderr.decode()[:160]}"
