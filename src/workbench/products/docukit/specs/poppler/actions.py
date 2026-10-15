"""
Docukit — actions poppler : lire et extraire (infos, texte, page en image, liste des images).
"""

from workbench.core.subprocess.wb_subprocess_types import (
    EnumArg, IntArg, PathArg,
)
from workbench.products.docukit.specs.common import Out, flag, ordered
from workbench.products.docukit.specs.poppler.base_spec import (
    PdfInfoSpec, PdfToTextSpec, PdfToPpmSpec, PdfImagesSpec,
)
from workbench.products.docukit.specs.poppler.base_model import (
    PdfInfoInput, PdfToTextInput, PdfToImageInput, PdfImagesListInput,
)

_MAX_PAGE = 100000


def _page_range_args(first: int, last: int) -> list:
    """`-f N [-l M]` : `last == 0` signifie « jusqu'à la fin »."""
    args = [IntArg(flag="-f", value=first, min_value=1, max_value=_MAX_PAGE)]
    if last:
        args.append(IntArg(flag="-l", value=last, min_value=first, max_value=_MAX_PAGE))
    return args


pdf_info_spec = PdfInfoSpec[PdfInfoInput](
    id="pdfinfo_summary",
    label="Afficher les informations du PDF",
    description="Titre, auteur, nombre de pages, taille, version, chiffrement, dates…",
    input_cls=PdfInfoInput,
    output_filename_template=Out.INFO,
    capture_stdout=True,
    build_args=lambda u: [
        *([flag("-isodates")] if u.iso_dates else []),
        PathArg(value=u.input_file, must_exist=True),
    ],
)


def _text_args(u: PdfToTextInput) -> list:
    return [
        *([flag("-layout")] if u.layout else []),
        *([] if u.page_breaks else [flag("-nopgbrk")]),
        *_page_range_args(u.first_page, u.last_page),
        EnumArg(flag="-enc", value="UTF-8", enum_values=["UTF-8"]),
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=Out.TEXT),
    ]


pdf_to_text_spec = PdfToTextSpec[PdfToTextInput](
    id="pdftotext_extract",
    label="Extraire le texte du PDF",
    description=(
        "Récupère le texte sélectionnable d'un PDF (fichier .txt, UTF-8). "
        "Pour un PDF scanné (image), utilisez plutôt l'OCR."
    ),
    input_cls=PdfToTextInput,
    output_filename_template=Out.TEXT,
    build_args=_text_args,
)


def _image_filename(u: PdfToImageInput) -> str:
    return Out.PAGE_PNG if u.format == "png" else Out.PAGE_JPG


def _image_args(u: PdfToImageInput) -> list:
    # `-scale-to N` borne le plus grand côté en pixels QUELLE QUE SOIT la taille
    # physique de la page : protège contre les pages géantes (« bombes » de
    # rendu) qu'un réglage en DPI laisserait exploser en mémoire.
    return [
        flag(f"-{u.format}"),
        IntArg(flag="-scale-to", value=u.longest_side, min_value=100, max_value=6000),
        IntArg(flag="-f", value=u.page, min_value=1, max_value=_MAX_PAGE),
        IntArg(flag="-l", value=u.page, min_value=1, max_value=_MAX_PAGE),
        flag("-singlefile"),
        *([flag("-gray")] if u.grayscale else []),
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value="page"),  # pdftoppm ajoute lui-même .png / .jpg
    ]


pdf_to_image_spec = PdfToPpmSpec[PdfToImageInput](
    id="pdftoppm_render_page",
    label="Convertir une page en image",
    description="Transforme une page du PDF en image PNG ou JPEG.",
    input_cls=PdfToImageInput,
    output_filename_template=_image_filename,
    build_args=_image_args,
)

pdf_images_list_spec = PdfImagesSpec[PdfImagesListInput](
    id="pdfimages_list",
    label="Lister les images contenues dans le PDF",
    description="Tableau des images intégrées (page, dimensions, résolution, poids).",
    input_cls=PdfImagesListInput,
    output_filename_template=Out.IMAGES_LIST,
    capture_stdout=True,
    build_args=lambda u: [
        flag("-list"),
        *_page_range_args(u.first_page, u.last_page),
        PathArg(value=u.input_file, must_exist=True),
    ],
)

POPPLER_ACTIONS = ordered(
    pdf_to_text_spec, pdf_to_image_spec, pdf_info_spec, pdf_images_list_spec
)
__all__ = ["POPPLER_ACTIONS"]
