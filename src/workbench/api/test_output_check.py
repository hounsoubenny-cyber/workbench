"""
Workbench — un outil qui « réussit » sans produire son fichier doit être signalé.

Avant le correctif : job `finished` / `success: True` alors que le fichier de sortie
était absent ou vide ; dans un pipeline, l'étape suivante échouait avec un message
sans rapport (« snapshot.jpg n'est pas une image »).

Lancer :  pytest workbench/api/test_output_check.py
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from workbench.api.test_job_failures import (
    Empty, LS_CONFIG, _build_app, _collect_ws, _create, _wait_status,
)
from workbench.core.subprocess.output_check import (
    OutputEmptyError, OutputMissingError, verify_output,
)
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
from workbench.core.subprocess.wb_subprocess_types import PathArg
from workbench.specs.pipeline_spec import PipelineSpec, PipelineStepSpec
from workbench.specs.specs import ActionSpec
from workbench.wb_utils.job_buffer_manager import JobStatus

TOUCH_CONFIG = BinVersionCheckerConfig(cmd="--version", marker="coreutils", tool_name="touch")

# `ls -d .` réussit (code 0) mais n'écrit AUCUN fichier : l'outil « réussit » sans rien produire.
from workbench.core.subprocess.wb_subprocess_types import BoolArg  # noqa: E402

writes_nothing = ActionSpec[Empty](
    id="writes_nothing", label="Réussit sans rien écrire", tool="ls", binary_config=LS_CONFIG,
    input_cls=Empty, output_filename_template="never_written.bin",
    build_args=lambda u: [BoolArg(flag="-d", value=True)],
)
writes_empty_file = ActionSpec[Empty](
    id="writes_empty_file", label="Écrit un fichier vide", tool="touch", binary_config=TOUCH_CONFIG,
    input_cls=Empty, output_filename_template="empty.bin",
    build_args=lambda u: [PathArg(value="empty.bin")],
)
captured_empty_is_fine = ActionSpec[Empty](
    id="captured_empty_is_fine", label="Sortie texte vide mais légitime", tool="ls", binary_config=LS_CONFIG,
    input_cls=Empty, output_filename_template="listing.txt", capture_stdout=True,
    build_args=lambda u: [BoolArg(flag="-d", value=True)],
)

# Variante dont la sortie capturée est réellement vide : `ls -A` dans un dossier vide.
empty_listing = ActionSpec[Empty](
    id="empty_listing", label="Listing vide", tool="ls", binary_config=LS_CONFIG,
    input_cls=Empty, output_filename_template="listing.txt", capture_stdout=True,
    build_args=lambda u: [BoolArg(flag="-A", value=True), PathArg(value="emptydir", must_exist=False)],
)

pipeline_missing_output = PipelineSpec[Empty](
    id="pipeline_missing_output", label="Étape 1 sans sortie, étape 2 en dépend", input_cls=Empty,
    steps=[
        PipelineStepSpec[Empty](id="step_nothing", action=writes_nothing, build_step_input=lambda p, o: Empty()),
        PipelineStepSpec[Empty](id="step_empty", action=writes_empty_file, build_step_input=lambda p, o: Empty()),
    ],
)


@pytest.fixture
def client():
    from workbench.api import test_job_failures as base
    base.SPECS.update({s.id: s for s in (writes_nothing, writes_empty_file, captured_empty_is_fine,
                                         pipeline_missing_output)})
    with TestClient(_build_app()) as c:
        yield c


def test_verify_output_unit(tmp_path):
    (tmp_path / "ok.txt").write_text("x")
    (tmp_path / "empty.txt").write_text("")
    verify_output(tmp_path / "ok.txt", "ok.txt", allow_empty=False)
    verify_output(tmp_path / "empty.txt", "empty.txt", allow_empty=True)
    with pytest.raises(OutputMissingError):
        verify_output(tmp_path / "absent.txt", "absent.txt", allow_empty=True)
    with pytest.raises(OutputEmptyError):
        verify_output(tmp_path / "empty.txt", "empty.txt", allow_empty=False)


def _assert_reported(client, job_id, code):
    assert _wait_status(client, job_id, JobStatus.FAILED.value) == JobStatus.FAILED.value
    messages = _collect_ws(client, job_id)
    error = next(m for m in messages if m["type"] == "job_error")
    assert error["error_code"] == code, error
    assert next(m for m in messages if m["type"] == "job_result")["result"]["success"] is False
    return error


def test_action_that_writes_nothing_is_a_failure(client):
    error = _assert_reported(client, _create(client, "writes_nothing"), "OUTPUT_MISSING")
    assert "never_written.bin" in error["message"]


def test_action_that_writes_an_empty_file_is_a_failure(client):
    error = _assert_reported(client, _create(client, "writes_empty_file"), "OUTPUT_EMPTY")
    assert "empty.bin" in error["message"]


def test_pipeline_step_without_output_is_reported_on_the_right_step(client):
    error = _assert_reported(client, _create(client, "pipeline_missing_output"), "PIPELINE_STEP_FAILED")
    assert error["details"]["step_id"] == "step_nothing"
    assert error["details"]["cause"]["error_code"] == "OUTPUT_MISSING"


def test_captured_stdout_may_be_empty(client):
    """Une sortie TEXTE capturée vide est légitime (grep sans résultat) : pas de faux positif."""
    job_id = _create(client, "captured_empty_is_fine")
    assert _wait_status(client, job_id, JobStatus.FINISHED.value) == JobStatus.FINISHED.value
    result = next(m for m in _collect_ws(client, job_id) if m["type"] == "job_result")["result"]
    assert result["success"] is True
