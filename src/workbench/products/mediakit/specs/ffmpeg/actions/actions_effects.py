#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:24:43 2026

@author: hounsousamuel
"""


"""
Workbench Mediakit — Actions FFmpeg : Incrustations et Effets Visuels.

Ce fichier gère les incrustations visuelles : watermark de logo, incrustation de sous-titres en dur (hardsub), 
ajustement des couleurs/luminosité/saturation, et flou d'anonymisation.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, PatternArg, MultiPathArg, MultiPathMode
)
from workbench.products.mediakit.specs.ffmpeg.base_spec import FfmpegSpec
from workbench.products.mediakit.specs.ffmpeg.base_model import (
    AddWatermarkInput, BurnSubtitlesInput, AdjustColorEqInput, BlurVideoInput
)

MIN_FFMPEG_VERSION = (4, 0)


# ─── 1. INCRUSTER UN LOGO / FILIGRANE IMAGE (WATERMARK) ──────────────────────
_WATERMARK_COORDS = {
    "top_left":     "{m}:{m}",
    "top_right":    "main_w-overlay_w-{m}:{m}",
    "bottom_left":  "{m}:main_h-overlay_h-{m}",
    "bottom_right": "main_w-overlay_w-{m}:main_h-overlay_h-{m}",
    "center":       "(main_w-overlay_w)/2:(main_h-overlay_h)/2"
}

watermark_spec = FfmpegSpec[AddWatermarkInput](
    id="ffmpeg_add_watermark_image",
    label="Incruster un logo en filigrane (PNG transparent)",
    input_cls=AddWatermarkInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="watermarked.mp4",
    build_args=lambda u: [
        MultiPathArg(
            flag="-i",
            values=[u.input_file, u.watermark_image],
            must_exist=True,
            mode=MultiPathMode.REPEAT_FLAG
        ),
        PatternArg(
            flag="-filter_complex",
            value=f"overlay={_WATERMARK_COORDS[u.position].format(m=u.margin_px)}"
        ),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="watermarked.mp4")
    ]
)


# ─── 2. INCRUSTER LES SOUS-TITRES EN DUR (HARDSUB) ───────────────────────────
burn_subtitles_spec = FfmpegSpec[BurnSubtitlesInput](
    id="ffmpeg_burn_subtitles",
    auto_even_dimensions=True,
    label="Incruster des sous-titres .srt en dur directement dans l'image",
    input_cls=BurnSubtitlesInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="subtitles_burned.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-vf", value=f"subtitles=\\'{u.subtitles_file}\\'"),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="subtitles_burned.mp4")
    ],
)


# ─── 3. AJUSTER COULEURS, LUMINOSITÉ ET SATURATION ───────────────────────────
adjust_color_eq_spec = FfmpegSpec[AdjustColorEqInput](
    id="ffmpeg_adjust_color_eq",
    auto_even_dimensions=True,
    label="Corriger l'exposition (luminosité, contraste, saturation)",
    input_cls=AdjustColorEqInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="color_adjusted.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(
            flag="-vf",
            value=f"eq=brightness={u.brightness}:contrast={u.contrast}:saturation={u.saturation}"
        ),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="color_adjusted.mp4")
    ]
)


# ─── 4. FLOU D'ANONYMISATION GLOBAL ──────────────────────────────────────────
blur_video_spec = FfmpegSpec[BlurVideoInput](
    id="ffmpeg_blur_video",
    auto_even_dimensions=True,
    label="Appliquer un flou global sur l'ensemble de la vidéo",
    input_cls=BlurVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="blurred.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-vf", value=f"boxblur={u.intensity}:1"),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="blurred.mp4")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
FFMPEG_EFFECTS_ACTIONS = collect_specs(__name__)
__all__ = ["FFMPEG_EFFECTS_ACTIONS"]