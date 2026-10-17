"""
Mediakit — chaque action est EXÉCUTÉE pour de vrai (ffmpeg, sox, ImageMagick) sur de vrais médias,
à travers l'API complète. Pour chaque action : le job réussit, le fichier produit existe, n'est pas
vide et est lisible par un outil indépendant (ffprobe / identify). Pour les actions listées dans
`SEMANTIC`, on vérifie en plus que le résultat FAIT ce qu'annonce son nom.
"""

import pytest

from workbench.products.mediakit.specs.utils import ACTION_ALL_CAT
from workbench.products.mediakit.tests import harness as H
from workbench.products.mediakit.tests.conftest import need

# Valeurs adaptées aux petits médias d'exemple (320x240, 12 s) quand le défaut ne conviendrait pas.
OVERRIDES = {
    "ffmpeg_crop_video": {"width": 160, "height": 120},
}
MAIN_KIND = {"ffmpeg_extract_subtitles": "video_subs"}


def _ext(name: str) -> str:
    return name.rsplit(".", 1)[-1]


def _check_resize(info, ui):
    w, h = ui["resolution"].split("x")
    stream = H.video_stream(info)
    assert (stream["width"], stream["height"]) == (int(w), int(h))

def _check_speed(info, ui):
    assert H.duration(info) == pytest.approx(12 / float(ui["speed_factor"]), abs=0.8)

def _check_trim(info, ui):
    assert H.duration(info) == pytest.approx(min(ui["duration_seconds"], 12 - ui["start_seconds"]), abs=0.8)

def _check_mute(info, ui):
    assert not [s for s in info["streams"] if s["codec_type"] == "audio"]

def _check_audio_only(info, ui):
    assert [s["codec_type"] for s in info["streams"]] == ["audio"]

def _check_gif(info, ui):
    assert info["format"]["format_name"] == "gif" and H.duration(info) <= ui["duration_s"] + 0.8

def _check_rotate_cw(info, ui):
    stream = H.video_stream(info)
    assert (stream["width"], stream["height"]) == (240, 320)

def _check_fps(info, ui):
    num, den = H.video_stream(info)["avg_frame_rate"].split("/")
    assert int(num) / int(den) == pytest.approx(int(ui["fps"]), abs=0.6)

def _check_crop(info, ui):
    stream = H.video_stream(info)
    assert (stream["width"], stream["height"]) == (ui["width"], ui["height"])

def _check_magick_resize(info, ui):
    assert H.video_stream(info)["width"] == 80          # 25 % de 320

def _check_gray(info, ui):
    assert H.video_stream(info)["pix_fmt"].startswith(("gray", "ya"))

def _check_magick_crop(info, ui):
    stream = H.video_stream(info)
    assert (stream["width"], stream["height"]) == (min(ui["width"], 320), min(ui["height"], 240))

def _check_magick_rotate(info, ui):
    stream = H.video_stream(info)
    assert (stream["width"], stream["height"]) == (240, 320)

def _check_sox_trim(info, ui):
    assert H.duration(info) == pytest.approx(min(ui["duration_seconds"], 3 - ui["start_seconds"]), abs=0.3)

def _check_sox_flac(info, ui):
    assert info["streams"][0]["codec_name"] == "flac"


# spec_id -> (surcharges d'entrée, vérification du résultat)
SEMANTIC = {
    "ffmpeg_resize_video": ({}, _check_resize),
    "ffmpeg_speed_video": ({"speed_factor": "2.0"}, _check_speed),
    "ffmpeg_trim_no_copy": ({"start_seconds": 2.0, "duration_seconds": 5.0}, _check_trim),
    "ffmpeg_mute_video": ({}, _check_mute),
    "ffmpeg_extract_audio_convert": ({"output_format": "wav"}, _check_audio_only),
    "ffmpeg_video_to_gif": ({}, _check_gif),
    "ffmpeg_rotate_video": ({"rotation": "90_cw"}, _check_rotate_cw),
    "ffmpeg_change_fps": ({"fps": 24}, _check_fps),
    "ffmpeg_crop_video": ({}, _check_crop),
    "magick_resize_image": ({"size": "25%"}, _check_magick_resize),
    "magick_grayscale": ({}, _check_gray),
    "magick_crop_image": ({"width": 100, "height": 100}, _check_magick_crop),
    "magick_rotate_image": ({"degrees": "90"}, _check_magick_rotate),
    "sox_trim_audio": ({"start_seconds": 1.0, "duration_seconds": 2.0}, _check_sox_trim),
    "sox_convert_format": ({"output_format": "flac"}, _check_sox_flac),
}

