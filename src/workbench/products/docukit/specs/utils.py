"""
Docukit — catalogue : catégories, recherche de specs, configs des binaires.

Les catégories sont orientées TÂCHES (« Organiser », « Sécuriser »…) et non
outils (« qpdf », « poppler ») : un utilisateur pense « fusionner », pas
« qpdf --pages ».
"""

from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
from workbench.specs.pipeline_spec import PipelineSpec
from workbench.wb_utils.merger import merge
from workbench.products.docukit import PRODUCT_ID, PRODUCT_NAME, __version__
from workbench.products.docukit.specs.qpdf.actions import (
    QPDF_PAGES_ACTIONS, QPDF_EDIT_ACTIONS, QPDF_SECURE_ACTIONS, QPDF_MAINTENANCE_ACTIONS,
)
from workbench.products.docukit.specs.poppler.actions import POPPLER_ACTIONS
from workbench.products.docukit.specs.poppler.base_spec import (
    PDFINFO_CONFIG, PDFTOTEXT_CONFIG, PDFTOPPM_CONFIG, PDFIMAGES_CONFIG,
)
from workbench.products.docukit.specs.qpdf.base_spec import QPDF_CONFIG
from workbench.products.docukit.specs.tesseract.actions import TESSERACT_ACTIONS, TESSERACT_CONFIG
from workbench.products.docukit.specs.pandoc.actions import PANDOC_ACTIONS, PANDOC_CONFIG
from workbench.products.docukit.specs.pipelines import PIPELINE_ACTIONS

# ─── Catégories (ordre = ordre d'affichage) ──────────────────────────────────

CATEGORIES: list[dict] = [
    {"id": "organize", "label": "Organiser", "icon": "📑",
     "description": "Fusionner, extraire, supprimer, inverser des pages.",
     "specs": QPDF_PAGES_ACTIONS},
    {"id": "edit", "label": "Éditer", "icon": "✏️",
     "description": "Pivoter des pages, ajouter un tampon ou un filigrane.",
     "specs": QPDF_EDIT_ACTIONS},
    {"id": "secure", "label": "Sécuriser", "icon": "🔒",
     "description": "Protéger par mot de passe ou retirer la protection.",
     "specs": QPDF_SECURE_ACTIONS},
    {"id": "extract", "label": "Lire & extraire", "icon": "🔍",
     "description": "Texte, images, informations et aperçu des pages.",
     "specs": POPPLER_ACTIONS},
    {"id": "ocr", "label": "OCR", "icon": "🧾",
     "description": "Lire le texte d'un scan ou d'une photo.",
     "specs": TESSERACT_ACTIONS},
    {"id": "convert", "label": "Convertir", "icon": "🔄",
     "description": "Word, Markdown, HTML, EPUB…",
     "specs": PANDOC_ACTIONS},
    {"id": "maintenance", "label": "Réparer & optimiser", "icon": "🛠️",
     "description": "Vérifier, réparer, alléger un PDF.",
     "specs": QPDF_MAINTENANCE_ACTIONS},
    {"id": "workflows", "label": "Workflows", "icon": "⚡",
     "description": "Plusieurs opérations enchaînées en un clic.",
     "specs": PIPELINE_ACTIONS},
]

ALL_SPECS: dict = merge(*[c["specs"] for c in CATEGORIES])
_CATEGORY_OF = {sid: c["id"] for c in CATEGORIES for sid in c["specs"]}

# ─── Binaires ────────────────────────────────────────────────────────────────

BINARY_CONFIGS: dict[str, BinVersionCheckerConfig] = {
    "qpdf": QPDF_CONFIG,
    "pdfinfo": PDFINFO_CONFIG,
    "pdftotext": PDFTOTEXT_CONFIG,
    "pdftoppm": PDFTOPPM_CONFIG,
    "pdfimages": PDFIMAGES_CONFIG,
    "tesseract": TESSERACT_CONFIG,
    "pandoc": PANDOC_CONFIG,
}

# Aide à l'installation affichée quand un outil est introuvable.
INSTALL_HINTS: dict[str, str] = {
    "qpdf": "Installez qpdf (apt install qpdf · brew install qpdf · winget install qpdf).",
    "pdfinfo": "Installez poppler-utils (apt install poppler-utils · brew install poppler).",
    "pdftotext": "Installez poppler-utils (apt install poppler-utils · brew install poppler).",
    "pdftoppm": "Installez poppler-utils (apt install poppler-utils · brew install poppler).",
    "pdfimages": "Installez poppler-utils (apt install poppler-utils · brew install poppler).",
    "tesseract": "Installez tesseract-ocr et le pack de langue (apt install tesseract-ocr tesseract-ocr-fra).",
    "pandoc": "Installez pandoc (https://pandoc.org/installing.html).",
}


def get_binary_config(tool_name: str) -> BinVersionCheckerConfig:
    """Config de version d'un binaire. KeyError si l'outil est inconnu."""
    return BINARY_CONFIGS[tool_name]


def get_spec(spec_id: str):
    return ALL_SPECS.get(spec_id)


def _tools_of(spec) -> list[str]:
    if isinstance(spec, PipelineSpec):
        seen: list[str] = []
        for step in spec.steps:
            if step.action.tool not in seen:
                seen.append(step.action.tool)
        return seen
    return [spec.tool]


def get_catalog() -> dict:
    """
    Catalogue complet pour l'interface (route GET /api/catalog) :
    `categories` (ordre d'affichage, ids de specs), `specs` (résumés),
    `tools` (binaires requis et aide à l'installation).
    """
    specs = {}
    for sid, spec in ALL_SPECS.items():
        specs[sid] = {
            "id": sid,
            "label": spec.label,
            "description": spec.description,
            "type": "pipeline" if isinstance(spec, PipelineSpec) else "action",
            "category": _CATEGORY_OF[sid],
            "tools": _tools_of(spec),
        }
    return {
        "product": {"id": PRODUCT_ID, "name": PRODUCT_NAME, "version": __version__},
        "categories": [
            {"id": c["id"], "label": c["label"], "icon": c["icon"],
             "description": c["description"], "specs": list(c["specs"])}
            for c in CATEGORIES
        ],
        "specs": specs,
        "tools": {t: {"install": hint} for t, hint in INSTALL_HINTS.items()},
    }
