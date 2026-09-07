#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:03:38 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions FFmpeg : Conversion, Compression et Formats Web.

Ce fichier gère les conversions de conteneurs, l'optimisation pour le Web (streaming instantané), 
la compression à qualité constante (CRF), la compression pour respecter une taille maximale en Mo,
 et la création de GIF haute fidélité (avec génération de palette 256 couleurs).
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, IntArg, FloatArg, PatternArg
)
from workbench.products.mediakit.specs.ffmpeg.base_spec import FfmpegSpec
from workbench.products.mediakit.specs.ffmpeg.base_model import (
    ConvertVideoInput, CompressCrfInput, CompressTargetSizeInput,
    VideoToGifInput, FaststartWebInput, _AUDIO_CODEC_BY_FORMAT
)

MIN_FFMPEG_VERSION = (4, 0)


# ─── 1. CONVERTIR LE FORMAT / CONTENEUR ──────────────────────────────────────
convert_format_spec = FfmpegSpec[ConvertVideoInput](
    id="ffmpeg_convert_format",
    auto_even_dimensions=True,
    label="Convertir le format vidéo (MP4, WebM, MKV, AVI, MOV)",
    input_cls=ConvertVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template=lambda u: f"converted.{u.output_format}",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        EnumArg(flag="-c:v", value=u.codec, enum_values=["libx264", "libx265", "vp9"]),
        EnumArg(
            flag="-c:a",
            value=_AUDIO_CODEC_BY_FORMAT.get(u.output_format, "aac"),
            enum_values=["aac", "libopus", "mp3"]
        ),
        PathArg(value=f"converted.{u.output_format}")
    ]
)


# ─── 2. COMPRESSION QUALITÉ CONSTANTE (CRF) ──────────────────────────────────
compress_crf_spec = FfmpegSpec[CompressCrfInput](
    id="ffmpeg_compress_crf",
    auto_even_dimensions=True,
    label="Compresser une vidéo (optimisation du poids via CRF)",
    input_cls=CompressCrfInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="compressed.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        EnumArg(flag="-c:v", value="libx264", enum_values=["libx264"]),
        IntArg(flag="-crf", value=u.crf, min_value=18, max_value=35),
        EnumArg(
            flag="-preset",
            value=u.preset,
            enum_values=["ultrafast", "fast", "medium", "slow", "veryslow"]
        ),
        EnumArg(flag="-c:a", value="aac", enum_values=["aac"]),
        EnumArg(flag="-b:a", value="128k", enum_values=["128k"]),
        PathArg(value="compressed.mp4")
    ]
)


# ─── 3. COMPRESSION POUR TAILLE CIBLE EN MO ──────────────────────────────────
def _calc_target_bitrate_bps(u: CompressTargetSizeInput) -> int:
    """Calcule le bitrate vidéo exact en bits/sec pour respecter le poids cible en Mo."""
    target_kbits = u.target_size_mb * 8192
    audio_bitrate_kbps = 128
    video_bitrate_kbps = max(64, int((target_kbits / u.duration_seconds) - audio_bitrate_kbps))
    return video_bitrate_kbps * 1000


compress_target_size_spec = FfmpegSpec[CompressTargetSizeInput](
    id="ffmpeg_compress_target_size",
    auto_even_dimensions=True,
    label="Compresser pour atteindre un poids cible (ex: <8 Mo Discord, <25 Mo Mail)",
    input_cls=CompressTargetSizeInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="target_size.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        EnumArg(flag="-c:v", value="libx264", enum_values=["libx264"]),
        IntArg(flag="-b:v", value=_calc_target_bitrate_bps(u), min_value=64000),
        EnumArg(flag="-c:a", value="aac", enum_values=["aac"]),
        EnumArg(flag="-b:a", value="128k", enum_values=["128k"]),
        PathArg(value="target_size.mp4")
    ]
)


# ─── 4. CRÉATION DE GIF ANIMÉ (HAUTE QUALITÉ AVEC PALETTE) ───────────────────
video_to_gif_spec = FfmpegSpec[VideoToGifInput](
    id="ffmpeg_video_to_gif",
    label="Créer un GIF animé fluide (génération de palette 256 couleurs)",
    input_cls=VideoToGifInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="animated.gif",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(
            flag="-vf",
            value=f"fps={u.fps},scale={u.width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
        ),
        FloatArg(flag="-t", value=u.duration_s, min_value=0.5, max_value=30.0),  # Option de sortie propre
        PathArg(value="animated.gif")
    ]
)


# ─── 5. OPTIMISATION STREAMING WEB (FASTSTART) ───────────────────────────────
faststart_web_spec = FfmpegSpec[FaststartWebInput](
    id="ffmpeg_faststart_web",
    label="Optimiser pour le streaming web (déplacement moov atom pour lecture instantanée)",
    input_cls=FaststartWebInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="web_ready.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        EnumArg(flag="-c", value="copy", enum_values=["copy"]),
        PatternArg(flag="-movflags", value="+faststart"),
        PathArg(value="web_ready.mp4")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
FFMPEG_CONVERT_ACTIONS = collect_specs(__name__)
__all__ = ["FFMPEG_CONVERT_ACTIONS"]