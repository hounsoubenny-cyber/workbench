#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:47:35 2026

@author: hounsousamuel
"""


"""
Workbench Mediakit — Actions ImageMagick : Géométrie, Cadrage et Dimensions.

Ce fichier gère toutes les manipulations spatiales et dimensionnelles :
le redimensionnement par pourcentages ou résolutions fixes, le rognage libre (crop),
la création de miniatures carrées parfaites pour profils/avatars, l'extension de toile
avec bandes de couleur (letterbox), la rotation angulaire, l'effet miroir (flip/flop)
et la correction automatique d'orientation basée sur les capteurs gyroscopiques EXIF.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, PatternArg, BoolArg
)
from workbench.products.mediakit.specs.magick.base_spec import MagickSpec
from workbench.products.mediakit.specs.magick.base_model import (
    ResizeImageInput, CropImageInput, SquareThumbnailInput,
    CanvasExtentInput, RotateImageInput, FlipFlopInput, AutoOrientInput
)

MIN_MAGICK_VERSION = (7, 0)


# ─── 1. REDIMENSIONNEMENT STANDARD ───────────────────────────────────────────
resize_image_spec = MagickSpec[ResizeImageInput](
    id="magick_resize_image",
    label="Redimensionner l'image (pourcentages ou dimensions cibles)",
    input_cls=ResizeImageInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"resized.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        EnumArg(
            flag="-resize",
            value=u.size,
            enum_values=["25%", "50%", "75%", "1920x1080", "1280x720", "800x600", "500x500", "256x256"]
        ),
        PathArg(value=f"resized.{u.output_format}")
    ]
)


# ─── 2. ROGNAGE RECTANGULAIRE (CROP MANUEL) ──────────────────────────────────
crop_image_spec = MagickSpec[CropImageInput](
    id="magick_crop_image",
    label="Rogner l'image (extraire une zone WxH+X+Y)",
    input_cls=CropImageInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"cropped.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PatternArg(flag="-crop", value=f"{u.width}x{u.height}+{u.x}+{u.y}"),
        BoolArg(flag="+repage", value=True),
        PathArg(value=f"cropped.{u.output_format}")
    ]
)


# ─── 3. MINIATURE CARRÉE AVATAR (SMART CROP CENTRÉ) ──────────────────────────
square_thumbnail_spec = MagickSpec[SquareThumbnailInput](
    id="magick_square_thumbnail",
    label="Créer une miniature carrée centrée (Avatar/Profil sans déformation)",
    input_cls=SquareThumbnailInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"thumbnail_square.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PatternArg(flag="-resize", value=f"{u.dimension}x{u.dimension}^"),
        EnumArg(flag="-gravity", value="center", enum_values=["center"]),
        PatternArg(flag="-extent", value=f"{u.dimension}x{u.dimension}"),
        PathArg(value=f"thumbnail_square.{u.output_format}")
    ]
)


# ─── 4. EXTENSION DE TOILE / LETTERBOX AVEC FOND ─────────────────────────────
canvas_extent_spec = MagickSpec[CanvasExtentInput](
    id="magick_canvas_extent",
    label="Étendre la toile et ajouter des bandes colorées (Letterbox)",
    input_cls=CanvasExtentInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"canvas_padded.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        EnumArg(flag="-background", value=u.background_color, enum_values=["black", "white", "gray", "transparent"]),
        EnumArg(flag="-gravity", value="center", enum_values=["center"]),
        PatternArg(flag="-extent", value=u.target_dimension),
        PathArg(value=f"canvas_padded.{u.output_format}")
    ]
)


# ─── 5. ROTATION ANGULAIRE ───────────────────────────────────────────────────
rotate_image_spec = MagickSpec[RotateImageInput](
    id="magick_rotate_image",
    label="Faire pivoter l'image (90°, 180°, 270°)",
    input_cls=RotateImageInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"rotated.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        EnumArg(flag="-rotate", value=u.degrees, enum_values=["90", "180", "270"]),
        PathArg(value=f"rotated.{u.output_format}")
    ]
)


# ─── 6. EFFET MIROIR (FLIP / FLOP) ───────────────────────────────────────────
flip_flop_spec = MagickSpec[FlipFlopInput](
    id="magick_flip_flop",
    label="Appliquer un effet miroir (horizontal ou vertical)",
    input_cls=FlipFlopInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"mirrored.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        BoolArg(flag="-flop" if u.direction == "horizontal" else "-flip", value=True),
        PathArg(value=f"mirrored.{u.output_format}")
    ]
)


# ─── 7. CORRECTION AUTOMATIQUE DE L'ORIENTATION (EXIF) ───────────────────────
auto_orient_spec = MagickSpec[AutoOrientInput](
    id="magick_auto_orient",
    label="Corriger automatiquement l'orientation selon les métadonnées de l'appareil",
    input_cls=AutoOrientInput,
    validate_arg=True,
    min_version=MIN_MAGICK_VERSION,
    output_filename_template=lambda u: f"oriented.{u.output_format}",
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        BoolArg(flag="-auto-orient", value=True),
        PathArg(value=f"oriented.{u.output_format}")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
MAGICK_GEOMETRY_ACTIONS = collect_specs(__name__)
__all__ = ["MAGICK_GEOMETRY_ACTIONS"]