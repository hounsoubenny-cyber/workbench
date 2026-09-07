#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:48:27 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions ImageMagick : Incrustations, Filigranes et Bordures.

Ce fichier gère la superposition d'éléments sur l'image :
l'incrustation de logo transparent (filigrane image), l'ajout de filigrane
textuel personnalisé sécurisé avec positionnement automatique,
et l'ajout de cadres ou bordures épaisses colorées.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, IntArg, PatternArg, BoolArg
)
from workbench.products.mediakit.specs.magick.base_spec import MagickSpec
from workbench.products.mediakit.specs.magick.base_model import (
    WatermarkImageInput, WatermarkTextInput, AddBorderInput
)

MIN_MAGICK_VERSION = (7, 0)

_ANNOTATE_OFFSETS = {
    "center": "+0+0",
    "north": "+0+20",
    "south": "+0+20",
    "southeast": "+20+20",
    "southwest": "+20+20",
}

# ─── 1. INCRUSTATION DE LOGO FILIGRANE IMAGE (WATERMARK PNG) ────────────────
watermark_image_spec = MagickSpec[WatermarkImageInput](
    id="magick_watermark_image",
    label="Incruster un logo en filigrane (PNG avec transparence)",
    input_cls=WatermarkImageInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"watermarked.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=u.watermark_file, must_exist=True),
        EnumArg(
            flag="-gravity",
            value=u.position,
            enum_values=["center", "north", "south", "east", "west", "southeast", "southwest", "northeast", "northwest"]
        ),
        BoolArg(flag="-composite", value=True),
        PathArg(value=f"watermarked.{u.output_format}")
    ]
)


# ─── 2. FILIGRANE TEXTUEL SÉCURISÉ ──────────────────────────────────────────
watermark_text_spec = MagickSpec[WatermarkTextInput](
    id="magick_watermark_text",
    label="Ajouter un filigrane textuel personnalisé",
    input_cls=WatermarkTextInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"text_watermarked.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        EnumArg(
            flag="-gravity",
            value=u.position,
            enum_values=["center", "south", "southeast", "southwest", "north"]
        ),
        IntArg(flag="-pointsize", value=u.pointsize, min_value=10, max_value=150),
        EnumArg(flag="-fill", value=u.color, enum_values=["white", "black", "red", "gold", "yellow"]),
        PatternArg(flag="-annotate", value=_ANNOTATE_OFFSETS.get(u.position, "+15+15")),
        PatternArg(
            value=u.text,
            allowed_regex=r"^[a-zA-Z0-9_\- #\.\+]+$"
        ),
        PathArg(value=f"text_watermarked.{u.output_format}")
    ]
)


# ─── 3. AJOUT D'UNE BORDURE / D'UN CADRE COLORÉ ──────────────────────────────
add_border_spec = MagickSpec[AddBorderInput](
    id="magick_add_border",
    label="Ajouter un cadre ou une bordure colorée autour de l'image",
    input_cls=AddBorderInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"bordered.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        EnumArg(flag="-bordercolor", value=u.color, enum_values=["black", "white", "gray", "red", "blue", "gold"]),
        PatternArg(flag="-border", value=f"{u.thickness}x{u.thickness}"),
        PathArg(value=f"bordered.{u.output_format}")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
MAGICK_OVERLAYS_ACTIONS = collect_specs(__name__)
__all__ = ["MAGICK_OVERLAYS_ACTIONS"]