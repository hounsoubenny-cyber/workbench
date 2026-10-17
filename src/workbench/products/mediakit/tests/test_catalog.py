"""
Mediakit — cohérence du catalogue (aucun binaire requis).

Ces tests parcourent les 100 specs d'un coup : toute nouvelle action ajoutée au catalogue
est couverte automatiquement.
"""

import json
from itertools import product

import pytest
from pydantic import ValidationError

from workbench.products.mediakit.specs.utils import (
    ACTION_ALL_CAT, ALL_CAT, BINARY_CONFS, PIPELINE_ALL_CAT, get_binary_config, get_catalog, get_spec,
)
from workbench.products.mediakit.tests import harness as H
from workbench.specs.pipeline_spec import PipelineSpec
from workbench.wb_utils.model_parser import model_to_dict

ACTIONS = sorted(ACTION_ALL_CAT)
PIPELINES = sorted(PIPELINE_ALL_CAT)

# Médias factices : seuls les NOMS comptent ici (aucun fichier n'est lu).
DUMMY = {k: (n, b"") for k, n in {"video": "v.mp4", "audio": "a.wav", "image": "i.png",
                                  "logo": "l.png", "subtitles": "s.srt"}.items()}


def _inputs(spec, overrides=None):
    kind = H.candidate_kinds(spec)[0]
    user_input, _ = H.build_request(spec, DUMMY, kind, overrides)
    return spec.input_cls.model_validate(user_input)


def test_catalog_shape_and_registry():
    assert len(ALL_CAT) == len(ACTION_ALL_CAT) + len(PIPELINE_ALL_CAT) > 90
    assert set(BINARY_CONFS) == {"ffmpeg", "sox", "magick"}
    catalog = json.loads(json.dumps(get_catalog()))          # sérialisable en JSON
    assert catalog
    assert get_spec("ffmpeg_crop_video") is ACTION_ALL_CAT["ffmpeg_crop_video"]
    assert get_binary_config("sox") is BINARY_CONFS["sox"]
    with pytest.raises(KeyError):
        get_binary_config("rm")


@pytest.mark.parametrize("spec_id", ACTIONS)
def test_every_action_builds_a_valid_command(spec_id):
    spec = ACTION_ALL_CAT[spec_id]
    assert spec.tool in BINARY_CONFS and spec.label.strip()
    form = model_to_dict(spec.input_cls)
    assert form and any(f["is_upload"] for f in form.values()), "une action sans fichier source ?"
    args = spec.full_args(_inputs(spec))
    assert args, "aucun argument construit"
    out = spec.output_filename_template
    out = out(_inputs(spec)) if callable(out) else out
    assert isinstance(out, str) and out and "/" not in out and not out.startswith("-")


@pytest.mark.parametrize("spec_id", ACTIONS)
def test_security_arguments_are_always_included(spec_id):
    """full_args() doit inclure les arguments de sécurité de l'outil (limites mémoire/temps, etc.)."""
    spec = ACTION_ALL_CAT[spec_id]
    inputs = _inputs(spec)
    assert len(spec.full_args(inputs)) >= len(spec.build_args(inputs))
    if spec.tool == "magick":
        flags = [getattr(a, "flag", None) for a in spec.full_args(inputs)]
        assert "-limit" in flags, "ImageMagick doit toujours tourner avec des limites de ressources"


def _outputs_after(spec, step_inputs_so_far):
    return {"_previous": step_inputs_so_far[-1] if step_inputs_so_far else None}


def pipeline_variants(spec):
    """Valeurs par défaut, puis CHAQUE choix de chaque champ énuméré, puis les bornes numériques."""
    form = {n: f for n, f in model_to_dict(spec.input_cls).items() if not f["is_upload"]}
    yield "défauts", {}
    for name, f in form.items():
        if f["type"] == "enum":
            for choice in f["choices"]:
                yield f"{name}={choice}", {name: choice}
        elif f["type"] in ("integer", "float"):
            c = f.get("constraints") or {}
            cast = int if f["type"] == "integer" else float
            for key in ("ge", "le"):
                if key in c:
                    yield f"{name}={c[key]}", {name: cast(c[key])}


@pytest.mark.parametrize("spec_id", PIPELINES)
def test_pipeline_every_choice_produces_valid_step_inputs(spec_id):
    """
    Propriété : pour TOUTE valeur que l'interface autorise sur un pipeline, chaque étape doit
    pouvoir construire son entrée. Sinon le pipeline échoue À L'EXÉCUTION, après avoir déjà
    lancé les premières étapes (cas réels trouvés : dimension « 800 » refusée par l'étape
    « miniature carrée », texte « NOUVEL ÉPISODE » refusé par le filigrane).
    """
    spec = PIPELINE_ALL_CAT[spec_id]
    problems = []
    for label, overrides in pipeline_variants(spec):
        user_input, _ = H.build_request(spec, DUMMY, H.candidate_kinds(spec)[0], overrides)
        try:
            pipeline_in = spec.input_cls.model_validate(user_input)
        except ValidationError as exc:
            problems.append(f"[{label}] entrée du pipeline refusée : {exc.errors()[0]['msg']}")
            continue
        outputs: dict = dict(user_input)
        for step in spec.steps:
            try:
                step_in = step.build_step_input(pipeline_in, outputs)
                spec_out = step.action.output_filename_template
                filename = spec_out(step_in) if callable(spec_out) else spec_out
                step.action.full_args(step_in)
            except Exception as exc:                       # noqa: BLE001
                problems.append(f"[{label}] étape {step.id} : {type(exc).__name__}: {str(exc)[:150]}")
                break
            outputs[step.id] = outputs["_previous"] = filename
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("spec_id", PIPELINES)
def test_pipeline_steps_reference_catalog_actions(spec_id):
    spec = PIPELINE_ALL_CAT[spec_id]
    assert isinstance(spec, PipelineSpec) and len(spec.steps) >= 2
    ids = [s.id for s in spec.steps]
    assert len(ids) == len(set(ids)), "ids d'étapes en double"
    for step in spec.steps:
        assert step.action.tool in BINARY_CONFS


def test_ffmpeg_descriptions_do_not_promise_audio_input():
    """
    Les actions ffmpeg à un fichier rejettent tout ce qui n'est pas une VIDÉO (FfmpegSpec.validate_args).
    La description du champ ne doit donc pas promettre « vidéo ou audio » (bug trouvé : elle le faisait).
    """
    for spec_id in ACTIONS:
        spec = ACTION_ALL_CAT[spec_id]
        if spec.tool == "ffmpeg" and spec.validate_arg:
            field = model_to_dict(spec.input_cls).get("input_file")
            if field:
                assert "audio" not in (field["description"] or "").lower(), spec_id
