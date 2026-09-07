#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:17:40 2026

@author: hounsousamuel
"""


"""
Workbench Mediakit — Actions FFmpeg : Extraction Audio, Frames et Sous-titres.

Ce fichier gère l'extraction de la piste audio (sans perte ou avec ré-encodage), 
la capture d'images fixes à un timestamp donné, l'extraction de séquences de miniatures et 
l'extraction de sous-titres intégré.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, FloatArg, PatternArg, BoolArg, IntArg
)
from workbench.products.mediakit.specs.ffmpeg.base_spec import FfmpegSpec
from workbench.products.mediakit.specs.ffmpeg.base_model import (
    ExtractAudioLosslessInput, ExtractAudioConvertInput,
    ExtractFrameInput, ExtractFramesSeriesInput, ExtractSubtitlesInput
)

MIN_FFMPEG_VERSION = (4, 0)


_AUDIO_CODECS = {
    "mp3": "libmp3lame",
    "wav": "pcm_s16le",
    "aac": "aac",
    "flac": "flac",
    "ogg": "libvorbis",
}

def _build_extract_audio_args(u: ExtractAudioConvertInput) -> list:
    args = [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        BoolArg(flag="-vn", value=True),
        EnumArg(
            flag="-c:a",
            value=_AUDIO_CODECS[u.output_format],
            enum_values=list(_AUDIO_CODECS.values()),
        ),
    ]
    # N'appliquer le bitrate que pour les formats compressés à perte
    if u.output_format in ("mp3", "aac", "ogg"):
        args.append(
            EnumArg(flag="-b:a", value=u.bitrate, enum_values=["128k", "192k", "256k", "320k"])
        )
    args.append(PathArg(value=f"audio.{u.output_format}"))
    return args

# ─── 1. EXTRACTION AUDIO SANS PERTE (-c:a copy) ──────────────────────────────
extract_audio_lossless_spec = FfmpegSpec[ExtractAudioLosslessInput](
    id="ffmpeg_extract_audio_lossless",
    label="Extraire la piste audio sans perte (copie brute du flux audio natif)",
    input_cls=ExtractAudioLosslessInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="audio_extracted.mka",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        BoolArg(flag="-vn", value=True),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="audio_extracted.mka")
    ]
)


# ─── 2. EXTRACTION AUDIO AVEC CONVERSION DE FORMAT ───────────────────────────
extract_audio_convert_spec = FfmpegSpec[ExtractAudioConvertInput](
    id="ffmpeg_extract_audio_convert",
    label="Extraire et convertir la piste audio (MP3, WAV, AAC, FLAC, OGG)",
    input_cls=ExtractAudioConvertInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template=lambda u: f"audio.{u.output_format}",
    build_args=_build_extract_audio_args
)


# ─── 3. CAPTURE D'IMAGE UNIQUE (SNAPSHOT) ────────────────────────────────────
extract_frame_single_spec = FfmpegSpec[ExtractFrameInput](
    id="ffmpeg_extract_frame_single",
    label="Capturer une image précise de la vidéo (Snapshot à un timestamp)",
    input_cls=ExtractFrameInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template=lambda u: f"snapshot.{u.output_format}",
    build_args=lambda u: [
        FloatArg(flag="-ss", value=u.timestamp_seconds, min_value=0.0),
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        IntArg(flag="-frames:v", value=1, min_value=1, max_value=1),
        PathArg(value=f"snapshot.{u.output_format}")
    ]
)


# ─── 4. SÉRIE DE MINIATURES (PLANCHE CONTACT) ────────────────────────────────
extract_frames_series_spec = FfmpegSpec[ExtractFramesSeriesInput](
    id="ffmpeg_extract_frames_series",
    label="Extraire une série d'images (1 capture toutes les N secondes)",
    input_cls=ExtractFramesSeriesInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template=lambda u: f"thumb_0001.{u.output_format}",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-vf", value=f"fps=1/{u.every_n_seconds}"),
        PathArg(value=f"thumb_%04d.{u.output_format}")
    ]
)


# ─── 5. EXTRACTION DE SOUS-TITRES INTÉGRÉS ───────────────────────────────────
_SUB_CODECS = {"srt": "subrip", "vtt": "webvtt"}

extract_subtitles_spec = FfmpegSpec[ExtractSubtitlesInput](
    id="ffmpeg_extract_subtitles",
    label="Extraire la piste de sous-titres intégrée (vers fichier .srt ou .vtt)",
    input_cls=ExtractSubtitlesInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template=lambda u: f"subtitles.{u.output_format}",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-map", value="0:s:0"),
        EnumArg(flag="-c:s", value=_SUB_CODECS[u.output_format], enum_values=["subrip", "webvtt"]),
        PathArg(value=f"subtitles.{u.output_format}")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
FFMPEG_EXTRACT_ACTIONS = collect_specs(__name__)
__all__ = ["FFMPEG_EXTRACT_ACTIONS"]