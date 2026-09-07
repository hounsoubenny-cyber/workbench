#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 10:43:08 2026

@author: hounsousamuel
"""


"""
Workbench Mediakit — Actions SoX : Formats, Échantillonnage, Résolution et Canaux.

Ce fichier gère le transcodage entre conteneurs audio (MP3, WAV, FLAC, OGG),
la conversion de fréquence d'échantillonnage haute fidélité (44.1kHz, 48kHz, 16kHz pour Whisper/IA),
la gestion du nombre de canaux (mixage Stéréo vers Mono et vice-versa, extraction de canal isolé)
et la modification de la résolution binaire (16, 24 ou 32 bits avec dither).
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import PathArg, EnumArg
from workbench.products.mediakit.specs.sox.base_spec import SoxSpec
from workbench.products.mediakit.specs.sox.base_model import (
    ConvertAudioInput, ResampleAudioInput, ChannelsRemixInput,
    ExtractChannelInput, ChangeBitDepthInput
)

MIN_SOX_VERSION = (14, 4)


# ─── 1. TRANSCODAGE DE FORMAT AUDIO ──────────────────────────────────────────
convert_audio_spec = SoxSpec[ConvertAudioInput](
    id="sox_convert_format",
    label="Transcoder le format audio (MP3, WAV, FLAC, OGG)",
    input_cls=ConvertAudioInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"converted.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"converted.{u.output_format}")
    ]
)


# ─── 2. RÉÉCHANTILLONNAGE DE FRÉQUENCE (SAMPLE RATE) ─────────────────────────
resample_audio_spec = SoxSpec[ResampleAudioInput](
    id="sox_resample_rate",
    label="Modifier la fréquence d'échantillonnage (48kHz, 44.1kHz, 16kHz...)",
    input_cls=ResampleAudioInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"resampled.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"resampled.{u.output_format}"),
        EnumArg(value="rate", enum_values=["rate"]),
        EnumArg(value=u.sample_rate, enum_values=["48000", "44100", "22050", "16000", "8000"])
    ]
)


# ─── 3. CONVERSION DE CANAUX (STÉRÉO / MONO) ─────────────────────────────────
channels_remix_spec = SoxSpec[ChannelsRemixInput](
    id="sox_channels_remix",
    label="Changer le nombre de canaux (Stéréo vers Mono ou Mono vers Stéréo)",
    input_cls=ChannelsRemixInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"channels_remixed.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        EnumArg(flag="-c", value=u.channels, enum_values=["1", "2"]),
        PathArg(value=f"channels_remixed.{u.output_format}")
    ]
)


# ─── 4. EXTRAIRE UN CANAL ISOLÉ (GAUCHE OU DROIT) ────────────────────────────
extract_channel_spec = SoxSpec[ExtractChannelInput](
    id="sox_extract_channel",
    label="Extraire un seul canal audio isolé (Gauche ou Droit)",
    input_cls=ExtractChannelInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"channel_{u.channel}.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"channel_{u.channel}.{u.output_format}"),
        EnumArg(value="remix", enum_values=["remix"]),
        EnumArg(value="1" if u.channel == "left" else "2", enum_values=["1", "2"])
    ]
)


# ─── 5. MODIFIER LA RÉSOLUTION BINAIRE (BIT DEPTH) ───────────────────────────
change_bit_depth_spec = SoxSpec[ChangeBitDepthInput](
    id="sox_change_bit_depth",
    label="Modifier la profondeur de quantification binaire (16, 24 ou 32 bits)",
    input_cls=ChangeBitDepthInput,
    validate_arg=True,
    min_version=MIN_SOX_VERSION,
    output_filename_template=lambda u: f"quantized_{u.bit_depth}bit.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        EnumArg(flag="-b", value=u.bit_depth, enum_values=["16", "24", "32"]),
        PathArg(value=f"quantized_{u.bit_depth}bit.{u.output_format}")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
SOX_CONVERT_ACTIONS = collect_specs(__name__)
__all__ = ["SOX_CONVERT_ACTIONS"]