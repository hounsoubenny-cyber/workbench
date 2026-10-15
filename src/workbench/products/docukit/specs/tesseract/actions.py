"""
Docukit — actions tesseract : OCR (image -> texte, image -> PDF recherchable).
"""

from pathlib import Path
from typing import ClassVar

from workbench.specs.specs import InputT
from workbench.core.subprocess.wb_subprocess_types import EnumArg, PathArg
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
from workbench.products.docukit.specs.base import DocukitSpec, InvalidDocumentError
from workbench.products.docukit.specs.common import Out, ordered
from workbench.products.docukit.specs.tesseract.base_model import (
    OcrBaseInput, OcrTextInput, OcrSearchablePdfInput, OcrLanguage, OcrPageMode,
)
from workbench.products.docukit.dk_utils.tools import tesseract_languages
from typing import get_args

TESSERACT_CONFIG = BinVersionCheckerConfig(
    cmd="--version", marker="tesseract", tool_name="tesseract"
)


class TesseractSpec(DocukitSpec[InputT]):
    tool: str = "tesseract"
    binary_config: BinVersionCheckerConfig = TESSERACT_CONFIG
    min_version: tuple | None = (4, 0)
    upload_kind: ClassVar[str | None] = "image"

    def extra_validation(self, user_input: OcrBaseInput, workdir: Path) -> None:
        """Échoue proprement si le modèle de langue n'est pas installé."""
        installed = tesseract_languages()
        missing = [c for c in user_input.language.split("+") if c not in installed]
        if missing:
            raise InvalidDocumentError(
                f"modèle OCR manquant : {', '.join(missing)}. "
                f"Langues installées : {', '.join(sorted(installed)) or 'aucune'}. "
                "Installez le paquet de langue (ex : tesseract-ocr-fra)."
            )


_LANGS = list(get_args(OcrLanguage))
_MODES = list(get_args(OcrPageMode))


def _common_args(u: OcrBaseInput, output_root: str, *trailing) -> list:
    # Syntaxe tesseract : <image> <racine de sortie> [options] [format].
    # tesseract ajoute lui-même l'extension (.txt / .pdf) à la racine.
    return [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=output_root),
        EnumArg(flag="-l", value=u.language, enum_values=_LANGS),
        EnumArg(flag="--psm", value=u.page_mode, enum_values=_MODES),
        *trailing,
    ]


ocr_text_spec = TesseractSpec[OcrTextInput](
    id="tesseract_ocr_text",
    label="Lire le texte d'une image (OCR)",
    description="Reconnaissance de caractères : image ou scan -> fichier texte.",
    input_cls=OcrTextInput,
    output_filename_template=Out.OCR_TEXT,
    build_args=lambda u: _common_args(u, "ocr_text"),
)

ocr_pdf_spec = TesseractSpec[OcrSearchablePdfInput](
    id="tesseract_searchable_pdf",
    label="Transformer une image en PDF recherchable",
    description="OCR : produit un PDF dont le texte est sélectionnable et recherchable.",
    input_cls=OcrSearchablePdfInput,
    output_filename_template=Out.OCR_PDF,
    build_args=lambda u: _common_args(
        u, "ocr_searchable", EnumArg(value="pdf", enum_values=["pdf"])
    ),
)

TESSERACT_ACTIONS = ordered(ocr_text_spec, ocr_pdf_spec)
__all__ = ["TESSERACT_ACTIONS"]
