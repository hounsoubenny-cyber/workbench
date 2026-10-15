"""
Docukit — action pandoc : convertir un document d'un format à un autre.

🔒 pandoc tourne TOUJOURS avec `--sandbox` : sans lui, un document piégé peut
faire lire un fichier local (`![x](/etc/passwd)`) ou déclencher une requête
réseau (`![x](http://…)` -> SSRF) pendant la conversion, et embarquer le
résultat dans le fichier produit. Aucun filtre, aucun template, aucun fichier
de référence fournis par le client : seulement des formats nommés.
"""

from pathlib import Path
from typing import ClassVar, get_args

from workbench.core.subprocess.wb_subprocess_types import EnumArg, PathArg
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
from workbench.products.docukit.specs.base import DocukitSpec, InvalidDocumentError
from workbench.products.docukit.specs.common import PANDOC_OUT_EXT, flag, ordered
from workbench.products.docukit.specs.pandoc.base_model import (
    PandocConvertInput, PandocFrom, PandocTo,
)
from workbench.products.docukit.dk_utils.tools import pandoc_sandbox_supports

PANDOC_CONFIG = BinVersionCheckerConfig(
    cmd="--version", marker="pandoc", tool_name="pandoc"
)
# Formats dont l'écriture nécessite des fichiers de données (modèles, styles).
_NEEDS_DATA_FILES = ("docx", "odt", "epub")


class PandocSpec(DocukitSpec[PandocConvertInput]):
    tool: str = "pandoc"
    binary_config: BinVersionCheckerConfig = PANDOC_CONFIG
    min_version: tuple | None = (2, 15)   # --sandbox : pandoc >= 2.15
    upload_kind: ClassVar[str | None] = None
    COMMON_ARGS: ClassVar[list] = [flag("--sandbox")]

    def extra_validation(self, user_input: PandocConvertInput, workdir: Path) -> None:
        fmt = user_input.to_format
        if fmt in _NEEDS_DATA_FILES and not pandoc_sandbox_supports(fmt):
            raise InvalidDocumentError(
                f"cette installation de pandoc ne sait pas produire du « {fmt} » en "
                "mode sécurisé (--sandbox). Installez le binaire officiel de pandoc "
                "(https://pandoc.org/installing.html) ou choisissez un format texte "
                "(html, markdown, plain, rst). Docukit ne désactive jamais le sandbox."
            )


def _output_filename(u: PandocConvertInput) -> str:
    return f"converted.{PANDOC_OUT_EXT[u.to_format]}"


def _args(u: PandocConvertInput) -> list:
    return [
        EnumArg(flag="-f", value=u.from_format, enum_values=list(get_args(PandocFrom))),
        EnumArg(flag="-t", value=u.to_format, enum_values=list(get_args(PandocTo))),
        EnumArg(flag="--wrap", value="none", enum_values=["none"]),
        *([flag("--standalone")] if u.standalone else []),
        *([flag("--toc")] if u.toc else []),
        PathArg(flag="-o", value=_output_filename(u)),
        PathArg(value=u.input_file, must_exist=True),
    ]


pandoc_convert_spec = PandocSpec(
    id="pandoc_convert",
    label="Convertir un document (Word, Markdown, HTML, EPUB…)",
    description=(
        "Convertit un document d'un format à un autre en conservant titres, "
        "listes, tableaux et liens. Les images externes ne sont pas embarquées "
        "(mode sécurisé)."
    ),
    input_cls=PandocConvertInput,
    output_filename_template=_output_filename,
    build_args=_args,
)

PANDOC_ACTIONS = ordered(pandoc_convert_spec)
__all__ = ["PANDOC_ACTIONS"]
