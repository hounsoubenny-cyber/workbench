#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:48:08 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions ImageMagick : Effets Artistiques et Anonymisation.

Ce fichier gère les effets visuels appliqués aux pixels :
le flou gaussien (artistique ou anonymisation), l'accentuation de netteté des détails,
la pixellisation de censure (mosaïque), le vignettage sombre aux coins,
l'effet artistique de peinture à l'huile et l'effet dessin au fusain.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, IntArg, PatternArg
)
from workbench.products.mediakit.specs.magick.base_spec import MagickSpec
from workbench.products.mediakit.specs.magick.base_model import (
    BlurImageInput, SharpenImageInput, PixelateImageInput,
    VignetteInput, OilPaintInput, CharcoalInput
)

MIN_MAGICK_VERSION = (7, 0)


# ─── 1. FLOU GAUSSIEN (BLUR) ─────────────────────────────────────────────────
blur_spec = MagickSpec[BlurImageInput](
    id="magick_blur_gaussian",
    label="Appliquer un flou gaussien (adoucir ou anonymiser)",
    input_cls=BlurImageInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"blurred.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PatternArg(flag="-blur", value=f"{u.radius}x{u.sigma}"),
        PathArg(value=f"blurred.{u.output_format}")
    ]
)


# ─── 2. ACCENTUATION DE LA NETTETÉ (SHARPEN) ─────────────────────────────────
sharpen_spec = MagickSpec[SharpenImageInput](
    id="magick_sharpen",
    label="Augmenter la netteté et la définition des détails",
    input_cls=SharpenImageInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"sharpened.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PatternArg(flag="-sharpen", value=f"{u.radius}x{u.sigma}"),
        PathArg(value=f"sharpened.{u.output_format}")
    ]
)


# ─── 3. PIXELLISATION / MOSAÏQUE DE CENSURE ──────────────────────────────────
_SCALE_MAP = {"10%": "1000%", "5%": "2000%", "2%": "5000%"}

pixelate_spec = MagickSpec[PixelateImageInput](
    id="magick_pixelate",
    label="Pixelliser l'image (effet mosaïque de censure / anonymisation)",
    input_cls=PixelateImageInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"pixelated.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PatternArg(flag="-scale", value=u.pixel_size),
        PatternArg(flag="-scale", value=_SCALE_MAP[u.pixel_size]),
        PathArg(value=f"pixelated.{u.output_format}")
    ]
)


# ─── 4. VIGNETTAGE PHOTO ─────────────────────────────────────────────────────
vignette_spec = MagickSpec[VignetteInput](
    id="magick_vignette",
    label="Ajouter un vignettage photo (assombrissement progressif des coins)",
    input_cls=VignetteInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"vignetted.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PatternArg(flag="-vignette", value=f"{u.radius}x{u.sigma}"),
        PathArg(value=f"vignetted.{u.output_format}")
    ]
)


# ─── 5. EFFET PEINTURE À L'HUILE ─────────────────────────────────────────────
oil_paint_spec = MagickSpec[OilPaintInput](
    id="magick_oil_paint",
    label="Appliquer un effet artistique de peinture à l'huile",
    input_cls=OilPaintInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"oil_painted.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        IntArg(flag="-paint", value=u.radius, min_value=1, max_value=12),
        PathArg(value=f"oil_painted.{u.output_format}")
    ]
)


# ─── 6. EFFET DESSIN AU FUSAIN ───────────────────────────────────────────────
charcoal_spec = MagickSpec[CharcoalInput](
    id="magick_charcoal",
    label="Transformer l'image en esquisse au fusain / dessin au crayon",
    input_cls=CharcoalInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"charcoal.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        IntArg(flag="-charcoal", value=u.radius, min_value=1, max_value=10),
        PathArg(value=f"charcoal.{u.output_format}")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
MAGICK_EFFECTS_ACTIONS = collect_specs(__name__)
__all__ = ["MAGICK_EFFECTS_ACTIONS"]