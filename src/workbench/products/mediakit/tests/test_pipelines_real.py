"""
Mediakit — les 17 pipelines sont EXÉCUTÉS pour de vrai, avec leurs valeurs par défaut, puis les
régressions des bugs trouvés (valeurs par défaut invalides, étape sans sortie, texte accentué).
"""

import json

import pytest

from workbench.products.mediakit.specs.utils import PIPELINE_ALL_CAT
from workbench.products.mediakit.tests import harness as H
from workbench.products.mediakit.tests.conftest import need

MAIN_KIND = {"ffmpeg": "video", "magick": "image", "sox": "audio"}


def _main_kind(spec) -> str:
    return MAIN_KIND[spec.steps[0].action.tool]


def _tools(spec) -> list[str]:
    return sorted({s.action.tool for s in spec.steps})


PARAMS = [pytest.param(sid, marks=need(*_tools(PIPELINE_ALL_CAT[sid])), id=sid) for sid in sorted(PIPELINE_ALL_CAT)]


@pytest.mark.parametrize("spec_id", PARAMS)
def test_pipeline_runs_with_its_default_values(spec_id, api, media, tmp_path):
    spec = PIPELINE_ALL_CAT[spec_id]
    user_input, uploads = H.build_request(spec, media, _main_kind(spec))
    job = api.run(spec_id, user_input, uploads)
    assert job.ok, f"{spec_id} : {job.error or job.result}"
    name = job.final_file()
    assert name, "le pipeline doit déclarer un fichier final"
    assert H.verify_output(job.download(), name, tmp_path) is None


@need("magick")
@pytest.mark.parametrize("dimension", ["512", "800", "1024"])
def test_ecommerce_pipeline_accepts_every_dimension_it_offers(dimension, api, media, tmp_path):
    """Régression : « 800 » (le défaut !) était refusé par l'étape « miniature carrée »."""
    spec = PIPELINE_ALL_CAT["pipeline_ecommerce_product"]
    user_input, uploads = H.build_request(spec, media, "image", {"dimension": dimension})
    job = api.run("pipeline_ecommerce_product", user_input, uploads)
    assert job.ok, job.error or job.result
    assert H.verify_output(job.download(), job.final_file(), tmp_path) is None


@need("ffmpeg", "magick")
def test_teaser_pipeline_accepts_accented_text(api, media, tmp_path):
    spec = PIPELINE_ALL_CAT["pipeline_video_teaser_card"]
    user_input, uploads = H.build_request(spec, media, "video", {"teaser_text": "Épisode spécial été"})
    job = api.run("pipeline_video_teaser_card", user_input, uploads)
    assert job.ok, job.error or job.result


@need("ffmpeg", "magick")
@pytest.mark.parametrize("evil", ["%[fx:w]", "@/etc/passwd", "back\\slash", "a:b", ""])
def test_teaser_pipeline_refuses_dangerous_text_before_running_anything(evil, api, media):
    """Le texte est validé à l'entrée : refus 422 immédiat, aucune étape lancée."""
    spec = PIPELINE_ALL_CAT["pipeline_video_teaser_card"]
    user_input, uploads = H.build_request(spec, media, "video", {"teaser_text": evil})
    r = api.create("pipeline_video_teaser_card", user_input, uploads)
    assert r.status_code == 422, f"{evil!r} : {r.status_code}"


@need("ffmpeg", "magick")
def test_snapshot_beyond_the_end_of_the_video_is_reported_on_the_right_step(api, media):
    """
    Régression : ffmpeg « réussit » sans image quand on demande un instant après la fin de la
    vidéo ; l'étape suivante échouait avec « snapshot.jpg n'est pas une image ». Désormais l'étape
    fautive est nommée, avec un message clair.
    """
    spec = PIPELINE_ALL_CAT["pipeline_video_teaser_card"]
    user_input, uploads = H.build_request(spec, media, "video", {"snapshot_timestamp_s": 100.0})
    job = api.run("pipeline_video_teaser_card", user_input, uploads)
    assert not job.ok
    assert job.error["error_code"] == "PIPELINE_STEP_FAILED"
    assert job.error["details"]["step_id"] == spec.steps[0].id
    assert job.error["details"]["cause"]["error_code"] in ("OUTPUT_MISSING", "OUTPUT_EMPTY")


@need("ffmpeg")
def test_pipeline_result_never_echoes_user_input(api, media):
    spec = PIPELINE_ALL_CAT["pipeline_video_teaser_card"]
    user_input, uploads = H.build_request(spec, media, "video", {"teaser_text": "Secret42"})
    job = api.run("pipeline_video_teaser_card", user_input, uploads)
    assert "Secret42" not in json.dumps(job.messages)
