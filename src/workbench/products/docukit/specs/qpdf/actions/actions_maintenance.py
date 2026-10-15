"""
Docukit — qpdf : maintenance (vérifier, réparer, optimiser).
"""

from workbench.core.subprocess.wb_subprocess_types import PathArg
from workbench.products.docukit.specs.common import (
    Out, attached_option, flag, ordered,
)
from workbench.products.docukit.specs.qpdf.base_spec import QpdfSpec
from workbench.products.docukit.specs.qpdf.base_model import (
    CheckInput, RepairInput, OptimizeInput,
)

check_spec = QpdfSpec[CheckInput](
    id="qpdf_check",
    label="Vérifier l'intégrité du PDF",
    description="Analyse la structure du fichier et produit un rapport texte.",
    input_cls=CheckInput,
    output_filename_template=Out.CHECK_REPORT,
    capture_stdout=True,
    build_args=lambda u: [
        flag("--check"),
        PathArg(value=u.input_file, must_exist=True),
    ],
)

repair_spec = QpdfSpec[RepairInput](
    id="qpdf_repair",
    label="Réparer un PDF abîmé",
    description=(
        "Reconstruit la structure d'un PDF endommagé (table de références "
        "corrompue, fichier tronqué…) quand c'est possible."
    ),
    input_cls=RepairInput,
    output_filename_template=Out.REPAIRED,
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=Out.REPAIRED),
    ],
)


def _optimize_args(u: OptimizeInput) -> list:
    args = [
        attached_option("--object-streams", "generate", r"generate"),
        attached_option("--compress-streams", "y", r"y"),
        flag("--recompress-flate"),
        attached_option("--compression-level", "9", r"9"),
    ]
    if u.web_optimized:
        args.append(flag("--linearize"))
    args += [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=Out.OPTIMIZED),
    ]
    return args


optimize_spec = QpdfSpec[OptimizeInput](
    id="qpdf_optimize",
    label="Optimiser la structure (sans perte)",
    description=(
        "Recompresse la structure interne du PDF sans toucher au rendu. "
        "Gain modeste mais garanti sans perte de qualité."
    ),
    input_cls=OptimizeInput,
    output_filename_template=Out.OPTIMIZED,
    build_args=_optimize_args,
)

QPDF_MAINTENANCE_ACTIONS = ordered(check_spec, repair_spec, optimize_spec)
__all__ = ["QPDF_MAINTENANCE_ACTIONS"]
