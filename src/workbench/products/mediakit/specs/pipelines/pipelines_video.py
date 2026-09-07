#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep  5 11:35:50 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions Pipelines FFmpeg : Workflows Vidéo Dédiés.

Ce fichier orchestre des enchaînements multi-étapes 100% vidéo :
le recyclage automatique de rushs 16:9 en Shorts/TikTok/Reels 9:16 avec logo,
l'optimisation chirurgicale de vidéos pour le web (720p + compression CRF + faststart),
la fabrication de GIF animés haute fidélité, l'incrustation de sous-titres suivie
de l'adaptation verticale, et l'accélération timelapse muette.
"""

from workbench.specs.registry import collect_specs
from workbench.specs.pipeline_spec import PipelineSpec, PipelineStepSpec
from workbench.products.mediakit.specs.pipelines.base_model import (
    SocialRepurposerInput, WebOptimizerInput, ProGifMakerInput,
    HardsubSocialInput, SpeedupMuteInput
)
from workbench.products.mediakit.specs.ffmpeg.actions.actions_timing import (
    trim_no_copy_spec, trim_with_copy_spec, speed_video_spec
)
from workbench.products.mediakit.specs.ffmpeg.actions.actions_geometry import (
    social_vertical_spec, resize_video_spec
)
from workbench.products.mediakit.specs.ffmpeg.actions.actions_effects import (
    watermark_spec, burn_subtitles_spec
)
from workbench.products.mediakit.specs.ffmpeg.actions.actions_convert import (
    compress_crf_spec, faststart_web_spec, video_to_gif_spec
)
from workbench.products.mediakit.specs.ffmpeg.actions.actions_audio import (
    mute_video_spec
)
from workbench.products.mediakit.specs.ffmpeg.base_model import (
    TrimVideoInput, SocialVerticalInput, AddWatermarkInput,
    ResizeVideoInput, CompressCrfInput, FaststartWebInput,
    VideoToGifInput, BurnSubtitlesInput, SpeedVideoInput, MuteVideoInput
)


# ─── 1. RECYCLEUR VIDÉO SOCIAL (TRIM -> VERTICAL 9:16 -> LOGO) ───────────────
pipeline_social_repurposer = PipelineSpec[SocialRepurposerInput](
    id="pipeline_social_repurposer",
    label="Recycleur Réseaux Sociaux (Découpe + Format vertical 9:16 + Watermark)",
    input_cls=SocialRepurposerInput,
    steps=[
        PipelineStepSpec[SocialRepurposerInput](
            id="step_trim",
            action=trim_no_copy_spec,
            build_step_input=lambda p, o: TrimVideoInput(
                input_file=p.input_file,
                start_seconds=p.start_seconds,
                duration_seconds=p.duration_seconds
            )
        ),
        PipelineStepSpec[SocialRepurposerInput](
            id="step_vertical",
            action=social_vertical_spec,
            build_step_input=lambda p, o: SocialVerticalInput(
                input_file=o["_previous"],
                mode=p.vertical_mode
            )
        ),
        PipelineStepSpec[SocialRepurposerInput](
            id="step_watermark",
            action=watermark_spec,
            build_step_input=lambda p, o: AddWatermarkInput(
                input_file=o["_previous"],
                watermark_image=p.watermark_logo,
                position=p.logo_position,
                margin_px=20
            )
        )
    ]
)


# ─── 2. COMPRESSEUR WEB HAUTE PERFORMANCE (RESIZE -> COMPRESS -> FASTSTART) ──
pipeline_web_optimizer = PipelineSpec[WebOptimizerInput](
    id="pipeline_web_optimizer",
    label="Optimiseur Web Vidéo (Descente 720p + Compression CRF + Faststart streaming)",
    input_cls=WebOptimizerInput,
    steps=[
        PipelineStepSpec[WebOptimizerInput](
            id="step_resize",
            action=resize_video_spec,
            build_step_input=lambda p, o: ResizeVideoInput(
                input_file=p.input_file,
                resolution=p.resolution
            )
        ),
        PipelineStepSpec[WebOptimizerInput](
            id="step_compress",
            action=compress_crf_spec,
            build_step_input=lambda p, o: CompressCrfInput(
                input_file=o["_previous"],
                crf=p.crf_quality,
                preset="slow"
            )
        ),
        PipelineStepSpec[WebOptimizerInput](
            id="step_faststart",
            action=faststart_web_spec,
            build_step_input=lambda p, o: FaststartWebInput(
                input_file=o["_previous"]
            )
        )
    ]
)


# ─── 3. FABRIQUE DE GIF ANIMÉ (TRIM -> GIF PALETTE) ──────────────────────────
pipeline_pro_gif_maker = PipelineSpec[ProGifMakerInput](
    id="pipeline_pro_gif_maker",
    label="Générateur de GIF animé (Découpe d'extrait + Palette 256 couleurs)",
    input_cls=ProGifMakerInput,
    steps=[
        PipelineStepSpec[ProGifMakerInput](
            id="step_trim_copy",
            action=trim_with_copy_spec,
            build_step_input=lambda p, o: TrimVideoInput(
                input_file=p.input_file,
                start_seconds=p.start_seconds,
                duration_seconds=p.duration_seconds
            )
        ),
        PipelineStepSpec[ProGifMakerInput](
            id="step_palette_gif",
            action=video_to_gif_spec,
            build_step_input=lambda p, o: VideoToGifInput(
                input_file=o["_previous"],
                fps=p.fps,
                width=p.width,
                duration_s=p.duration_seconds  # Appliqué sur le clip déjà taillé
            )
        )
    ]
)



# ─── 4. SOUS-TITRAGE HARDSUB + FORMAT VERTICAL ───────────────────────────────
pipeline_hardsub_social = PipelineSpec[HardsubSocialInput](
    id="pipeline_hardsub_social",
    label="Vidéo Sociale Sous-titrée (Format 9:16 vertical puis incrustation SRT)",
    input_cls=HardsubSocialInput,
    steps=[
        # Étape 1 : On recadre d'abord au format vertical 9:16
        PipelineStepSpec[HardsubSocialInput](
            id="step_vertical",
            action=social_vertical_spec,
            build_step_input=lambda p, o: SocialVerticalInput(
                input_file=p.input_file,
                mode=p.vertical_mode
            )
        ),
        # Étape 2 : On incruste les sous-titres à l'intérieur du cadre 9:16 déjà prêt
        PipelineStepSpec[HardsubSocialInput](
            id="step_burn_sub",
            action=burn_subtitles_spec,
            build_step_input=lambda p, o: BurnSubtitlesInput(
                input_file=o["_previous"],
                subtitles_file=p.subtitles_file
            )
        )
    ]
)


# ─── 5. ACCÉLÉRATION TIMELAPSE MUET (SPEED -> MUTE) ──────────────────────────
pipeline_speedup_mute = PipelineSpec[SpeedupMuteInput](
    id="pipeline_speedup_mute",
    label="Timelapse Vidéo (Accélération x2 + Coupure définitive du son)",
    input_cls=SpeedupMuteInput,
    steps=[
        PipelineStepSpec[SpeedupMuteInput](
            id="step_speed",
            action=speed_video_spec,
            build_step_input=lambda p, o: SpeedVideoInput(
                input_file=p.input_file,
                speed_factor=p.speed_factor
            )
        ),
        PipelineStepSpec[SpeedupMuteInput](
            id="step_mute",
            action=mute_video_spec,
            build_step_input=lambda p, o: MuteVideoInput(
                input_file=o["_previous"]
            )
        )
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
PIPELINES_VIDEO_ACTIONS = collect_specs(__name__, spec_type=PipelineSpec)
__all__ = ["PIPELINES_VIDEO_ACTIONS"]