"""
Docukit — modèles d'entrée Pydantic des actions qpdf.

Chaque modèle EST le formulaire affiché à l'utilisateur (introspecté par
`model_to_dict`). Les noms de champs sont donc des API : ne pas les renommer
à la légère. Les types restent volontairement simples (str / int / bool /
Literal / list[str]) pour que l'introspection produise des types propres.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from workbench.specs.uploads import UploadRef
from workbench.products.docukit.specs.common import (
    PDF_EXTS, PAGE_RANGE_HELP,
    check_filename, check_filenames, check_page_range, check_password,
)


class PdfSourceInput(BaseModel):
    """Socle commun : un PDF source."""

    input_file: str = UploadRef(description="Document PDF source")

    @field_validator("input_file")
    @classmethod
    def _pdf_name(cls, v: str) -> str:
        return check_filename(v, PDF_EXTS)


# ─── A. ORGANISER LES PAGES ──────────────────────────────────────────────────

class MergeInput(BaseModel):
    inputs: list[str] = UploadRef(
        description="PDF à fusionner, dans l'ordre", min_length=2, max_length=50
    )

    @field_validator("inputs")
    @classmethod
    def _pdf_names(cls, v: list[str]) -> list[str]:
        return check_filenames(v, PDF_EXTS)


class ExtractPagesInput(PdfSourceInput):
    pages: str = Field(
        default="1", max_length=200,
        description=f"Pages à conserver — {PAGE_RANGE_HELP}",
    )

    @field_validator("pages")
    @classmethod
    def _range(cls, v: str) -> str:
        return check_page_range(v)


class DeletePagesInput(PdfSourceInput):
    pages: str = Field(
        default="1", max_length=200,
        description=f"Pages à supprimer — {PAGE_RANGE_HELP}",
    )

    @field_validator("pages")
    @classmethod
    def _range(cls, v: str) -> str:
        return check_page_range(v, allow_exclusion=False)


class ReversePagesInput(PdfSourceInput):
    pass


# ─── B. ÉDITER ───────────────────────────────────────────────────────────────

class RotateInput(PdfSourceInput):
    angle: Literal["90", "180", "270"] = Field(
        default="90", description="Rotation dans le sens des aiguilles d'une montre (degrés)"
    )
    pages: str = Field(
        default="1-z", max_length=200,
        description=f"Pages concernées — {PAGE_RANGE_HELP}",
    )

    @field_validator("pages")
    @classmethod
    def _range(cls, v: str) -> str:
        return check_page_range(v)


class StampInput(PdfSourceInput):
    stamp_file: str = UploadRef(
        description="PDF du tampon / filigrane (sa première page est répétée sur chaque page)"
    )
    mode: Literal["overlay", "underlay"] = Field(
        default="overlay",
        description="overlay = par-dessus le contenu ; underlay = derrière le contenu",
    )
    pages: str = Field(
        default="1-z", max_length=200,
        description=f"Pages à tamponner — {PAGE_RANGE_HELP}",
    )

    @field_validator("stamp_file")
    @classmethod
    def _stamp_name(cls, v: str) -> str:
        return check_filename(v, PDF_EXTS)

    @field_validator("pages")
    @classmethod
    def _range(cls, v: str) -> str:
        return check_page_range(v)


# ─── C. SÉCURITÉ ─────────────────────────────────────────────────────────────

class ProtectInput(PdfSourceInput):
    password: str = Field(description="Mot de passe d'ouverture du document (chiffrement AES-256)")
    owner_password: str = Field(
        default="",
        description=(
            "Mot de passe propriétaire, pour lever les restrictions ci-dessous. "
            "Laissez vide pour réutiliser le mot de passe d'ouverture."
        ),
    )
    allow_print: bool = Field(default=True, description="Autoriser l'impression")
    allow_copy: bool = Field(default=True, description="Autoriser la copie du texte et des images")
    allow_modify: bool = Field(default=False, description="Autoriser la modification du document")

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return check_password(v)

    @field_validator("owner_password")
    @classmethod
    def _owner_pw(cls, v: str) -> str:
        return check_password(v, "mot de passe propriétaire") if v else v


class UnlockInput(PdfSourceInput):
    password: str = Field(description="Mot de passe actuel du document")

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return check_password(v)


# ─── D. MAINTENANCE ──────────────────────────────────────────────────────────

class CheckInput(PdfSourceInput):
    pass


class RepairInput(PdfSourceInput):
    pass


class OptimizeInput(PdfSourceInput):
    web_optimized: bool = Field(
        default=False,
        description="Affichage rapide sur le web : la 1re page s'affiche avant la fin du téléchargement",
    )
