#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:44:03 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions SoX : Effets Acoustiques et Traitement Spatial.

Ce fichier gère les effets audionumériques créatifs et d'immersion :
la réverbération acoustique pour simuler la résonance de pièces réelles,
l'effet d'écho et de délai temporel, le chorus multi-voix pour enrichir
le timbre sonore, et l'overdrive pour apporter une saturation harmonique chaleureuse.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, IntArg, FloatArg, PatternArg
)
from workbench.products.mediakit.specs.sox.base_spec import SoxSpec
from workbench.products.mediakit.specs.sox.base_model import (
    ReverbAudioInput, EchoAudioInput, ChorusAudioInput, OverdriveAudioInput
)

MIN_SOX_VERSION = (14, 4)

_CHORUS_PROFILES = {
    "subtle": (
        FloatArg(value=0.7), FloatArg(value=0.9),
        IntArg(value=55), FloatArg(value=0.4), FloatArg(value=0.25), FloatArg(value=2.0),
        EnumArg(value="-t", enum_values=["-t", "-s"]),
    ),
    "medium": (
        FloatArg(value=0.6), FloatArg(value=0.9),
        # Voix 1
        IntArg(value=50), FloatArg(value=0.4), FloatArg(value=0.25), FloatArg(value=2.0),
        EnumArg(value="-t", enum_values=["-t", "-s"]),
        # Voix 2
        IntArg(value=60), FloatArg(value=0.32), FloatArg(value=0.4), FloatArg(value=2.3),
        EnumArg(value="-t", enum_values=["-t", "-s"]),
    ),
    "heavy": (
        FloatArg(value=0.5), FloatArg(value=0.9),
        # Voix 1
        IntArg(value=50), FloatArg(value=0.4), FloatArg(value=0.25), FloatArg(value=2.0),
        EnumArg(value="-t", enum_values=["-t", "-s"]),
        # Voix 2
        IntArg(value=60), FloatArg(value=0.32), FloatArg(value=0.4), FloatArg(value=2.3),
        EnumArg(value="-t", enum_values=["-t", "-s"]),
        # Voix 3
        IntArg(value=40), FloatArg(value=0.3), FloatArg(value=0.3), FloatArg(value=1.5),
        EnumArg(value="-s", enum_values=["-t", "-s"]),
    ),
}


# ─── 1. RÉVERBÉRATION ACOUSTIQUE (REVERB) ───────────────────────────────────
reverb_audio_spec = SoxSpec[ReverbAudioInput](
    id="sox_reverb_audio",
    label="Appliquer une réverbération de studio (simulation d'espace acoustique)",
    input_cls=ReverbAudioInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"reverbed.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"reverbed.{u.output_format}"),
        EnumArg(value="reverb", enum_values=["reverb"]),
        IntArg(value=u.reverberance, min_value=0, max_value=100),
        IntArg(value=u.damping, min_value=0, max_value=100)
    ]
)


# ─── 2. ÉCHO / DÉLAI SPATIAL (ECHO) ──────────────────────────────────────────
echo_audio_spec = SoxSpec[EchoAudioInput](
    id="sox_echo_audio",
    label="Ajouter un effet d'écho et de délai rythmique",
    input_cls=EchoAudioInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"echoed.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"echoed.{u.output_format}"),
        EnumArg(value="echo", enum_values=["echo"]),
        FloatArg(value=0.8),               # Gain d'entrée
        FloatArg(value=0.88),              # Gain de sortie
        IntArg(value=u.delay_ms, min_value=50, max_value=2000),
        FloatArg(value=u.decay, min_value=0.1, max_value=0.9)
    ]
)


# ─── 3. CHORUS (ÉPAISSIR LE TIMBRE VOCAL / INSTRUMENTAL) ────────────────────

chorus_audio_spec = SoxSpec[ChorusAudioInput](
    id="sox_chorus_audio",
    label="Effet Chorus (épaissir le son en simulant plusieurs sources simultanées)",
    input_cls=ChorusAudioInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"chorus.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"chorus.{u.output_format}"),
        EnumArg(value="chorus", enum_values=["chorus"]),
        *_CHORUS_PROFILES[u.intensity],
    ]
)


# ─── 4. OVERDRIVE (DISTORSION ET CHALEUR HARMONIQUE) ─────────────────────────
overdrive_audio_spec = SoxSpec[OverdriveAudioInput](
    id="sox_overdrive_audio",
    label="Saturation Overdrive (ajouter de la distorsion et de la chaleur analogique)",
    input_cls=OverdriveAudioInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"overdriven.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"overdriven.{u.output_format}"),
        EnumArg(value="overdrive", enum_values=["overdrive"]),
        IntArg(value=u.gain_db, min_value=1, max_value=40),
        IntArg(value=u.colour, min_value=0, max_value=100)
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
SOX_EFFECTS_ACTIONS = collect_specs(__name__)
__all__ = ["SOX_EFFECTS_ACTIONS"]