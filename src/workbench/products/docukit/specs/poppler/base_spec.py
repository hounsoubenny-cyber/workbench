"""
Docukit — specs de base poppler.

Chaque utilitaire poppler est un binaire distinct (donc une `tool` distincte
côté moteur, avec son propre marqueur de version). Tous impriment leur version
sur stderr avec `-v`.
"""

from typing import ClassVar

from workbench.specs.specs import InputT
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
from workbench.products.docukit.specs.base import DocukitSpec

# `-scale-to` et `-singlefile` (pdftoppm) existent depuis poppler 0.2x ;
# on exige 0.86 (Ubuntu 20.04) comme plancher raisonnable.
MIN_POPPLER_VERSION = (0, 86)


def _cfg(tool: str) -> BinVersionCheckerConfig:
    return BinVersionCheckerConfig(cmd="-v", marker=f"{tool} version", tool_name=tool)


PDFINFO_CONFIG = _cfg("pdfinfo")
PDFTOTEXT_CONFIG = _cfg("pdftotext")
PDFTOPPM_CONFIG = _cfg("pdftoppm")
PDFIMAGES_CONFIG = _cfg("pdfimages")


class _PopplerSpec(DocukitSpec[InputT]):
    min_version: tuple | None = MIN_POPPLER_VERSION
    upload_kind: ClassVar[str | None] = "pdf"


class PdfInfoSpec(_PopplerSpec[InputT]):
    tool: str = "pdfinfo"
    binary_config: BinVersionCheckerConfig = PDFINFO_CONFIG


class PdfToTextSpec(_PopplerSpec[InputT]):
    tool: str = "pdftotext"
    binary_config: BinVersionCheckerConfig = PDFTOTEXT_CONFIG


class PdfToPpmSpec(_PopplerSpec[InputT]):
    tool: str = "pdftoppm"
    binary_config: BinVersionCheckerConfig = PDFTOPPM_CONFIG


class PdfImagesSpec(_PopplerSpec[InputT]):
    tool: str = "pdfimages"
    binary_config: BinVersionCheckerConfig = PDFIMAGES_CONFIG
