"""
Docukit — catalogue des actions qpdf (par catégorie, puis à plat).
"""

from workbench.products.docukit.specs.qpdf.actions.actions_pages import QPDF_PAGES_ACTIONS
from workbench.products.docukit.specs.qpdf.actions.actions_edit import QPDF_EDIT_ACTIONS
from workbench.products.docukit.specs.qpdf.actions.actions_secure import QPDF_SECURE_ACTIONS
from workbench.products.docukit.specs.qpdf.actions.actions_maintenance import QPDF_MAINTENANCE_ACTIONS
from workbench.wb_utils.merger import merge

QPDF_ACTIONS = merge(
    QPDF_PAGES_ACTIONS, QPDF_EDIT_ACTIONS,
    QPDF_SECURE_ACTIONS, QPDF_MAINTENANCE_ACTIONS,
)

__all__ = [
    "QPDF_ACTIONS", "QPDF_PAGES_ACTIONS", "QPDF_EDIT_ACTIONS",
    "QPDF_SECURE_ACTIONS", "QPDF_MAINTENANCE_ACTIONS",
]
