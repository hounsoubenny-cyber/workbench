"""
Docukit — pipelines : workflows qui enchaînent plusieurs outils.

Chaque étape écrit un fichier dans le workdir que l'étape suivante référence
(jamais de pipe Unix). Le modèle d'entrée d'un pipeline est le formulaire
affiché à l'utilisateur ; il hérite des validateurs des modèles d'actions
qu'il réutilise, de sorte que TOUTE valeur client est validée une fois, à
l'entrée.

Les étapes construisent leurs entrées avec `model_construct` : les fichiers
intermédiaires (`merged.pdf`, `page.png`…) portent des noms réservés que les
validateurs refusent côté client (voir `RESERVED_NAMES`), et les autres
valeurs ont déjà été validées par le modèle du pipeline.
"""

from pydantic import Field

from workbench.specs.pipeline_spec import PipelineStepSpec
from workbench.products.docukit.specs.base import DocukitPipelineSpec
from workbench.products.docukit.specs.common import ordered
from workbench.products.docukit.specs.qpdf.base_model import (
    MergeInput, OptimizeInput, ExtractPagesInput, ProtectInput, PdfSourceInput,
)
from workbench.products.docukit.specs.qpdf.actions.actions_pages import (
    merge_spec, extract_pages_spec,
)
from workbench.products.docukit.specs.qpdf.actions.actions_maintenance import optimize_spec
from workbench.products.docukit.specs.qpdf.actions.actions_secure import protect_spec
from workbench.products.docukit.specs.poppler.base_model import PdfToImageInput
from workbench.products.docukit.specs.poppler.actions import pdf_to_image_spec
from workbench.products.docukit.specs.tesseract.base_model import (
    OcrTextInput, OcrLanguage, OcrPageMode,
)
from workbench.products.docukit.specs.tesseract.actions import ocr_text_spec


# =============================================================================
# 1. FUSIONNER PUIS OPTIMISER   (qpdf -> qpdf)
# =============================================================================

class MergeOptimizeInput(MergeInput):
    web_optimized: bool = Field(
        default=True,
        description="Affichage rapide sur le web (la 1re page s'affiche avant la fin du téléchargement)",
    )


pipeline_merge_optimize = DocukitPipelineSpec[MergeOptimizeInput](
    id="docukit_merge_optimize",
    label="Fusionner puis optimiser",
    description="Assemble plusieurs PDF puis recompresse le résultat, en une seule opération.",
    input_cls=MergeOptimizeInput,
    steps=[
        PipelineStepSpec[MergeOptimizeInput](
            id="step_merge",
            action=merge_spec,
            build_step_input=lambda p, o: MergeInput.model_construct(inputs=p.inputs),
        ),
        PipelineStepSpec[MergeOptimizeInput](
            id="step_optimize",
            action=optimize_spec,
            build_step_input=lambda p, o: OptimizeInput.model_construct(
                input_file=o["step_merge"], web_optimized=p.web_optimized
            ),
        ),
    ],
)


# =============================================================================
# 2. OCR D'UNE PAGE DE PDF SCANNÉ   (pdftoppm -> tesseract)
# =============================================================================

class OcrPageInput(PdfSourceInput):
    page: int = Field(default=1, ge=1, le=100000, description="Numéro de la page à lire")
    language: OcrLanguage = Field(default="fra", description="Langue du texte")
    page_mode: OcrPageMode = Field(
        default="3",
        description="3 = automatique · 4 = une seule colonne · 6 = un seul bloc de texte · 11 = texte épars",
    )


# 3500 px sur le plus grand côté ≈ 300 DPI sur une page A4 : la résolution
# recommandée par tesseract pour une bonne reconnaissance.
_OCR_RENDER_SIDE = 3500

pipeline_ocr_page = DocukitPipelineSpec[OcrPageInput](
    id="docukit_ocr_page",
    label="Lire une page d'un PDF scanné (OCR)",
    description=(
        "Rend la page en image haute définition puis en extrait le texte par OCR. "
        "Pour un PDF dont le texte est déjà sélectionnable, préférez « Extraire le texte »."
    ),
    input_cls=OcrPageInput,
    steps=[
        PipelineStepSpec[OcrPageInput](
            id="step_render",
            action=pdf_to_image_spec,
            build_step_input=lambda p, o: PdfToImageInput.model_construct(
                input_file=p.input_file, page=p.page, longest_side=_OCR_RENDER_SIDE,
                format="png", grayscale=True,
            ),
        ),
        PipelineStepSpec[OcrPageInput](
            id="step_ocr",
            action=ocr_text_spec,
            build_step_input=lambda p, o: OcrTextInput.model_construct(
                input_file=o["step_render"], language=p.language, page_mode=p.page_mode
            ),
        ),
    ],
)


# =============================================================================
# 3. EXTRAIT PROTÉGÉ   (qpdf -> qpdf)
# =============================================================================

# Ordre des champs affichés : fichier, pages, puis les réglages de protection.
class ProtectedExcerptInput(ProtectInput, ExtractPagesInput):
    pass


pipeline_protected_excerpt = DocukitPipelineSpec[ProtectedExcerptInput](
    id="docukit_protected_excerpt",
    label="Extraire des pages et les protéger par mot de passe",
    description="Idéal pour partager seulement quelques pages d'un document, sous mot de passe.",
    input_cls=ProtectedExcerptInput,
    steps=[
        PipelineStepSpec[ProtectedExcerptInput](
            id="step_extract",
            action=extract_pages_spec,
            build_step_input=lambda p, o: ExtractPagesInput.model_construct(
                input_file=p.input_file, pages=p.pages
            ),
        ),
        PipelineStepSpec[ProtectedExcerptInput](
            id="step_protect",
            action=protect_spec,
            build_step_input=lambda p, o: ProtectInput.model_construct(
                input_file=o["step_extract"], password=p.password,
                owner_password=p.owner_password, allow_print=p.allow_print,
                allow_copy=p.allow_copy, allow_modify=p.allow_modify,
            ),
        ),
    ],
)


PIPELINE_ACTIONS = ordered(
    pipeline_merge_optimize, pipeline_ocr_page, pipeline_protected_excerpt
)
__all__ = ["PIPELINE_ACTIONS"]
