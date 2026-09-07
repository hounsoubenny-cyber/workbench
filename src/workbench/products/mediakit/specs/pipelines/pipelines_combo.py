#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep  5 11:34:58 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Super-Pipelines Croisés Multi-Outils (SoX + ImageMagick + FFmpeg).

Ce fichier met en valeur toute la puissance architecturale du moteur Workbench :
faire coopérer des binaires hétérogènes sans jamais utiliser de pipe Unix (|) :
- SoX masterise le son, ImageMagick formate l'image 1080p, FFmpeg produit la vidéo YouTube.
- FFmpeg extrait l'audio, SoX le filtre avec précision studio, FFmpeg réinjecte la bande-son.
- FFmpeg capture une frame, ImageMagick la légende avec texte et cadre promotionnel.
- FFmpeg découpe et anime, ImageMagick optimise la compression WebP.
"""

from workbench.specs.registry import collect_specs
from workbench.specs.pipeline_spec import PipelineSpec, PipelineStepSpec
from workbench.products.mediakit.specs.pipelines.base_model import (
    YoutubePodcastCardInput, VideoAudioRemasterInput,
    VideoTeaserCardInput, VideoToOptimizedWebpInput
)
from workbench.products.mediakit.specs.sox.actions.actions_dynamics import normalize_gain_spec, compand_dynamics_spec
from workbench.products.mediakit.specs.sox.actions.actions_eq import bass_treble_spec
from workbench.products.mediakit.specs.sox.base_model import NormalizeGainInput, CompandDynamicsInput, BassTrebleInput
from workbench.products.mediakit.specs.magick.actions.actions_geometry import canvas_extent_spec
from workbench.products.mediakit.specs.magick.actions.actions_overlays import watermark_text_spec, add_border_spec
from workbench.products.mediakit.specs.magick.actions.actions_convert import compress_quality_spec
from workbench.products.mediakit.specs.magick.base_model import CanvasExtentInput, WatermarkTextInput, AddBorderInput, CompressQualityInput
from workbench.products.mediakit.specs.ffmpeg.actions.actions_multi import image_plus_audio_spec
from workbench.products.mediakit.specs.ffmpeg.actions.actions_extract import extract_audio_convert_spec, extract_frame_single_spec
from workbench.products.mediakit.specs.ffmpeg.actions.actions_audio import replace_audio_spec
from workbench.products.mediakit.specs.ffmpeg.actions.actions_convert import video_to_gif_spec
from workbench.products.mediakit.specs.ffmpeg.actions.actions_timing import trim_no_copy_spec
from workbench.products.mediakit.specs.ffmpeg.base_model import (
    ImagePlusAudioInput, ExtractAudioConvertInput, ReplaceAudioInput,
    ExtractFrameInput, TrimVideoInput, VideoToGifInput
)


# ─── 1. GÉNÉRATEUR VIDÉO PODCAST YOUTUBE (SOX + MAGICK -> FFMPEG) ────────────
pipeline_youtube_podcast_card = PipelineSpec[YoutubePodcastCardInput](
    id="pipeline_youtube_podcast_card",
    label="Générateur Podcast YouTube (Normalisation SoX + Pochette Magick 1080p + Vidéo FFmpeg)",
    input_cls=YoutubePodcastCardInput,
    steps=[
        PipelineStepSpec[YoutubePodcastCardInput](
            id="step_sox_norm",
            action=normalize_gain_spec,
            build_step_input=lambda p, o: NormalizeGainInput(
                input_file=p.audio_file,
                target_db=-1.0,
                output_format="wav"
            )
        ),
        PipelineStepSpec[YoutubePodcastCardInput](
            id="step_magick_cover",
            action=canvas_extent_spec,
            build_step_input=lambda p, o: CanvasExtentInput(
                input_file=p.cover_image,
                target_dimension="1920x1080",
                background_color=p.background_color,
                output_format="jpg"
            )
        ),
        PipelineStepSpec[YoutubePodcastCardInput](
            id="step_ffmpeg_mux",
            action=image_plus_audio_spec,
            build_step_input=lambda p, o: ImagePlusAudioInput(
                image_file=o["step_magick_cover"],
                audio_file=o["step_sox_norm"]
            )
        )
    ]
)


# ─── 2. REMASTER AUDIO VIDÉO (FFMPEG -> SOX -> FFMPEG) ───────────────────────
pipeline_video_audio_remaster = PipelineSpec[VideoAudioRemasterInput](
    id="pipeline_video_audio_remaster",
    label="Remasterisation Sonore Vidéo (Extraction WAV -> Traitement Studio SoX -> Réinjection FFmpeg)",
    input_cls=VideoAudioRemasterInput,
    steps=[
        PipelineStepSpec[VideoAudioRemasterInput](
            id="step_extract_wav",
            action=extract_audio_convert_spec,
            build_step_input=lambda p, o: ExtractAudioConvertInput(
                input_file=p.video_file,
                output_format="wav",
                bitrate="192k"
            )
        ),
        PipelineStepSpec[VideoAudioRemasterInput](
            id="step_sox_master",
            action=compand_dynamics_spec,
            build_step_input=lambda p, o: CompandDynamicsInput(
                input_file=o["_previous"],
                profile="podcast_voice",
                output_format="wav"
            )
        ),
        PipelineStepSpec[VideoAudioRemasterInput](
            id="step_sox_eq",
            action=bass_treble_spec,
            build_step_input=lambda p, o: BassTrebleInput(
                input_file=o["_previous"],
                bass_db=p.bass_boost_db,
                treble_db=1.5,
                output_format="wav"
            )
        ),
        PipelineStepSpec[VideoAudioRemasterInput](
            id="step_reinject_audio",
            action=replace_audio_spec,
            build_step_input=lambda p, o: ReplaceAudioInput(
                input_file=p.video_file,
                new_audio_file=o["_previous"]
            )
        )
    ]
)


# ─── 3. CARTE PROMOTIONNELLE TEASER (FFMPEG -> MAGICK) ───────────────────────
pipeline_video_teaser_card = PipelineSpec[VideoTeaserCardInput](
    id="pipeline_video_teaser_card",
    label="Affiche Teaser Réseaux Sociaux (Capture Frame FFmpeg + Titrage et Bordure Magick)",
    input_cls=VideoTeaserCardInput,
    steps=[
        PipelineStepSpec[VideoTeaserCardInput](
            id="step_snapshot",
            action=extract_frame_single_spec,
            build_step_input=lambda p, o: ExtractFrameInput(
                input_file=p.video_file,
                timestamp_seconds=p.snapshot_timestamp_s,
                output_format="jpg"
            )
        ),
        PipelineStepSpec[VideoTeaserCardInput](
            id="step_text_badge",
            action=watermark_text_spec,
            build_step_input=lambda p, o: WatermarkTextInput(
                input_file=o["_previous"],
                text=p.teaser_text,
                position="south",
                pointsize=36,
                color=p.text_color,
                output_format="jpg"
            )
        ),
        PipelineStepSpec[VideoTeaserCardInput](
            id="step_frame_border",
            action=add_border_spec,
            build_step_input=lambda p, o: AddBorderInput(
                input_file=o["_previous"],
                thickness=18,
                color="black",
                output_format="jpg"
            )
        )
    ]
)


# ─── 4. ANIMATION WEBP ULTRA-LÉGÈRE (FFMPEG -> MAGICK) ───────────────────────
pipeline_video_to_optimized_webp = PipelineSpec[VideoToOptimizedWebpInput](
    id="pipeline_video_to_optimized_webp",
    label="Animation WebP Optimisée (Découpe & Animation FFmpeg + Compression Magick)",
    input_cls=VideoToOptimizedWebpInput,
    steps=[
        PipelineStepSpec[VideoToOptimizedWebpInput](
            id="step_trim",
            action=trim_no_copy_spec,
            build_step_input=lambda p, o: TrimVideoInput(
                input_file=p.video_file,
                start_seconds=p.start_seconds,
                duration_seconds=p.duration_seconds
            )
        ),
        PipelineStepSpec[VideoToOptimizedWebpInput](
            id="step_gif_anim",
            action=video_to_gif_spec,
            build_step_input=lambda p, o: VideoToGifInput(
                input_file=o["_previous"],
                fps=15,
                width=p.width,
                duration_s=p.duration_seconds
            )
        ),
        PipelineStepSpec[VideoToOptimizedWebpInput](
            id="step_webp_compress",
            action=compress_quality_spec,
            build_step_input=lambda p, o: CompressQualityInput(
                input_file=o["_previous"],
                quality=78,
                output_format="webp"
            )
        )
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
PIPELINES_COMBO_ACTIONS = collect_specs(__name__, spec_type=PipelineSpec)
__all__ = ["PIPELINES_COMBO_ACTIONS"]