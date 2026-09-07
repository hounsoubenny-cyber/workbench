#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workbench — Test API "complet" avec TestClient (synchrone, in-process).

Contrairement a test_api_client.py (qui teste juste le routing avec une
FakeSpec qui ignore l'input), ce fichier utilise le VRAI catalogue
(workbench/examples/demo_catalog.py) : ls, grep, ffmpeg x2, + un pipeline
ls -> grep. Aucun mock : le TestClient de FastAPI/Starlette execute le vrai
ASGI app, qui execute vraiment les binaires (sous-process reels), qui
ecrivent vraiment des fichiers sur disque, telecharges via /download.

Lancer :  python3 -m workbench.api.test_api_client_full
       ou pytest workbench/api/test_api_client_full.py

Ce fichier teste le code APRES les fixes appliques (voir commentaires
"# FIX (bug #N)" dans orchestrator.py / create_routes.py /
job_buffer_manager.py). Le dernier test (test_pre_fix_bugs_repro) documente
ET reproduit ce qui se passait AVANT (utile pour comprendre l'impact reel).
"""

import gc
import json
import time
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig

from workbench.api.config import WbConfig
from workbench.core.orchestrator import MainEngine
from workbench.wb_utils.job_file_cleaner import AsyncJobFileCleaner
from workbench.api.create_routes import create_router
from workbench.wb_utils.job_buffer_manager import JobStatus
from workbench.examples.demo_catalog import get_spec, show_catalog


# ─── FIXTURES DE FICHIERS LOCAUX A UPLOADER ─────────────────────────────────

def _sample_text_file() -> str:
    p = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
    p.write("hello world\nfoo bar\nautre ligne\n")
    p.close()
    return p.name


def _sample_video_file(tag: str) -> str:
    """Petite vraie video mp4 (source lavfi), generee une fois, reutilisee comme upload."""
    out = tempfile.NamedTemporaryFile(suffix=f"_{tag}.mp4", delete=False)
    out.close()
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=64x64:rate=10",
         "-t", "1", out.name],
        check=True, capture_output=True,
    )
    return out.name


# ─── SETUP DE L'APPLICATION DE TEST (catalogue REEL) ────────────────────────

def build_app():
    config = WbConfig(max_concurrent_job=5, buffer_max_lines=500, buffer_clear_delay=5)
    orchestrator = MainEngine(config)
    cleaner = AsyncJobFileCleaner(default_ttl=120, every=5)
    
    def dummy_get_binary_config(tool_name: str) -> BinVersionCheckerConfig:
        if tool_name == "ffmpeg":
            return BinVersionCheckerConfig(cmd="-version", marker="ffmpeg", tool_name="ffmpeg")
        elif tool_name in ["ls", "cat", "grep"]:
            return BinVersionCheckerConfig(cmd="--version", marker="coreutils" if tool_name != "grep" else "grep", tool_name=tool_name)
        return BinVersionCheckerConfig(cmd="--version", marker=tool_name, tool_name=tool_name)


    router = create_router(
        orchestrator=orchestrator,
        show_specs_func=show_catalog,
        get_spec_func=get_spec,
        job_file_cleaner=cleaner,
        get_binary_config=dummy_get_binary_config
    )

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Code exécuté au DÉMARRAGE
        orchestrator.start()
        cleaner.start()
        yield
        await orchestrator.stop()
        await cleaner.stop()

    app = FastAPI(lifespan=lifespan)
    app.include_router(router)

    return app, orchestrator, cleaner


def create_job(client: TestClient, spec_id: str, user_input: dict, timeout: float | None = None,
                upload_paths: list[str] | None = None):
    """
    Helper : POST /job/create en multipart (voir create_routes.py — endpoint
    passe en multipart pour supporter l'upload de fichiers vers le workdir).
    `upload_paths` : chemins LOCAUX (sur le disque du test) des fichiers à
    uploader, DANS L'ORDRE attendu par les champs UploadRef de la spec.
    """
    payload = {"id": spec_id, "user_input": user_input, "timeout": timeout}
    files = []
    opened = []
    try:
        for p in (upload_paths or []):
            f = open(p, "rb")
            opened.append(f)
            files.append(("files", (Path(p).name, f, "application/octet-stream")))
        return client.post(
            "/job/create",
            data={"data": json.dumps(payload)},
            files=files,  # meme vide, force l'encodage multipart/form-data
        )
    finally:
        for f in opened:
            f.close()


def wait_job_finished(client: TestClient, job_id: str, timeout: float = 20.0):
    """Poll /job/status jusqu'a JobStatus.FINISHED (ou timeout)."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        r = client.get("/job/status", params={"job_id": job_id})
        last = r.json()
        if last.get("status") == JobStatus.FINISHED.value:
            return last
        time.sleep(0.2)
    raise TimeoutError(f"Job {job_id} pas termine apres {timeout}s (dernier statut: {last})")


# ─── TESTS ───────────────────────────────────────────────────────────────────

def test_config_get_and_post():
    app, orchestrator, cleaner = build_app()
    with TestClient(app) as client:
        r = client.get("/config")
        assert r.status_code == 200
        assert r.json()["max_concurrent_job"] == 5

        r = client.post("/config", json={"max_concurrent_job": 8})
        assert r.status_code == 200
        assert r.json()["success"] is True

        r = client.get("/config")
        assert r.json()["max_concurrent_job"] == 8
    print("✅ test_config_get_and_post")


def test_catalog_real():
    app, orchestrator, cleaner = build_app()
    with TestClient(app) as client:
        r = client.get("/catalog")
        assert r.status_code == 200
        data = r.json()
        for spec_id in ("list_directory", "filter_pattern", "generate_test_video",
                         "convert_to_gif", "ls_then_grep_pipeline"):
            assert spec_id in data, f"{spec_id} manquant du catalogue"
    print("✅ test_catalog_real — catalogue complet (ls, grep, ffmpeg x2, pipeline)")


def test_action_spec_ls_real_job():
    """Job simple (ActionSpec) : ls -la sur un vrai dossier, vrai fichier produit."""
    app, orchestrator, cleaner = build_app()
    with TestClient(app) as client:
        r = create_job(client, "list_directory", {"show_all": True, "long_format": True}, 15)
        assert r.status_code == 200, r.text
        data = r.json()
        job_id = data["job_id"]
        workdir = data["workdir"]
        assert data["is_action_spec"] is True
        assert data["output_files"] == [
            {"id": "list_directory", "last": True, "file": "ls_output.txt", "pos": 0}
        ]

        status = wait_job_finished(client, job_id)
        assert status["status"] == JobStatus.FINISHED.value

        # FIX (bug #18) : `ls` seul (hors pipeline) doit maintenant produire
        # reellement ls_output.txt (via capture_stdout sur l'ActionSpec),
        # pas juste le PROMETTRE dans output_files sans jamais l'ecrire.
        r = client.get("/download", params={"workdir": workdir, "path": "ls_output.txt"})
        assert r.status_code == 200, r.text
        assert b"total" in r.content

        # Reste a verifier : le WORKDIR lui-meme doit exister et etre le
        # meme dossier tout au long du job (verifie le fix #7).
        assert Path(workdir).exists(), (
            "Le workdir a disparu avant la fin du job — "
            "c'est exactement le bug #7 (TemporaryDirectory jamais garde en vie)."
        )
    print("✅ test_action_spec_ls_real_job")


def test_action_spec_ffmpeg_generate_and_download():
    """Job ffmpeg reel : genere une vraie video, la telecharge via /download."""
    app, orchestrator, cleaner = build_app()
    with TestClient(app) as client:
        r = create_job(client, "generate_test_video", {"duration_s": 1.0, "size": "64x64"}, 20)
        assert r.status_code == 200, r.text
        data = r.json()
        job_id, workdir = data["job_id"], data["workdir"]
        assert data["output_files"][0]["file"] == "generated.mp4"

        wait_job_finished(client, job_id)

        r = client.get("/download", params={"workdir": workdir, "path": "generated.mp4"})
        assert r.status_code == 200, r.text
        assert len(r.content) > 0
        assert r.content[4:8] == b"ftyp"  # signature mp4 (ftyp box)
    print("✅ test_action_spec_ffmpeg_generate_and_download — vraie vidéo mp4 générée + téléchargée")


def test_pipeline_ls_then_grep_real():
    """Pipeline reel: ls -> grep, deux outils differents chaines."""
    app, orchestrator, cleaner = build_app()
    with TestClient(app) as client:
        r = create_job(client, "ls_then_grep_pipeline", {"keyword": "total"}, 20)  # "total 0" est toujours dans un `ls -la`
        assert r.status_code == 200, r.text
        data = r.json()
        job_id, workdir = data["job_id"], data["workdir"]

        # FIX #2/#9/#17 verifie ici : avant les fix, output_files etait soit
        # vide (bug #2), soit indexe par le mauvais espace d'id (bug #17,
        # action_spec.id au lieu de step.id — qui est la cle utilisee par
        # Pipeline.run() dans son dict de sortie).
        ids = {f["id"] for f in data["output_files"]}
        assert ids == {"step_ls", "step_grep"}, data["output_files"]

        wait_job_finished(client, job_id)

        # Verifie que FIX #10 (correction post-execution des output_files)
        # fonctionne reellement main tenant que #17 (id namespace) est
        # corrige aussi.
        r2 = client.get("/job/status", params={"job_id": job_id})
        assert r2.status_code == 200

        r = client.get("/download", params={"workdir": workdir, "path": "filtered_output.txt"})
        assert r.status_code == 200, r.text
        assert b"total" in r.content, r.content
    print("✅ test_pipeline_ls_then_grep_real — pipeline 2 outils, output_files correct (fix #2/#9)")


def test_pipeline_output_files_resolved_after_run():
    """
    Verification directe (sans passer par l'API) que FIX #9/#10/#17
    fonctionnent ensemble : apres execution reelle du pipeline,
    entry.output_files contient les VRAIS noms de fichiers, correctement
    associes (meme espace d'id que le dict retourne par Pipeline.run()).
    """
    import asyncio
    import tempfile
    from workbench.core.orchestrator import MainEngine
    from workbench.examples.demo_catalog import pipeline_spec, PipelineFilterInput

    async def _run():
        with tempfile.TemporaryDirectory() as wd:
            orch = MainEngine(WbConfig(max_concurrent_job=5))
            orch.start()
            done = asyncio.Event()
            job_id = orch.job_id()
            info = orch.create_job(
                spec=pipeline_spec, job_id=job_id, workdir=wd,
                user_input=PipelineFilterInput(keyword="total"),
                done_callback=lambda t: done.set(), timeout=20,
            )
            await done.wait()
            entry = info["entry"]
            await entry.task
            await orch.stop()
            return entry.output_files

    output_files = asyncio.run(_run())
    by_id = {f["id"]: f["file"] for f in output_files}
    assert by_id == {"step_ls": "ls_output.txt", "step_grep": "filtered_output.txt"}, by_id
    print("✅ test_pipeline_output_files_resolved_after_run — fix #9/#10/#17 vérifiés")


def test_job_create_with_invalid_input_returns_422_not_500():
    """FIX #8 : un input invalide doit renvoyer une 422 propre, pas planter le serveur."""
    app, orchestrator, cleaner = build_app()
    with TestClient(app) as client:
        r = create_job(client, "filter_pattern", {"pattern": "x"}, 10)  # 'input_file' manquant -> ValidationError
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["error_code"] == "INVALID_INPUT_PARAMS"
    print("✅ test_job_create_with_invalid_input_returns_422_not_500")


def test_unknown_spec_returns_404():
    app, orchestrator, cleaner = build_app()
    with TestClient(app) as client:
        r = create_job(client, "does_not_exist", {})
        assert r.status_code == 404
    print("✅ test_unknown_spec_returns_404")


def test_websocket_logs_replay_and_end():
    """
    Ouvre le job puis se connecte APRES la fin. Le serveur fait un replay
    complet du buffer (run_log, job_result, job_end deja bufferises pendant
    l'execution) AVANT d'envoyer explicitement job_result+job_end une
    deuxieme fois (branche "job deja fini" de MainEngine.on_ws) — c'est
    donc bien un doublon inoffensif mais reel, a garder en tete.
    """
    app, orchestrator, cleaner = build_app()
    with TestClient(app) as client:
        r = create_job(client, "list_directory", {"show_all": True, "long_format": True}, 10)
        job_id = r.json()["job_id"]
        wait_job_finished(client, job_id)

        types_seen = []
        with client.websocket_connect(f"/job/ws/logs?job_id={job_id}") as ws:
            for _ in range(20):
                msg = ws.receive_json()
                types_seen.append(msg["type"])
                if msg["type"] == "replay_end":
                    break
        assert "replay_start" in types_seen
        assert "job_result" in types_seen
        assert "replay_end" in types_seen
    print("✅ test_websocket_logs_replay_and_end")


def test_upload_single_file():
    """
    `filter_pattern` seul (hors pipeline) n'a jamais rien a lire : chaque
    job a son PROPRE workdir, vide au depart. Le seul moyen de lui donner
    un fichier est de l'UPLOADER a la creation du job — via le champ
    UploadRef `input_file` de GrepInput (voir demo_catalog.py).
    """
    app, orchestrator, cleaner = build_app()
    local_txt = _sample_text_file()
    with TestClient(app) as client:
        r = create_job(
            client, "filter_pattern",
            {"pattern": "foo", "input_file": "notes.txt"},
            timeout=10, upload_paths=[local_txt],
        )
        assert r.status_code == 200, r.text
        data = r.json()
        job_id, workdir = data["job_id"], data["workdir"]

        # Le fichier uploade doit vraiment exister, RENOMME selon ce que
        # user_input a demande ("notes.txt"), pas selon le nom original du
        # fichier local.
        assert (Path(workdir) / "notes.txt").exists()

        wait_job_finished(client, job_id)
        r = client.get("/download", params={"workdir": workdir, "path": "filtered_output.txt"})
        assert r.status_code == 200, r.text
        assert b"foo bar" in r.content
    print("✅ test_upload_single_file — upload + renommage + grep dessus, bout en bout")


def test_upload_count_mismatch_returns_422():
    """Spec attend 1 fichier (UploadRef), client en envoie 0 -> 422 propre, pas un crash cote engine."""
    app, orchestrator, cleaner = build_app()
    with TestClient(app) as client:
        r = create_job(client, "filter_pattern", {"pattern": "foo", "input_file": "notes.txt"}, timeout=10)
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["error_code"] == "UPLOAD_COUNT_MISMATCH"
    print("✅ test_upload_count_mismatch_returns_422")


def test_upload_multiple_files_concat():
    """
    Demo MultiPathArg (mode REPEAT_FLAG, "-i f1 -i f2") + UploadRef sur une
    liste : concatene 2 videos uploadees, DANS L'ORDRE d'upload.
    """
    app, orchestrator, cleaner = build_app()
    clip_a = _sample_video_file("a")
    clip_b = _sample_video_file("b")
    with TestClient(app) as client:
        r = create_job(
            client, "concat_videos",
            {"inputs": ["clip_a.mp4", "clip_b.mp4"]},
            timeout=30, upload_paths=[clip_a, clip_b],
        )
        assert r.status_code == 200, r.text
        data = r.json()
        job_id, workdir = data["job_id"], data["workdir"]
        assert (Path(workdir) / "clip_a.mp4").exists()
        assert (Path(workdir) / "clip_b.mp4").exists()

        wait_job_finished(client, job_id, timeout=30)
        r = client.get("/download", params={"workdir": workdir, "path": "concatenated.mp4"})
        assert r.status_code == 200, r.text
        assert len(r.content) > 0
        assert r.content[4:8] == b"ftyp"  # signature mp4
    print("✅ test_upload_multiple_files_concat — MultiPathArg (repeat_flag) + UploadRef liste, bout en bout")


def test_pre_fix_bugs_repro():
    """
    Repro isolee de 2 bugs, sans passer par le serveur complet, pour montrer
    concretement leur effet AVANT correctif (documentation, pas une regression
    sur le code corrige ci-dessus).
    """
    import tempfile

    # --- bug #7 : TemporaryDirectory jamais garde -> supprime par le GC ---
    def create_workdir_BUGGY(job_id):
        return tempfile.TemporaryDirectory(prefix=job_id, ignore_cleanup_errors=True)

    workdir_obj = create_workdir_BUGGY("wb-job_demo")
    path_str = workdir_obj.name
    assert Path(path_str).exists()
    del workdir_obj          # <- c'est EXACTEMENT ce qui se passe quand la
    gc.collect()             #    coroutine de la route se termine : plus de ref.
    assert not Path(path_str).exists(), (
        "Le dossier existe encore : sur CPython le refcounting aurait du "
        "declencher le cleanup immediatement. (Ce test documente le bug, "
        "ce n'est pas un bug DANS notre code corrige.)"
    )
    print("✅ test_pre_fix_bugs_repro — bug #7 reproduit isolement (dossier supprime par le GC)")

    # --- bug #8 : dict brut vs modele Pydantic attendu ---
    from workbench.examples.demo_catalog import ls_action_spec
    raw_dict_input = {"show_all": True, "long_format": True}
    try:
        ls_action_spec.full_args(raw_dict_input)  # AttributeError attendu ici
        raise AssertionError("Le bug #8 aurait du lever une AttributeError")
    except AttributeError:
        pass
    print("✅ test_pre_fix_bugs_repro — bug #8 reproduit isolement (dict brut -> AttributeError)")

def test_advanced_create_custom_spec():
    """Test de la nouvelle route /job/advanced/create avec une spec générée à la volée (RawEntry)"""
    app, orchestrator, cleaner = build_app()
    
    # Création de deux fichiers locaux temporaires à uploader
    part1 = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
    part1.write("Hello ")
    part1.close()

    part2 = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w")
    part2.write("World!")
    part2.close()

    # Le payload brut (RawEntry) que le frontend enverrait
    raw_payload = {
        "tool": "cat",
        "args": [
            {
                "type": "multi_path",
                "flag": "",
                "values": ["part1.txt", "part2.txt"],
                "mode": "positional",
                "must_exist": True,
                "is_upload_file": True
            }
        ],
        "output_filename": "merged.txt",
        "timeout": 15,
        "check_version": False, # Optionnel : désactive le check version pour aller plus vite
        "capture_stdout": True  # Indispensable pour 'cat' qui écrit dans stdout
    }

    with TestClient(app) as client:
        # On prépare le multipart avec le JSON "data" et les fichiers
        files = [
            ("files", ("part1.txt", open(part1.name, "rb"), "text/plain")),
            ("files", ("part2.txt", open(part2.name, "rb"), "text/plain")),
        ]
        
        r = client.post(
            "/job/advanced/create",
            data={"data": json.dumps(raw_payload)},
            files=files
        )
        
        assert r.status_code == 200, f"Erreur API: {r.text}"
        data = r.json()
        job_id, workdir = data["job_id"], data["workdir"]
        
        # Vérification des marqueurs spécifiques à custom_spec
        assert data["is_custom_spec"] is True
        assert data["spec"]["type"] == "action"

        # On attend la fin de la concaténation
        wait_job_finished(client, job_id, timeout=10)

        # On télécharge le résultat (merged.txt)
        r = client.get("/download", params={"workdir": workdir, "path": "merged.txt"})
        assert r.status_code == 200, r.text
        
        # Le contenu doit être la fusion des deux fichiers !
        assert r.content == b"Hello World!"

    print("✅ test_advanced_create_custom_spec — CustomActionSpec généré à la volée, upload et exécution validés")
    
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🧪 WORKBENCH — SUITE DE TESTS API (TestClient, catalogue réel)")
    print("=" * 70)
    tests = [
        test_config_get_and_post,
        test_catalog_real,
        test_action_spec_ls_real_job,
        test_action_spec_ffmpeg_generate_and_download,
        test_pipeline_ls_then_grep_real,
        test_pipeline_output_files_resolved_after_run,
        test_job_create_with_invalid_input_returns_422_not_500,
        test_unknown_spec_returns_404,
        test_websocket_logs_replay_and_end,
        test_upload_single_file,
        test_upload_count_mismatch_returns_422,
        test_upload_multiple_files_concat,
        test_pre_fix_bugs_repro,
        test_advanced_create_custom_spec
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            failed += 1
            print(f"❌ {t.__name__} : {e!r}")
    print("=" * 70)
    if failed:
        print(f"❌ {failed}/{len(tests)} test(s) en échec")
        raise SystemExit(1)
    print(f"✅ {len(tests)}/{len(tests)} tests passés")