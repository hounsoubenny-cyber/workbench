#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:43:30 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions SoX : Découpe, Timing, Vitesse et Tonalité.

Ce fichier gère la manipulation temporelle et spectrale des fichiers audio :
la découpe de segments précis (trim), l'application de fondus progressifs (fade in/out),
l'insertion de silences en début/fin de piste (pad), la modification indépendante du tempo
(accélérer/ralentir sans altérer la voix), le changement de tonalité (pitch sans changer la vitesse),
et l'inversion complète du sens de lecture audio (reverse).
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, FloatArg, IntArg
)
from workbench.products.mediakit.specs.sox.base_spec import SoxSpec
from workbench.products.mediakit.specs.sox.base_model import (
    TrimAudioInput, FadeAudioInput, PadSilenceInput,
    ChangeTempoInput, ChangePitchInput, ReverseAudioInput
)

MIN_SOX_VERSION = (14, 4)


# ─── 1. DÉCOUPE DE SEGMENT AUDIO (TRIM) ──────────────────────────────────────
trim_audio_spec = SoxSpec[TrimAudioInput](
    id="sox_trim_audio",
    label="Découper un extrait audio (point de départ et durée)",
    input_cls=TrimAudioInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"trimmed.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"trimmed.{u.output_format}"),
        EnumArg(value="trim", enum_values=["trim"]),
        FloatArg(value=u.start_seconds, min_value=0.0),
        FloatArg(value=u.duration_seconds, min_value=0.01)
    ]
)


# ─── 2. FONDUS ENTRANT ET SORTANT (FADE IN / OUT) ────────────────────────────
def _build_sox_fade_args(u: FadeAudioInput) -> list:
    args = [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"faded.{u.output_format}"),
        EnumArg(value="fade", enum_values=["fade"]),
        EnumArg(value=u.curve, enum_values=["t", "q", "h"]),
        FloatArg(value=u.fade_in_s, min_value=0.0),
    ]
    if u.fade_out_s > 0:
        args.extend([
            FloatArg(value=0.0),             # Stop-time calculé depuis la fin
            FloatArg(value=u.fade_out_s, min_value=0.0)
        ])
    return args


fade_audio_spec = SoxSpec[FadeAudioInput](
    id="sox_fade_audio",
    label="Appliquer des fondus progressifs en entrée et sortie (Fade in/out)",
    input_cls=FadeAudioInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"faded.{u.output_format}",
    build_args=_build_sox_fade_args
)


# ─── 3. AJOUTER DES SILENCES EN DÉBUT / FIN (PAD) ────────────────────────────
pad_silence_spec = SoxSpec[PadSilenceInput](
    id="sox_pad_silence",
    label="Ajouter des silences au début ou à la fin d'une piste audio",
    input_cls=PadSilenceInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"padded.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"padded.{u.output_format}"),
        EnumArg(value="pad", enum_values=["pad"]),
        FloatArg(value=u.pad_start_s, min_value=0.0),
        FloatArg(value=u.pad_end_s, min_value=0.0)
    ]
)


# ─── 4. MODIFIER LE TEMPO SANS CHANGER LA HAUTEUR (TEMPO) ────────────────────
change_tempo_spec = SoxSpec[ChangeTempoInput](
    id="sox_change_tempo",
    label="Accélérer ou ralentir l'audio sans modifier la tonalité (garder la voix naturelle)",
    input_cls=ChangeTempoInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"tempo_adjusted.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"tempo_adjusted.{u.output_format}"),
        EnumArg(value="tempo", enum_values=["tempo"]),
        FloatArg(value=u.factor, min_value=0.5, max_value=2.5)
    ]
)


# ─── 5. MODIFIER LA TONALITÉ SANS CHANGER LE TEMPO (PITCH) ───────────────────
change_pitch_spec = SoxSpec[ChangePitchInput](
    id="sox_change_pitch",
    label="Modifier la tonalité / hauteur de voix (sans altérer la vitesse)",
    input_cls=ChangePitchInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"pitch_adjusted.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"pitch_adjusted.{u.output_format}"),
        EnumArg(value="pitch", enum_values=["pitch"]),
        IntArg(value=u.cents, min_value=-1200, max_value=1200)
    ]
)


# ─── 6. LECTURE INVERSÉE (REVERSE) ───────────────────────────────────────────
reverse_audio_spec = SoxSpec[ReverseAudioInput](
    id="sox_reverse_audio",
    label="Inverser le sens de lecture du fichier audio (effet miroir / rewind)",
    input_cls=ReverseAudioInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"reversed.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"reversed.{u.output_format}"),
        EnumArg(value="reverse", enum_values=["reverse"])
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
SOX_TIMING_ACTIONS = collect_specs(__name__)
__all__ = ["SOX_TIMING_ACTIONS"]