#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:21:27 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions FFmpeg : Découpe, Vitesse, FPS et Timing.

Ce fichier gère le découpage temporel (rapide ou chirurgical), le changement de cadence d'images (FPS),
 l'accélération/ralenti audio-vidéo synchronisé et l'inversion de vidéo.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, FloatArg, PatternArg, IntArg
)
from workbench.products.mediakit.specs.ffmpeg.base_spec import FfmpegSpec
from workbench.products.mediakit.specs.ffmpeg.base_model import (
    TrimVideoInput, SpeedVideoInput, ReverseVideoInput, ChangeFpsInput
)

MIN_FFMPEG_VERSION = (4, 0)


# ─── 1. DÉCOUPE RAPIDE SANS RÉ-ENCODAGE (-c copy) ────────────────────────────
trim_with_copy_spec = FfmpegSpec[TrimVideoInput](
    id="ffmpeg_trim_with_copy",
    label="Découper une vidéo (rapide, sans ré-encodage, calé sur keyframe)",
    input_cls=TrimVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="trimmed_copy.mp4",
    build_args=lambda u: [
        FloatArg(flag="-ss", value=u.start_seconds, min_value=0.0),
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        FloatArg(flag="-t", value=u.duration_seconds, min_value=0.01),
        EnumArg(flag="-c", value="copy", enum_values=["copy"]),
        PathArg(value="trimmed_copy.mp4")
    ]
)


# ─── 2. DÉCOUPE EXACTE À LA FRAME PRÈS (RÉ-ENCODAGE) ─────────────────────────
trim_no_copy_spec = FfmpegSpec[TrimVideoInput](
    id="ffmpeg_trim_no_copy",
    auto_even_dimensions=True,
    label="Découper une vidéo (précision absolue à la milliseconde près)",
    input_cls=TrimVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="trimmed_exact.mp4",
    build_args=lambda u: [
        FloatArg(flag="-ss", value=u.start_seconds, min_value=0.0),
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        FloatArg(flag="-t", value=u.duration_seconds, min_value=0.01),
        EnumArg(flag="-c:v", value="libx264", enum_values=["libx264"]),
        EnumArg(flag="-c:a", value="aac", enum_values=["aac"]),
        PathArg(value="trimmed_exact.mp4")
    ]
)


# ─── 3. ACCÉLÉRÉ / RALENTI SYNCHRONISÉ AUDIO & VIDÉO ─────────────────────────
_SPEED_FILTERS = {
    "0.25": "[0:v]setpts=4.0*PTS[v];[0:a]atempo=0.5,atempo=0.5[a]",
    "0.5":  "[0:v]setpts=2.0*PTS[v];[0:a]atempo=0.5[a]",
    "0.75": "[0:v]setpts=1.333*PTS[v];[0:a]atempo=0.75[a]",
    "1.25": "[0:v]setpts=0.8*PTS[v];[0:a]atempo=1.25[a]",
    "1.5":  "[0:v]setpts=0.667*PTS[v];[0:a]atempo=1.5[a]",
    "2.0":  "[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]",
}

speed_video_spec = FfmpegSpec[SpeedVideoInput](
    id="ffmpeg_speed_video",
    label="Modifier la vitesse de lecture (accéléré / ralenti audio et vidéo)",
    input_cls=SpeedVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="speed_adjusted.mp4",
    auto_even_dimensions=True,
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-filter_complex", value=_SPEED_FILTERS[u.speed_factor]),
        PatternArg(flag="-map", value="[v]"),
        PatternArg(flag="-map", value="[a]"),
        EnumArg(flag="-c:v", value="libx264", enum_values=["libx264"]),
        EnumArg(flag="-c:a", value="aac", enum_values=["aac"]),
        PathArg(value="speed_adjusted.mp4")
    ]
)


# ─── 4. INVERSER LE SENS DE LECTURE (REVERSE) ────────────────────────────────
reverse_video_spec = FfmpegSpec[ReverseVideoInput](
    id="ffmpeg_reverse_video",
    auto_even_dimensions=True,
    label="Inverser la vidéo et l'audio (effet rembobinage)",
    input_cls=ReverseVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="reversed.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-vf", value="reverse"),
        PatternArg(flag="-af", value="areverse"),
        EnumArg(flag="-c:v", value="libx264", enum_values=["libx264"]),
        EnumArg(flag="-c:a", value="aac", enum_values=["aac"]),
        PathArg(value="reversed.mp4")
    ]
)


# ─── 5. MODIFIER LA CADENCE D'IMAGES (FPS) ───────────────────────────────────
change_fps_spec = FfmpegSpec[ChangeFpsInput](
    id="ffmpeg_change_fps",
    auto_even_dimensions=True,
    label="Changer le framerate / FPS (ex: 60 FPS -> 30 FPS ou 24 FPS cinéma)",
    input_cls=ChangeFpsInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="fps_adjusted.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        IntArg(flag="-r", value=u.fps, min_value=15, max_value=60),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="fps_adjusted.mp4")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
FFMPEG_TIMING_ACTIONS = collect_specs(__name__)
__all__ = ["FFMPEG_TIMING_ACTIONS"]