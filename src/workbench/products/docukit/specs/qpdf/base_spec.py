"""
Docukit — spec de base pour qpdf.

`--warning-exit-0` : qpdf renvoie le code 3 quand il termine avec de simples
avertissements (PDF légèrement abîmé mais correctement traité). Le moteur ne
considère comme succès que les codes 0 et 1 : sans ce drapeau, une réparation
réussie serait vue comme un échec. Les erreurs réelles gardent le code 2.
"""

from typing import ClassVar

from workbench.specs.specs import InputT
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
from workbench.products.docukit.specs.base import DocukitSpec
from workbench.products.docukit.specs.common import flag

QPDF_CONFIG = BinVersionCheckerConfig(
    cmd="--version", marker="qpdf version", tool_name="qpdf"
)
MIN_QPDF_VERSION = (10, 6)


class QpdfSpec(DocukitSpec[InputT]):
    tool: str = "qpdf"
    binary_config: BinVersionCheckerConfig = QPDF_CONFIG
    min_version: tuple | None = MIN_QPDF_VERSION
    upload_kind: ClassVar[str | None] = "pdf"
    COMMON_ARGS: ClassVar[list] = [flag("--warning-exit-0")]
