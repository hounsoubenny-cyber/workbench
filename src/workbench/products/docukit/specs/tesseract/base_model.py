"""
Docukit — modèles d'entrée des actions tesseract (OCR).
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from workbench.specs.uploads import UploadRef
from workbench.products.docukit.specs.common import IMAGE_EXTS, check_filename

OcrLanguage = Literal["fra", "eng", "fra+eng", "eng+fra"]
# Modes de segmentation de page (--psm), parmi les plus utiles :
#   3 = automatique (défaut) · 4 = une colonne · 6 = un bloc de texte · 11 = texte épars
OcrPageMode = Literal["3", "4", "6", "11"]


class OcrBaseInput(BaseModel):
    input_file: str = UploadRef(description="Image à analyser (PNG, JPEG, TIFF, BMP, GIF, WebP)")
    language: OcrLanguage = Field(
        default="fra",
        description="Langue du texte (le modèle de langue doit être installé sur la machine)",
    )
    page_mode: OcrPageMode = Field(
        default="3",
        description="3 = automatique · 4 = une seule colonne · 6 = un seul bloc de texte · 11 = texte épars",
    )

    @field_validator("input_file")
    @classmethod
    def _image_name(cls, v: str) -> str:
        return check_filename(v, IMAGE_EXTS)


class OcrTextInput(OcrBaseInput):
    pass


class OcrSearchablePdfInput(OcrBaseInput):
    pass
