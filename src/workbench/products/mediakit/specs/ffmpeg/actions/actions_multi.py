#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:25:07 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions FFmpeg : Concaténation et Assemblage Multi-fichiers.

Le fichier pour les opérations multi-fichiers (concaténation de plusieurs vidéos via MultiPathArg et création d'une vidéo YouTube/Podcast à partir d'une image fixe et d'un MP3).
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, PatternArg, BoolArg, MultiPathArg, MultiPathMode,
    IntArg
)
from workbench.products.mediakit.specs.ffmpeg.base_spec import FfmpegSpec
from workbench.products.mediakit.specs.ffmpeg.base_model import (
    ConcatVideosInput, ImagePlusAudioInput
)

MIN_FFMPEG_VERSION = (4, 0)


# ─── 1. CONCATÉNER PLUSIEURS VIDÉOS (AVEC NORMALISATION DES FORMATS) ─────────
def _build_concat_args(u: ConcatVideosInput) -> list:
    n = len(u.inputs)
    
    # 1. Normalisation vidéo : chaque clip est mis à l'échelle (1080p max),
    # centré avec bandes noires si le ratio diffère, avec SAR=1 et format yuv420p.
    # Cela élimine 100% des crashs FFmpeg sur les différences de résolutions/ratios.
    v_prep = "".join(
        f"[{i}:v:0]scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{i}];"
        for i in range(n)
    )

    args = [
        MultiPathArg(
            flag="-i",
            values=u.inputs,
            must_exist=True,
            mode=MultiPathMode.REPEAT_FLAG
        )
    ]

    if u.has_audio:
        # 2. Normalisation audio : harmonise fréquence (44.1kHz) et stéréo
        a_prep = "".join(
            f"[{i}:a:0]aformat=sample_rates=44100:channel_layouts=stereo[a{i}];"
            for i in range(n)
        )
        concat_chain = "".join(f"[v{i}][a{i}]" for i in range(n))
        filter_complex = f"{v_prep}{a_prep}{concat_chain}concat=n={n}:v=1:a=1[outv][outa]"
        
        args.extend([
            PatternArg(flag="-filter_complex", value=filter_complex),
            PatternArg(flag="-map", value="[outv]"),
            PatternArg(flag="-map", value="[outa]"),
            EnumArg(flag="-c:v", value="libx264", enum_values=["libx264"]),
            PatternArg(flag="-pix_fmt", value="yuv420p"),
            EnumArg(flag="-c:a", value="aac", enum_values=["aac"]),
            EnumArg(flag="-b:a", value="192k", enum_values=["192k"]),
        ])
    else:
        # Mode vidéo seule (permet de concaténer des timelapses ou rushs sans son)
        concat_chain = "".join(f"[v{i}]" for i in range(n))
        filter_complex = f"{v_prep}{concat_chain}concat=n={n}:v=1:a=0[outv]"
        
        args.extend([
            PatternArg(flag="-filter_complex", value=filter_complex),
            PatternArg(flag="-map", value="[outv]"),
            EnumArg(flag="-c:v", value="libx264", enum_values=["libx264"]),
            PatternArg(flag="-pix_fmt", value="yuv420p"),
        ])

    args.append(PathArg(value="concatenated.mp4"))
    return args


concat_videos_spec = FfmpegSpec[ConcatVideosInput](
    id="ffmpeg_concat_videos",
    label="Assembler plusieurs vidéos bout à bout (dans l'ordre d'upload)",
    input_cls=ConcatVideosInput,
    validate_arg=False,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="concatenated.mp4",
    build_args=_build_concat_args
)


# ─── 2. CRÉER UNE VIDÉO DEPUIS UNE IMAGE FIXE + UN FICHIER AUDIO ─────────────
image_plus_audio_spec = FfmpegSpec[ImagePlusAudioInput](
    id="ffmpeg_image_plus_audio",
    label="Créer une vidéo YouTube/Podcast à partir d'une image fixe et d'un audio",
    input_cls=ImagePlusAudioInput,
    validate_arg=False,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="podcast_video.mp4",
    auto_even_dimensions=True,
    build_args=lambda u: [
        IntArg(flag="-loop", value=1, min_value=1, max_value=1),  # -loop 1 obligatoire
        PathArg(flag="-i", value=u.image_file, must_exist=True),
        PathArg(flag="-i", value=u.audio_file, must_exist=True),
        EnumArg(flag="-c:v", value="libx264", enum_values=["libx264"]),
        EnumArg(flag="-c:a", value="aac", enum_values=["aac"]),
        EnumArg(flag="-b:a", value="192k", enum_values=["192k"]),
        PatternArg(flag="-pix_fmt", value="yuv420p"),
        BoolArg(flag="-shortest", value=True),
        PathArg(value="podcast_video.mp4")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
FFMPEG_MULTI_ACTIONS = collect_specs(__name__)
__all__ = ["FFMPEG_MULTI_ACTIONS"]
