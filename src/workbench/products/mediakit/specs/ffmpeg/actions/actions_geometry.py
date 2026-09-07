#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:22:43 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions FFmpeg : Géométrie, Recadrage et Formats Sociaux.
Ce fichier gère la géométrie de l'image : redimensionnement, recadrage manuel, rotation, miroir, bandes noires (letterboxing) et 
adaptation verticale pour les réseaux sociaux (TikTok, Reels, Shorts).
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, PatternArg
)
from workbench.products.mediakit.specs.ffmpeg.base_spec import FfmpegSpec
from workbench.products.mediakit.specs.ffmpeg.base_model import (
    ResizeVideoInput, CropVideoInput, SocialVerticalInput,
    RotateVideoInput, FlipVideoInput, PadLetterboxInput, _RESOLUTIONS
)

MIN_FFMPEG_VERSION = (4, 0)


# ─── 1. REDIMENSIONNEMENT PRÉDÉFINI ──────────────────────────────────────────
resize_video_spec = FfmpegSpec[ResizeVideoInput](
    id="ffmpeg_resize_video",
    label="Redimensionner la vidéo (1080p, 720p, 480p, 360p, 240p)",
    input_cls=ResizeVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="resized.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        EnumArg(
            flag="-vf",
            value=f"scale={u.resolution.replace('x', ':')}",
            enum_values=[f"scale={r.replace('x', ':')}" for r in _RESOLUTIONS]
        ),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="resized.mp4")
    ]
)


# ─── 2. RECADRAGE MANUEL (CROP WxH+X+Y) ──────────────────────────────────────
crop_video_spec = FfmpegSpec[CropVideoInput](
    id="ffmpeg_crop_video",
    auto_even_dimensions=True,
    label="Recadrer la vidéo (rogner une zone rectangulaire)",
    input_cls=CropVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="cropped.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-vf", value=f"crop={u.width}:{u.height}:{u.x}:{u.y}"),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="cropped.mp4")
    ]
)


# ─── 3. ADAPTATION FORMAT VERTICAL 9:16 (TIKTOK / REELS / SHORTS) ────────────
_SOCIAL_VERTICAL_FILTERS = {
    # Crop centré pur avec largeur impérativement arrondie au multiple de 2 le plus proche
    "crop_center": "crop=trunc(ih*(9/16)/2)*2:ih",
    # Vidéo originale au centre avec arrière-plan flouté en haut et bas
    "blur_background": (
        "split[main][bg];"
        "[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5[bgblur];"
        "[main]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
        "[bgblur][fg]overlay=(W-w)/2:(H-h)/2"
    )
}

social_vertical_spec = FfmpegSpec[SocialVerticalInput](
    id="ffmpeg_social_vertical",
    label="Convertir au format 9:16 vertical (Reels, TikTok, Shorts)",
    input_cls=SocialVerticalInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="vertical_social.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(
            flag="-vf" if u.mode == "crop_center" else "-filter_complex",
            value=_SOCIAL_VERTICAL_FILTERS[u.mode]
        ),
        EnumArg(flag="-c:v", value="libx264", enum_values=["libx264"]),
        PatternArg(flag="-pix_fmt", value="yuv420p"),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="vertical_social.mp4")
    ]
)


# ─── 4. ROTATION VIDÉO (90°, 180°) ───────────────────────────────────────────
_ROTATION_FILTERS = {
    "90_cw":  "transpose=1",
    "90_ccw": "transpose=2",
    "180":    "transpose=1,transpose=1"
}

rotate_video_spec = FfmpegSpec[RotateVideoInput](
    id="ffmpeg_rotate_video",
    auto_even_dimensions=True,
    label="Faire pivoter la vidéo (90° horaire, anti-horaire ou 180°)",
    input_cls=RotateVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="rotated.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-vf", value=_ROTATION_FILTERS[u.rotation]),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="rotated.mp4")
    ]
)


# ─── 5. EFFET MIROIR (FLIP / FLOP) ───────────────────────────────────────────
flip_video_spec = FfmpegSpec[FlipVideoInput](
    id="ffmpeg_flip_video",
    auto_even_dimensions=True,
    label="Appliquer un effet miroir (horizontal ou vertical)",
    input_cls=FlipVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="flipped.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-vf", value="hflip" if u.direction == "horizontal" else "vflip"),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="flipped.mp4")
    ]
)


# ─── 6. LETTERBOXING (AJOUT DE BANDES NOIRES / BLANCHES) ──────────────────────
_PAD_FILTERS = {
    "16:9": "pad=trunc(max(iw\\,ih*(16/9))/2)*2:trunc(max(ih\\,iw*(9/16))/2)*2:(ow-iw)/2:(oh-ih)/2",
    "4:3":  "pad=trunc(max(iw\\,ih*(4/3))/2)*2:trunc(max(ih\\,iw*(3/4))/2)*2:(ow-iw)/2:(oh-ih)/2",
    "1:1":  "pad=trunc(max(iw\\,ih)/2)*2:trunc(max(iw\\,ih)/2)*2:(ow-iw)/2:(oh-ih)/2"
}
pad_letterbox_spec = FfmpegSpec[PadLetterboxInput](
    id="ffmpeg_pad_letterbox",
    auto_even_dimensions=True,
    label="Ajouter des bandes noires / marges pour forcer un ratio d'aspect",
    input_cls=PadLetterboxInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="letterbox.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-vf", value=f"{_PAD_FILTERS[u.target_aspect]}:{u.color}"),
        EnumArg(flag="-c:v", value="libx264", enum_values=["libx264"]),
        PatternArg(flag="-pix_fmt", value="yuv420p"),
        EnumArg(flag="-c:a", value="copy", enum_values=["copy"]),
        PathArg(value="letterbox.mp4")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================

FFMPEG_GEOMETRY_ACTIONS = collect_specs(__name__)
__all__ = ["FFMPEG_GEOMETRY_ACTIONS"]