#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 10:43:08 2026

@author: hounsousamuel
"""


"""
Workbench Mediakit — Actions ImageMagick : Conversion, Compression et Optimisation Web.

Ce fichier gère le transcodage entre formats d'images (WebP, AVIF, PNG, JPG, BMP, TIFF),
la compression optimisée pour le web par réduction contrôlée de qualité,
la suppression définitive des métadonnées privées EXIF/GPS (strip) pour alléger les fichiers,
et la génération de favicons multi-tailles au format standard ICO.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, IntArg, BoolArg, PatternArg
)
from workbench.products.mediakit.specs.magick.base_spec import MagickSpec
from workbench.products.mediakit.specs.magick.base_model import (
    ConvertFormatInput, CompressQualityInput, StripMetadataInput, GenerateFaviconInput
)

MIN_MAGICK_VERSION = (7, 0)


# ─── 1. TRANSCODAGE DE FORMAT D'IMAGE ────────────────────────────────────────
convert_format_spec = MagickSpec[ConvertFormatInput](
    id="magick_convert_format",
    label="Convertir le format d'image (WebP, AVIF, PNG, JPG, TIFF, BMP)",
    input_cls=ConvertFormatInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"converted.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=f"converted.{u.output_format}")
    ]
)


# ─── 2. COMPRESSION DE QUALITÉ OPTIMISÉE ─────────────────────────────────────
compress_quality_spec = MagickSpec[CompressQualityInput](
    id="magick_compress_quality",
    label="Optimiser le poids de l'image (réglage qualité WebP/JPG de 1 à 100)",
    input_cls=CompressQualityInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"compressed.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        IntArg(flag="-quality", value=u.quality, min_value=1, max_value=100),
        PathArg(value=f"compressed.{u.output_format}")
    ]
)


# ─── 3. NETTOYAGE DES MÉTADONNÉES EXIF / GPS (STRIP) ─────────────────────────
strip_metadata_spec = MagickSpec[StripMetadataInput](
    id="magick_strip_metadata",
    label="Anonymiser l'image et alléger le poids (suppression des données EXIF et GPS)",
    input_cls=StripMetadataInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"stripped.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        BoolArg(flag="-strip", value=True),
        PathArg(value=f"stripped.{u.output_format}")
    ]
)


# ─── 4. GÉNÉRATION D'UN FAVICON ICO MULTI-RÉSOLUTIONS ────────────────────────
generate_favicon_spec = MagickSpec[GenerateFaviconInput](
    id="magick_generate_favicon",
    label="Générer un favicon web multi-tailles (.ico 16x16, 32x32, 48x48)",
    input_cls=GenerateFaviconInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template="favicon.ico",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PatternArg(flag="-define", value="icon:auto-resize=48,32,16"),
        PathArg(value="favicon.ico")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
MAGICK_CONVERT_ACTIONS = collect_specs(__name__)
__all__ = ["MAGICK_CONVERT_ACTIONS"]