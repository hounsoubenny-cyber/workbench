"""
Mediakit — utilitaires : détection de type (libmagic), validation du texte de filigrane, et
régression de `validate_args` (étapes de pipeline dont le modèle n'hérite pas de la classe de base).
"""

import pytest

from workbench.products.mediakit.mk_utils.text import OVERLAY_TEXT_PATTERN, check_overlay_text
from workbench.products.mediakit.mk_utils.utils import is_audio_file, is_image_file, is_video_file
from workbench.products.mediakit.specs.utils import ACTION_ALL_CAT
from workbench.products.mediakit.tests.conftest import need
from workbench.wb_utils.model_parser import model_to_dict


# ─── Détection de type (libmagic) ────────────────────────────────────────────

@need("ffmpeg")
def test_mime_detection_on_real_media(media, tmp_path):
    paths = {}
    for kind, (name, data) in media.items():
        paths[kind] = tmp_path / name
        paths[kind].write_bytes(data)
    assert is_video_file(str(paths["video"])) and not is_video_file(str(paths["audio"]))
    assert is_audio_file(str(paths["audio"])) and not is_audio_file(str(paths["image"]))
    assert is_image_file(str(paths["image"])) and is_image_file(str(paths["gif"]))
    assert not is_image_file(str(paths["subtitles"])) and not is_video_file(str(paths["subtitles"]))


def test_mime_detection_is_false_for_missing_or_text_files(tmp_path):
    text = tmp_path / "notes.png"
    text.write_text("juste du texte renommé en .png")
    assert not is_image_file(str(text)) and not is_video_file(str(text)) and not is_audio_file(str(text))
    assert not is_image_file(str(tmp_path / "absent.png"))


@pytest.mark.xfail(strict=True, reason=(
    "OUVERT : `is_image_file` accepte tout `image/*`, SVG compris. Un SVG est du code (références "
    "externes, délégués selon la politique ImageMagick) : surface d'attaque à fermer en limitant aux "
    "formats raster. Cette suite NE l'exploite PAS (rsvg absent ici) ; à retirer quand corrigé."))
def test_svg_should_not_count_as_a_safe_image(tmp_path):
    svg = tmp_path / "x.png"
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>')
    assert not is_image_file(str(svg))


# ─── Texte de filigrane ──────────────────────────────────────────────────────

@pytest.mark.parametrize("text", ["COPYRIGHT", "Café", "NOUVEL ÉPISODE", "© 2026 Bénin", "a-b_c.d+e #1", "L'été", "日本語"])
def test_overlay_text_accepts_letters_of_any_language(text):
    assert check_overlay_text(text) == text


@pytest.mark.parametrize("text", ["", "%w", "%[fx:w]", "@/etc/passwd", "a\\b", 'say "hi"', "a:b", "x;y", "-draw", "a\nb", "a\x00b", "{x}"])
def test_overlay_text_refuses_imagemagick_escapes_and_controls(text):
    with pytest.raises(ValueError):
        check_overlay_text(text)


def test_overlay_regex_is_the_one_used_by_the_command():
    """La commande et le validateur partagent LA MÊME expression (plus de dérive possible)."""
    from workbench.products.mediakit.specs.magick.actions import actions_overlays
    assert actions_overlays.OVERLAY_TEXT_PATTERN == OVERLAY_TEXT_PATTERN


# ─── validate_args : validate_arg=False doit court-circuiter ─────────────────

def test_validate_args_skips_everything_when_validation_is_disabled(tmp_path):
    """
    Régression : les pipelines appellent TOUJOURS validate_args() ; l'ancien code contrôlait le TYPE
    du modèle avant de regarder `validate_arg`, et faisait échouer toute étape dont le modèle
    n'hérite pas de BaseFfmpegActionInput (pipeline_youtube_podcast_card ne pouvait jamais réussir).
    """
    spec = ACTION_ALL_CAT["ffmpeg_image_plus_audio"]
    assert spec.validate_arg is False
    fields = model_to_dict(spec.input_cls)
    sample = {n: ("a.png" if "image" in n else "a.wav") if f["is_upload"] else f["default"]
              for n, f in fields.items() if f["is_upload"] or f["default"] is not None}
    spec.validate_args(spec.input_cls.model_validate(sample), tmp_path)    # ne doit rien lever
