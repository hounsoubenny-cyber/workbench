"""
Workbench — issue des jobs : un job qui PLANTE doit être signalé au client,
et le résultat d'un pipeline ne doit pas renvoyer les entrées saisies.

Premier point :

Avant le correctif, une exception levée pendant l'exécution (fichier requis
absent, étape de pipeline en échec, timeout...) sortait de `execute_entry`
sans rien envoyer : le statut restait « running », aucun `job_result` ni
`job_end` n'arrivait sur le WebSocket (l'interface attendait indéfiniment),
puis, une fois le job purgé, `/job/status` répondait « finished » comme si
tout s'était bien passé.

Lancer :  pytest workbench/api/test_job_failures.py
"""

import json
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from workbench.api.config import WbConfig
from workbench.api.create_routes import create_router
from workbench.core.orchestrator import MainEngine
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
from workbench.core.subprocess.wb_subprocess_types import BoolArg, PathArg
from workbench.specs.pipeline_spec import PipelineSpec, PipelineStepSpec
from workbench.specs.specs import ActionSpec
from workbench.wb_utils.job_buffer_manager import JobStatus
from workbench.wb_utils.job_file_cleaner import AsyncJobFileCleaner

LS_CONFIG = BinVersionCheckerConfig(cmd="--version", marker="coreutils", tool_name="ls")


class Empty(BaseModel):
    pass


# `must_exist=True` sur un fichier absent : l'exception est levée PENDANT
# l'exécution (pas à la création du job) — le cas qui plantait en silence.
broken_action = ActionSpec[Empty](
    id="broken_action", label="Action qui plante", tool="ls",
    binary_config=LS_CONFIG, input_cls=Empty,
    output_filename_template="out.txt",
    build_args=lambda u: [PathArg(value="absent.txt", must_exist=True)],
)

ok_action = ActionSpec[Empty](
    id="ok_action", label="Action qui marche", tool="ls",
    binary_config=LS_CONFIG, input_cls=Empty,
    output_filename_template="ls.txt", capture_stdout=True,
    build_args=lambda u: [BoolArg(flag="-a", value=True)],
)

broken_pipeline = PipelineSpec[Empty](
    id="broken_pipeline", label="Pipeline dont la 2e étape plante", input_cls=Empty,
    steps=[
        PipelineStepSpec[Empty](
            id="step_ok", action=ok_action,
            build_step_input=lambda p, o: Empty(), capture_stdout=True,
        ),
        PipelineStepSpec[Empty](
            id="step_boom", action=broken_action,
            build_step_input=lambda p, o: Empty(),
        ),
    ],
)

class SecretInput(BaseModel):
    password: str


secret_pipeline = PipelineSpec[SecretInput](
    id="secret_pipeline", label="Pipeline dont l'entrée contient un secret", input_cls=SecretInput,
    steps=[
        PipelineStepSpec[SecretInput](
            id="step_ls", action=ok_action,
            build_step_input=lambda p, o: Empty(), capture_stdout=True,
        ),
    ],
)

SPECS = {s.id: s for s in (broken_action, ok_action, broken_pipeline, secret_pipeline)}


def _build_app():
    config = WbConfig(max_concurrent_job=5, buffer_max_lines=200, buffer_clear_delay=30)
    orchestrator = MainEngine(config)
    cleaner = AsyncJobFileCleaner(default_ttl=60, every=5)
    router = create_router(
        orchestrator=orchestrator,
        show_specs_func=lambda: {},
        get_spec_func=SPECS.get,
        get_binary_config=lambda tool: LS_CONFIG,
        job_file_cleaner=cleaner,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        orchestrator.start()
        cleaner.start()
        yield
        await orchestrator.stop()
        await cleaner.stop()

    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    return app


def _create(client: TestClient, spec_id: str, user_input: dict | None = None) -> str:
    r = client.post(
        "/job/create",
        data={"data": json.dumps({"id": spec_id, "user_input": user_input or {}, "timeout": 20})},
        files=[],
    )
    assert r.status_code == 200, r.text
    return r.json()["job_id"]


def _wait_status(client: TestClient, job_id: str, wanted: str, seconds: float = 6.0) -> str:
    deadline = time.time() + seconds
    status = None
    while time.time() < deadline:
        status = client.get("/job/status", params={"job_id": job_id}).json()["status"]
        if status == wanted:
            return status
        time.sleep(0.1)
    return status


def _collect_ws(client: TestClient, job_id: str) -> list[dict]:
    messages = []
    with client.websocket_connect(f"/job/ws/logs?job_id={job_id}") as ws:
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg.get("type") == "job_end":
                return messages


def _assert_failure_reported(client: TestClient, job_id: str):
    assert _wait_status(client, job_id, JobStatus.FAILED.value) == JobStatus.FAILED.value, (
        "le statut doit passer à 'failed' quand l'exécution plante"
    )
    messages = _collect_ws(client, job_id)  # ne doit PAS bloquer : job_end attendu
    errors = [m for m in messages if m.get("type") == "job_error"]
    assert errors, f"aucun message job_error reçu : {messages}"
    assert errors[0]["error_code"] and errors[0]["message"]
    result = next(m for m in messages if m.get("type") == "job_result")
    assert result["result"]["success"] is False


def test_crashing_action_is_reported():
    with TestClient(_build_app()) as client:
        _assert_failure_reported(client, _create(client, "broken_action"))


def test_failing_pipeline_step_is_reported():
    with TestClient(_build_app()) as client:
        _assert_failure_reported(client, _create(client, "broken_pipeline"))


def test_healthy_job_still_finishes_normally():
    """Le correctif ne doit rien changer au chemin nominal."""
    with TestClient(_build_app()) as client:
        job_id = _create(client, "ok_action")
        assert _wait_status(client, job_id, JobStatus.FINISHED.value) == JobStatus.FINISHED.value
        messages = _collect_ws(client, job_id)
        assert not [m for m in messages if m.get("type") == "job_error"]
        result = next(m for m in messages if m.get("type") == "job_result")
        assert result["result"]["success"] is True


def test_pipeline_result_does_not_echo_user_inputs():
    """
    Les entrées saisies (mot de passe...) ne doivent JAMAIS repartir dans
    `job_result` (envoyé au client, stocké dans le buffer, rejoué à chaque
    reconnexion). Seules les sorties d'étapes sont renvoyées.
    """
    with TestClient(_build_app()) as client:
        job_id = _create(client, "secret_pipeline", {"password": "hunter2-S3CRET"})
        assert _wait_status(client, job_id, JobStatus.FINISHED.value) == JobStatus.FINISHED.value
        messages = _collect_ws(client, job_id)
        assert "hunter2-S3CRET" not in json.dumps(messages)
        result = next(m for m in messages if m.get("type") == "job_result")["result"]
        assert result["step_ls"] == "ls.txt"          # la sortie d'étape reste là
        assert result["success"] is True
