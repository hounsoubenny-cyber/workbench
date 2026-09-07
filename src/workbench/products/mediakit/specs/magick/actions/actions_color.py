#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:47:50 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions ImageMagick : Couleurs, Exposition et Étalonnage.

Ce fichier gère le traitement colorimétrique et l'exposition des images :
la conversion en noir et blanc pur, l'application d'un virage sépia vintage,
l'ajustement combiné de luminosité et de contraste, l'égalisation dynamique
automatique des niveaux (Auto-Level), l'inversion en négatif et la colorisation par teinte monochrome.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, PatternArg, BoolArg
)
from workbench.products.mediakit.specs.magick.base_spec import MagickSpec
from workbench.products.mediakit.specs.magick.base_model import (
    GrayscaleInput, SepiaToneInput, BrightnessContrastInput,
    AutoLevelInput, NegateColorsInput, ColorizeTintInput
)

MIN_MAGICK_VERSION = (7, 0)


# ─── 1. CONVERSION NOIR & BLANC (GRAYSCALE) ──────────────────────────────────
grayscale_spec = MagickSpec[GrayscaleInput](
    id="magick_grayscale",
    label="Convertir en Noir & Blanc (nuances de gris pures)",
    input_cls=GrayscaleInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"grayscale.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        EnumArg(flag="-colorspace", value="Gray", enum_values=["Gray"]),
        PathArg(value=f"grayscale.{u.output_format}")
    ]
)


# ─── 2. VIRAGE SÉPIA VINTAGE ─────────────────────────────────────────────────
sepia_spec = MagickSpec[SepiaToneInput](
    id="magick_sepia",
    label="Appliquer un filtre sépia rétro / vintage",
    input_cls=SepiaToneInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"sepia.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PatternArg(flag="-sepia-tone", value=f"{u.threshold_percent}%"),
        PathArg(value=f"sepia.{u.output_format}")
    ]
)


# ─── 3. AJUSTEMENT LUMINOSITÉ & CONTRASTE ────────────────────────────────────
brightness_contrast_spec = MagickSpec[BrightnessContrastInput](
    id="magick_brightness_contrast",
    label="Régler la luminosité et le contraste de l'image",
    input_cls=BrightnessContrastInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"adjusted.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PatternArg(flag="-brightness-contrast", value=f"{u.brightness}x{u.contrast}"),
        PathArg(value=f"adjusted.{u.output_format}")
    ]
)


# ─── 4. CORRECTION AUTOMATIQUE DES NIVEAUX (AUTO-LEVEL) ──────────────────────
auto_level_spec = MagickSpec[AutoLevelInput](
    id="magick_auto_level",
    label="Égaliser automatiquement les contrastes et niveaux dynamiques",
    input_cls=AutoLevelInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"auto_leveled.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        BoolArg(flag="-auto-level", value=True),
        PathArg(value=f"auto_leveled.{u.output_format}")
    ]
)


# ─── 5. NÉGATIF / INVERSION DES COULEURS ─────────────────────────────────────
negate_colors_spec = MagickSpec[NegateColorsInput](
    id="magick_negate_colors",
    label="Inverser les couleurs (effet négatif photographique)",
    input_cls=NegateColorsInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"negated.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        BoolArg(flag="-negate", value=True),
        PathArg(value=f"negated.{u.output_format}")
    ]
)


# ─── 6. TEINTE MONOCHROME (COLORIZE) ─────────────────────────────────────────
colorize_tint_spec = MagickSpec[ColorizeTintInput](
    id="magick_colorize_tint",
    label="Appliquer un filtre de teinte colorée unie (Colorize)",
    input_cls=ColorizeTintInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"tinted.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        EnumArg(flag="-fill", value=u.color, enum_values=["red", "blue", "green", "gold", "cyan", "magenta"]),
        PatternArg(flag="-colorize", value=f"{u.percent}%"),
        PathArg(value=f"tinted.{u.output_format}")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
MAGICK_COLOR_ACTIONS = collect_specs(__name__)
__all__ = ["MAGICK_COLOR_ACTIONS"]