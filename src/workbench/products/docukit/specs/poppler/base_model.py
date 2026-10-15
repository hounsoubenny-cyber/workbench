"""
Docukit — modèles d'entrée des actions poppler (pdfinfo, pdftotext, pdftoppm, pdfimages).
"""

from typing import Literal

from pydantic import Field, field_validator

from workbench.products.docukit.specs.qpdf.base_model import PdfSourceInput


class PdfInfoInput(PdfSourceInput):
    iso_dates: bool = Field(default=True, description="Dates au format ISO 8601 (2026-10-14T08:00:00)")


class PdfToTextInput(PdfSourceInput):
    layout: bool = Field(
        default=False,
        description="Conserver la mise en page (colonnes, tableaux) au lieu du texte brut",
    )
    first_page: int = Field(default=1, ge=1, le=100000, description="Première page à lire")
    last_page: int = Field(default=0, ge=0, le=100000, description="Dernière page à lire (0 = jusqu'à la fin)")
    page_breaks: bool = Field(default=True, description="Séparer les pages par un saut de page")

    @field_validator("last_page")
    @classmethod
    def _order(cls, v: int, info) -> int:
        first = info.data.get("first_page", 1)
        if v and v < first:
            raise ValueError("la dernière page doit être ≥ à la première")
        return v


class PdfToImageInput(PdfSourceInput):
    page: int = Field(default=1, ge=1, le=100000, description="Numéro de la page à convertir en image")
    longest_side: int = Field(
        default=1600, ge=100, le=6000,
        description="Taille de l'image en pixels (plus grand côté) — 1600 ≈ écran, 3500 ≈ impression A4",
    )
    format: Literal["png", "jpeg"] = "png"
    grayscale: bool = Field(default=False, description="Niveaux de gris")


class PdfImagesListInput(PdfSourceInput):
    first_page: int = Field(default=1, ge=1, le=100000, description="Première page à analyser")
    last_page: int = Field(default=0, ge=0, le=100000, description="Dernière page à analyser (0 = jusqu'à la fin)")

    @field_validator("last_page")
    @classmethod
    def _order(cls, v: int, info) -> int:
        first = info.data.get("first_page", 1)
        if v and v < first:
            raise ValueError("la dernière page doit être ≥ à la première")
        return v
