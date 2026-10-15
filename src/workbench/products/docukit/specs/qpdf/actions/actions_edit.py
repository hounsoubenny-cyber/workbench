"""
Docukit — qpdf : éditer (rotation, tampon / filigrane).

`--rotate`, `--to`, `--repeat` n'acceptent que la forme collée `--nom=valeur`
(voir `attached_option`) : la valeur est validée par expression régulière
avant d'être injectée.
"""

from workbench.core.subprocess.wb_subprocess_types import PathArg
from workbench.products.docukit.specs.common import (
    Out, PAGE_RANGE_PATTERN, attached_option, flag, ordered,
)
from workbench.products.docukit.specs.qpdf.base_spec import QpdfSpec
from workbench.products.docukit.specs.qpdf.base_model import RotateInput, StampInput

rotate_spec = QpdfSpec[RotateInput](
    id="qpdf_rotate",
    label="Pivoter des pages",
    description="Tourne les pages choisies de 90°, 180° ou 270° (sens horaire).",
    input_cls=RotateInput,
    output_filename_template=Out.ROTATED,
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(value=Out.ROTATED),
        attached_option(
            "--rotate", f"+{u.angle}:{u.pages}",
            rf"\+(?:90|180|270):{PAGE_RANGE_PATTERN}",
        ),
    ],
)

stamp_spec = QpdfSpec[StampInput](
    id="qpdf_stamp",
    label="Ajouter un tampon ou un filigrane (PDF)",
    description=(
        "Superpose (ou place derrière) la première page d'un PDF « tampon » "
        "sur chaque page du document : filigrane CONFIDENTIEL, papier à en-tête, logo…"
    ),
    input_cls=StampInput,
    output_filename_template=Out.STAMPED,
    build_args=lambda u: [
        PathArg(value=u.input_file, must_exist=True),
        PathArg(flag=f"--{u.mode}", value=u.stamp_file, must_exist=True),
        attached_option("--to", u.pages, PAGE_RANGE_PATTERN),
        attached_option("--repeat", "1", r"1"),
        flag("--"),
        PathArg(value=Out.STAMPED),
    ],
)

QPDF_EDIT_ACTIONS = ordered(rotate_spec, stamp_spec)
__all__ = ["QPDF_EDIT_ACTIONS"]