PARAMS = [pytest.param(sid, marks=need(ACTION_ALL_CAT[sid].tool), id=sid) for sid in sorted(ACTION_ALL_CAT)]


@pytest.mark.parametrize("spec_id", PARAMS)
def test_action_runs_and_produces_a_valid_file(spec_id, api, media, tmp_path):
    spec = ACTION_ALL_CAT[spec_id]
    overrides = {**OVERRIDES.get(spec_id, {}), **SEMANTIC.get(spec_id, ({}, None))[0]}
    user_input, uploads = H.build_request(spec, media, MAIN_KIND.get(spec_id, H.candidate_kinds(spec)[0]), overrides)

    job = api.run(spec_id, user_input, uploads)
    assert job.ok, f"{spec_id} a échoué : {job.error or job.result.get('stderr', '')[-300:]}"

    name = job.final_file()
    data = job.download()
    assert H.verify_output(data, name, tmp_path) is None, f"{name} : {H.verify_output(data, name, tmp_path)}"

    check = SEMANTIC.get(spec_id, ({}, None))[1]
    if check:
        check(H.probe(data, tmp_path, _ext(name)), user_input)


# ─── Cas d'échec : le message doit être clair, le job ne doit jamais rester bloqué ───

@need("ffmpeg")
def test_crop_larger_than_the_video_fails_cleanly(api, media):
    spec = ACTION_ALL_CAT["ffmpeg_crop_video"]
    user_input, uploads = H.build_request(spec, media, "video", {"width": 4000, "height": 4000})
    job = api.run("ffmpeg_crop_video", user_input, uploads)
    assert not job.ok
    assert job.result.get("returncode") not in (0, None) or job.error


@need("ffmpeg")
def test_a_video_is_required_not_an_audio_file(api, media):
    """Les actions ffmpeg à un fichier n'acceptent que des vidéos : refus net à la création (422)."""
    spec = ACTION_ALL_CAT["ffmpeg_mute_video"]
    user_input, uploads = H.build_request(spec, media, "audio")
    r = api.create("ffmpeg_mute_video", user_input, uploads)
    assert r.status_code == 422 and "vidéo" in r.text


@need("sox")
def test_sox_refuses_a_non_audio_file(api, media):
    spec = ACTION_ALL_CAT["sox_reverse_audio"]
    user_input, uploads = H.build_request(spec, media, "image")
    assert api.create("sox_reverse_audio", user_input, uploads).status_code == 422


@need("magick")
def test_magick_refuses_a_non_image_file(api, media):
    spec = ACTION_ALL_CAT["magick_grayscale"]
    user_input, uploads = H.build_request(spec, media, "audio")
    assert api.create("magick_grayscale", user_input, uploads).status_code == 422


@need("magick")
def test_overlay_text_accepts_accents_and_refuses_imagemagick_escapes(api, media):
    """Le texte de filigrane : lettres accentuées OK ; `%`, `@fichier`, `\\` refusés AVANT exécution."""
    spec = ACTION_ALL_CAT["magick_watermark_text"]
    ok_input, uploads = H.build_request(spec, media, "image", {"text": "Café © Bénin 2026"})
    assert api.run("magick_watermark_text", ok_input, uploads).ok

    for evil in ("%[fx:w]", "@/etc/passwd", "a\\nb", "x'; rm", "-draw", ""):
        bad_input, uploads = H.build_request(spec, media, "image", {"text": evil})
        r = api.create("magick_watermark_text", bad_input, uploads)
        assert r.status_code == 422, f"{evil!r} aurait dû être refusé : {r.status_code}"


@need("magick")
def test_animated_gif_to_webp_is_not_empty(api, media, tmp_path):
    """Régression : GIF animé -> WebP produisait un fichier de 0 octet (il manquait `-coalesce`)."""
    spec = ACTION_ALL_CAT["magick_convert_format"]
    user_input, uploads = H.build_request(spec, media, "gif", {"output_format": "webp"})
    job = api.run("magick_convert_format", user_input, uploads)
    assert job.ok, job.error or job.result
    data = job.download()
    assert len(data) > 500 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
