#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep  5 11:35:16 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions Pipelines SoX : Workflows Audio Dédiés.

Ce fichier orchestre des enchaînements DSP de studio 100% audio :
le mastering vocal complet pour podcasts et interviews (anti-rumble, compand, norm),
le conditionnement optimal de fichiers vocaux pour les IA de transcription (Whisper),
la fabrication de jingles de transition radio (tempo, reverb, fade out),
et la transformation vintage Lo-Fi (égalisation réductrice et saturation analogique).
"""

from workbench.specs.registry import collect_specs
from workbench.specs.pipeline_spec import PipelineSpec, PipelineStepSpec
from workbench.products.mediakit.specs.pipelines.base_model import (
    PodcastMasteringInput, SpeechToTextPrepInput, DjStingerInput, LofiRetroInput
)
from workbench.products.mediakit.specs.sox.actions.actions_dynamics import (
    strip_silence_spec, compand_dynamics_spec, normalize_gain_spec
)
from workbench.products.mediakit.specs.sox.actions.actions_eq import (
    highpass_spec, lowpass_spec, bass_treble_spec
)
from workbench.products.mediakit.specs.sox.actions.actions_convert import (
    channels_remix_spec, resample_audio_spec, convert_audio_spec
)
from workbench.products.mediakit.specs.sox.actions.actions_timing import (
    trim_audio_spec, change_tempo_spec, fade_audio_spec
)
from workbench.products.mediakit.specs.sox.actions.actions_effects import (
    reverb_audio_spec, overdrive_audio_spec
)
from workbench.products.mediakit.specs.sox.base_model import (
    StripSilenceInput, HighPassFilterInput, CompandDynamicsInput, NormalizeGainInput,
    ChannelsRemixInput, ResampleAudioInput, TrimAudioInput, ChangeTempoInput,
    FadeAudioInput, ReverbAudioInput, LowPassFilterInput, BassTrebleInput,
    OverdriveAudioInput, ConvertAudioInput
)


# ─── 1. MASTERING VOCAL PODCAST (SILENCE -> HIGHPASS -> COMPAND -> NORM) ─────
pipeline_podcast_mastering = PipelineSpec[PodcastMasteringInput](
    id="pipeline_podcast_mastering",
    label="Mastering Vocal Studio (Coupe-silence + Anti-rumble + Compresseur + Normalisation)",
    input_cls=PodcastMasteringInput,
    steps=[
        PipelineStepSpec[PodcastMasteringInput](
            id="step_strip_silence",
            action=strip_silence_spec,
            build_step_input=lambda p, o: StripSilenceInput(
                input_file=p.input_file,
                threshold_percent=1.0,
                min_silence_duration=0.4,
                output_format="wav"
            )
        ),
        PipelineStepSpec[PodcastMasteringInput](
            id="step_highpass",
            action=highpass_spec,
            build_step_input=lambda p, o: HighPassFilterInput(
                input_file=o["_previous"],
                cutoff_hz=p.highpass_cutoff_hz,
                output_format="wav"
            )
        ),
        PipelineStepSpec[PodcastMasteringInput](
            id="step_compand",
            action=compand_dynamics_spec,
            build_step_input=lambda p, o: CompandDynamicsInput(
                input_file=o["_previous"],
                profile="podcast_voice",
                output_format="wav"
            )
        ),
        PipelineStepSpec[PodcastMasteringInput](
            id="step_normalize",
            action=normalize_gain_spec,
            build_step_input=lambda p, o: NormalizeGainInput(
                input_file=o["_previous"],
                target_db=p.target_peak_db,
                output_format=p.output_format
            )
        )
    ]
)


# ─── 2. PRÉPARATION IA SPEECH-TO-TEXT / WHISPER (MONO -> 16kHz -> NORM) ──────
pipeline_speech_to_text_prep = PipelineSpec[SpeechToTextPrepInput](
    id="pipeline_speech_to_text_prep",
    label="Conditionnement Audio pour IA Whisper (Mono + Rééchantillonnage 16 kHz + Normalisation)",
    input_cls=SpeechToTextPrepInput,
    steps=[
        PipelineStepSpec[SpeechToTextPrepInput](
            id="step_mono",
            action=channels_remix_spec,
            build_step_input=lambda p, o: ChannelsRemixInput(
                input_file=p.input_file,
                channels="1",
                output_format="wav"
            )
        ),
        PipelineStepSpec[SpeechToTextPrepInput](
            id="step_16k",
            action=resample_audio_spec,
            build_step_input=lambda p, o: ResampleAudioInput(
                input_file=o["_previous"],
                sample_rate="16000",
                output_format="wav"
            )
        ),
        PipelineStepSpec[SpeechToTextPrepInput](
            id="step_norm",
            action=normalize_gain_spec,
            build_step_input=lambda p, o: NormalizeGainInput(
                input_file=o["_previous"],
                target_db=-1.0,
                output_format="wav"
            )
        )
    ]
)


# ─── 3. JINGLE RADIO / DJ STINGER (TRIM -> TEMPO -> REVERB -> FADE) ──────────
pipeline_dj_stinger = PipelineSpec[DjStingerInput](
    id="pipeline_dj_stinger",
    label="Jingle Radio Transition (Extrait court + Accélération + Réverbération + Fondu)",
    input_cls=DjStingerInput,
    steps=[
        PipelineStepSpec[DjStingerInput](
            id="step_trim",
            action=trim_audio_spec,
            build_step_input=lambda p, o: TrimAudioInput(
                input_file=p.input_file,
                start_seconds=p.start_seconds,
                duration_seconds=p.duration_seconds,
                output_format="wav"
            )
        ),
        PipelineStepSpec[DjStingerInput](
            id="step_tempo",
            action=change_tempo_spec,
            build_step_input=lambda p, o: ChangeTempoInput(
                input_file=o["_previous"],
                factor=p.tempo_factor,
                output_format="wav"
            )
        ),
        PipelineStepSpec[DjStingerInput](
            id="step_reverb",
            action=reverb_audio_spec,
            build_step_input=lambda p, o: ReverbAudioInput(
                input_file=o["_previous"],
                reverberance=45,
                damping=40,
                output_format="wav"
            )
        ),
        PipelineStepSpec[DjStingerInput](
            id="step_fade",
            action=fade_audio_spec,
            build_step_input=lambda p, o: FadeAudioInput(
                input_file=o["_previous"],
                curve="t",
                fade_in_s=0.2,
                fade_out_s=p.fade_out_seconds,
                output_format="mp3"
            )
        )
    ]
)


# ─── 4. TRANSFORMATION VINTAGE LO-FI (LOWPASS -> BASS BOOST -> OVERDRIVE) ────
pipeline_lofi_retro = PipelineSpec[LofiRetroInput](
    id="pipeline_lofi_retro",
    label="Effet Audio Lo-Fi Rétro (Filtrage étouffé + Boost des basses + Saturation analogique)",
    input_cls=LofiRetroInput,
    steps=[
        PipelineStepSpec[LofiRetroInput](
            id="step_lowpass",
            action=lowpass_spec,
            build_step_input=lambda p, o: LowPassFilterInput(
                input_file=p.input_file,
                cutoff_hz=3200,
                output_format="wav"
            )
        ),
        PipelineStepSpec[LofiRetroInput](
            id="step_bass",
            action=bass_treble_spec,
            build_step_input=lambda p, o: BassTrebleInput(
                input_file=o["_previous"],
                bass_db=4.5,
                treble_db=-6.0,
                output_format="wav"
            )
        ),
        PipelineStepSpec[LofiRetroInput](
            id="step_overdrive",
            action=overdrive_audio_spec,
            build_step_input=lambda p, o: OverdriveAudioInput(
                input_file=o["_previous"],
                gain_db=p.overdrive_gain_db,
                colour=30,
                output_format="mp3"
            )
        )
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
PIPELINES_AUDIO_ACTIONS = collect_specs(__name__, spec_type=PipelineSpec)
__all__ = ["PIPELINES_AUDIO_ACTIONS"]