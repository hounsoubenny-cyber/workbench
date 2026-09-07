#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:43:43 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions SoX : Égalisation et Filtres Fréquentiels.

Ce fichier gère le filtrage fréquentiel et l'égalisation sonore :
l'ajustement rapide des basses et des aigus (Bass & Treble en dB),
le filtrage passe-bas pour adoucir les sons agressifs, le filtrage passe-haut
pour supprimer les vibrations sourdes et bruits de micro (rumble), ainsi que
l'égalisation paramétrique chirurgicale (fréquence, largeur de bande et gain).
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, FloatArg, IntArg
)
from workbench.products.mediakit.specs.sox.base_spec import SoxSpec
from workbench.products.mediakit.specs.sox.base_model import (
    BassTrebleInput, LowPassFilterInput, HighPassFilterInput, ParametricEqualizerInput
)

MIN_SOX_VERSION = (14, 4)


# ─── 1. ÉGALISEUR BASS & TREBLE RAPIDE ───────────────────────────────────────
bass_treble_spec = SoxSpec[BassTrebleInput](
    id="sox_bass_treble",
    label="Ajuster les basses et les aigus (booster ou couper en dB)",
    input_cls=BassTrebleInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"eq_bass_treble.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"eq_bass_treble.{u.output_format}"),
        EnumArg(value="bass", enum_values=["bass"]),
        FloatArg(value=u.bass_db, min_value=-20.0, max_value=20.0),
        EnumArg(value="treble", enum_values=["treble"]),
        FloatArg(value=u.treble_db, min_value=-20.0, max_value=20.0)
    ]
)


# ─── 2. FILTRE PASSE-BAS (LOW-PASS) ──────────────────────────────────────────
lowpass_spec = SoxSpec[LowPassFilterInput](
    id="sox_lowpass_filter",
    label="Filtre passe-bas (couper les hautes fréquences stridentes)",
    input_cls=LowPassFilterInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"lowpassed.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"lowpassed.{u.output_format}"),
        EnumArg(value="lowpass", enum_values=["lowpass"]),
        IntArg(value=u.cutoff_hz, min_value=200, max_value=20000)
    ]
)


# ─── 3. FILTRE PASSE-HAUT (HIGH-PASS) ─────────────────────────────────────────
highpass_spec = SoxSpec[HighPassFilterInput](
    id="sox_highpass_filter",
    label="Filtre passe-haut (supprimer les bruits sourds et vibrations micro < 100 Hz)",
    input_cls=HighPassFilterInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"highpassed.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"highpassed.{u.output_format}"),
        EnumArg(value="highpass", enum_values=["highpass"]),
        IntArg(value=u.cutoff_hz, min_value=20, max_value=5000)
    ]
)


# ─── 4. ÉGALISEUR PARAMÉTRIQUE DE PRÉCISION ──────────────────────────────────
parametric_equalizer_spec = SoxSpec[ParametricEqualizerInput](
    id="sox_parametric_equalizer",
    label="Égaliseur paramétrique chirurgical (fréquence centrale, largeur et gain)",
    input_cls=ParametricEqualizerInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"parametric_eq.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"parametric_eq.{u.output_format}"),
        EnumArg(value="equalizer", enum_values=["equalizer"]),
        IntArg(value=u.frequency_hz, min_value=40, max_value=16000),
        IntArg(value=u.bandwidth_hz, min_value=10, max_value=4000),
        FloatArg(value=u.gain_db, min_value=-24.0, max_value=24.0)
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
SOX_EQ_ACTIONS = collect_specs(__name__)
__all__ = ["SOX_EQ_ACTIONS"]