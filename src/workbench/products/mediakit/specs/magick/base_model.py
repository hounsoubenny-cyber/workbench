#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 18:24:36 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Modèles d'input Pydantic complets pour toutes les actions ImageMagick.
"""

from typing import Literal
from pydantic import BaseModel, Field
from workbench.specs.uploads import UploadRef


class BaseMagickActionInput(BaseModel):
    """Socle commun pour toute action ImageMagick avec fichier image source."""
    input_file: str = UploadRef(description="Fichier image source principal")


# ─── A. CONVERSION & OPTIMISATION WEB ───
class ConvertFormatInput(BaseMagickActionInput):
    output_format: Literal["webp", "avif", "png", "jpg", "bmp", "tiff"] = "webp"


class CompressQualityInput(BaseMagickActionInput):
    quality: int = Field(default=82, ge=1, le=100, description="Niveau de qualité JPEG/WebP (1-100)")
    output_format: Literal["webp", "jpg"] = "webp"


class StripMetadataInput(BaseMagickActionInput):
    output_format: Literal["jpg", "png", "webp"] = "jpg"


class GenerateFaviconInput(BaseMagickActionInput):
    pass


# ─── B. GÉOMÉTRIE & CADRAGE ───
class ResizeImageInput(BaseMagickActionInput):
    size: Literal["25%", "50%", "75%", "1920x1080", "1280x720", "800x600", "500x500", "256x256"] = "800x600"
    output_format: Literal["png", "jpg", "webp"] = "png"


class CropImageInput(BaseMagickActionInput):
    width: int = Field(default=400, ge=10)
    height: int = Field(default=400, ge=10)
    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)
    output_format: Literal["png", "jpg", "webp"] = "png"


class SquareThumbnailInput(BaseMagickActionInput):
    dimension: Literal["128", "256", "512", "1024"] = "512"
    output_format: Literal["png", "jpg", "webp"] = "jpg"


class CanvasExtentInput(BaseMagickActionInput):
    target_dimension: Literal["1920x1080", "1280x720", "1080x1080", "800x600"] = "1920x1080"
    background_color: Literal["black", "white", "gray", "transparent"] = "black"
    output_format: Literal["png", "jpg", "webp"] = "jpg"


class RotateImageInput(BaseMagickActionInput):
    degrees: Literal["90", "180", "270"] = "90"
    output_format: Literal["png", "jpg", "webp"] = "png"


class FlipFlopInput(BaseMagickActionInput):
    direction: Literal["horizontal", "vertical"] = "horizontal"
    output_format: Literal["png", "jpg", "webp"] = "png"


class AutoOrientInput(BaseMagickActionInput):
    output_format: Literal["jpg", "png", "webp"] = "jpg"


# ─── C. COULEURS & EXPOSITION ───
class GrayscaleInput(BaseMagickActionInput):
    output_format: Literal["png", "jpg", "webp"] = "png"


class SepiaToneInput(BaseMagickActionInput):
    threshold_percent: int = Field(default=80, ge=30, le=95, description="Intensité du sépia (80% recommandé)")
    output_format: Literal["jpg", "png", "webp"] = "jpg"


class BrightnessContrastInput(BaseMagickActionInput):
    brightness: int = Field(default=10, ge=-50, le=50, description="Ajustement luminosité (-50 à +50)")
    contrast: int = Field(default=15, ge=-50, le=50, description="Ajustement contraste (-50 à +50)")
    output_format: Literal["jpg", "png", "webp"] = "jpg"


class AutoLevelInput(BaseMagickActionInput):
    output_format: Literal["jpg", "png", "webp"] = "jpg"


class NegateColorsInput(BaseMagickActionInput):
    output_format: Literal["png", "jpg", "webp"] = "png"


class ColorizeTintInput(BaseMagickActionInput):
    color: Literal["red", "blue", "green", "gold", "cyan", "magenta"] = "blue"
    percent: int = Field(default=35, ge=5, le=90, description="Pourcentage de teinte")
    output_format: Literal["jpg", "png", "webp"] = "jpg"


# ─── D. FILTRES & EFFETS ───
class BlurImageInput(BaseMagickActionInput):
    radius: int = Field(default=0, ge=0, le=20)
    sigma: int = Field(default=8, ge=1, le=50)
    output_format: Literal["png", "jpg", "webp"] = "png"


class SharpenImageInput(BaseMagickActionInput):
    radius: int = Field(default=0, ge=0, le=10)
    sigma: int = Field(default=3, ge=1, le=20)
    output_format: Literal["png", "jpg", "webp"] = "png"


class PixelateImageInput(BaseMagickActionInput):
    pixel_size: Literal["10%", "5%", "2%"] = "5%"
    output_format: Literal["png", "jpg", "webp"] = "jpg"


class VignetteInput(BaseMagickActionInput):
    radius: int = Field(default=0, ge=0, le=50)
    sigma: int = Field(default=20, ge=5, le=100)
    output_format: Literal["jpg", "png", "webp"] = "jpg"


class OilPaintInput(BaseMagickActionInput):
    radius: int = Field(default=4, ge=1, le=12, description="Rayon des coups de pinceau")
    output_format: Literal["jpg", "png", "webp"] = "jpg"


class CharcoalInput(BaseMagickActionInput):
    radius: int = Field(default=3, ge=1, le=10)
    output_format: Literal["jpg", "png", "webp"] = "jpg"


# ─── E. INCRUSTATIONS & CADRES ───
class WatermarkImageInput(BaseMagickActionInput):
    watermark_file: str = UploadRef(description="Image PNG du logo transparent")
    position: Literal["center", "north", "south", "east", "west", "southeast", "southwest", "northeast", "northwest"] = "southeast"
    output_format: Literal["png", "jpg", "webp"] = "png"


class WatermarkTextInput(BaseMagickActionInput):
    text: str = Field(default="COPYRIGHT", max_length=50)
    position: Literal["center", "south", "southeast", "southwest", "north"] = "southeast"
    pointsize: int = Field(default=28, ge=10, le=150)
    color: Literal["white", "black", "red", "gold", "yellow"] = "white"
    output_format: Literal["jpg", "png", "webp"] = "jpg"


class AddBorderInput(BaseMagickActionInput):
    thickness: int = Field(default=15, ge=1, le=100)
    color: Literal["black", "white", "gray", "red", "blue", "gold"] = "black"
    output_format: Literal["png", "jpg", "webp"] = "png"