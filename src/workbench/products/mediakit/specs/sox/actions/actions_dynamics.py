#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:43:02 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions SoX : Volume, Dynamique et Nettoyage Sonore.

Ce fichier gère le contrôle des niveaux sonores et de la dynamique :
la normalisation de crête pour éviter le clipping numérique, l'ajustement
manuel de gain en dB, la compression dynamique professionnelle (profils podcast,
maximisation du volume) et la détection/suppression automatique des silences indésirables.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, FloatArg, PatternArg, IntArg
)
from workbench.products.mediakit.specs.sox.base_spec import SoxSpec
from workbench.products.mediakit.specs.sox.base_model import (
    NormalizeGainInput, AdjustGainInput, CompandDynamicsInput, StripSilenceInput
)

MIN_SOX_VERSION = (14, 4)

_COMPAND_PROFILES = {
    "podcast_voice": (
        PatternArg(value="0.3,1"),
        PatternArg(value="6:-70,-60,-20"),
        FloatArg(value=-5.0),
        FloatArg(value=-90.0),
        FloatArg(value=0.2),
    ),
    "loudness_booster": (
        PatternArg(value="0.05,0.2"),
        PatternArg(value="6:-60,-40,-10"),
        FloatArg(value=-2.0),
        FloatArg(value=-80.0),
        FloatArg(value=0.05),
    ),
    "subtle_compression": (
        PatternArg(value="0.5,1.5"),
        PatternArg(value="6:-60,-50,-15"),
        FloatArg(value=-2.0),
        FloatArg(value=-90.0),
        FloatArg(value=0.3),
    ),
}

# ─── 1. NORMALISATION DE CRÊTE (MAXIMISER LE VOLUME SANS SATURATION) ─────────
normalize_gain_spec = SoxSpec[NormalizeGainInput](
    id="sox_normalize_gain",
    label="Normaliser la crête sonore (volume max sans écrêtage)",
    input_cls=NormalizeGainInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"normalized.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"normalized.{u.output_format}"),
        EnumArg(value="norm", enum_values=["norm"]),
        FloatArg(value=u.target_db, min_value=-24.0, max_value=0.0)
    ]
)


# ─── 2. AJUSTEMENT MANUEL DE GAIN (AMPLIFICATION / ATTÉNUATION dB) ───────────
adjust_gain_spec = SoxSpec[AdjustGainInput](
    id="sox_adjust_gain",
    label="Ajuster le gain audio manuellement (amplification ou réduction en dB)",
    input_cls=AdjustGainInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"gain_adjusted.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"gain_adjusted.{u.output_format}"),
        EnumArg(value="gain", enum_values=["gain"]),
        FloatArg(value=u.gain_db, min_value=-30.0, max_value=30.0)
    ]
)


# ─── 3. COMPRESSION DYNAMIQUE (COMPAND) ──────────────────────────────────────

compand_dynamics_spec = SoxSpec[CompandDynamicsInput](
    id="sox_compand_dynamics",
    label="Compresseur dynamique de studio (lisser les écarts de voix et d'ambiance)",
    input_cls=CompandDynamicsInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"companded.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"companded.{u.output_format}"),
        EnumArg(value="compand", enum_values=["compand"]),
        *_COMPAND_PROFILES[u.profile],
    ]
)


# ─── 4. SUPPRESSION AUTOMATIQUE DES BLANCS ET SILENCES ───────────────────────
strip_silence_spec = SoxSpec[StripSilenceInput](
    id="sox_strip_silence",
    label="Supprimer les blancs et silences au début et à la fin",
    input_cls=StripSilenceInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"trimmed_silence.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"trimmed_silence.{u.output_format}"),
        EnumArg(value="silence", enum_values=["silence"]),
        # 1. Silences au début : 1 période, durée min, seuil en %
        IntArg(value=1),
        FloatArg(value=u.min_silence_duration),
        PatternArg(value=f"{u.threshold_percent}%"),
        # 2. Silences à la fin : -1 (détection depuis la fin), durée min, seuil en %
        IntArg(value=-1),
        FloatArg(value=u.min_silence_duration),
        PatternArg(value=f"{u.threshold_percent}%"),
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
SOX_DYNAMICS_ACTIONS = collect_specs(__name__)
__all__ = ["SOX_DYNAMICS_ACTIONS"]