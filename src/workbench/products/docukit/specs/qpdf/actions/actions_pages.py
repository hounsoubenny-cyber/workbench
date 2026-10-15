"""
Docukit — qpdf : organiser les pages (fusion, extraction, suppression, inversion).

Toutes ces actions reposent sur `--empty --pages <fichier> [plage] -- <sortie>` :
on part d'un document vide et on y "pioche" les pages voulues.
"""

from workbench.core.subprocess.wb_subprocess_types import (
    MultiPathArg, MultiPathMode, PathArg, PatternArg,
)
from workbench.products.docukit.specs.common import (
    Out, PAGE_RANGE_PATTERN, flag, ordered,
)
from workbench.products.docukit.specs.qpdf.base_spec import QpdfSpec
from workbench.products.docukit.specs.qpdf.base_model import (
    MergeInput, ExtractPagesInput, DeletePagesInput, ReversePagesInput,
)


def _pages_group(input_file: str, page_range: str | None) -> list:
    """`--empty --pages <fichier> [plage] --` : le motif commun des actions."""
    args = [flag("--empty"), flag("--pages"), PathArg(value=input_file, must_exist=True)]
    if page_range:
        args.append(PatternArg(value=page_range, allowed_regex=PAGE_RANGE_PATTERN))
    args.append(flag("--"))
    return args


merge_spec = QpdfSpec[MergeInput](
    id="qpdf_merge",
    label="Fusionner plusieurs PDF en un seul",
    description="Assemble plusieurs documents PDF dans l'ordre choisi.",
    input_cls=MergeInput,
    output_filename_template=Out.MERGED,
    build_args=lambda u: [
        flag("--empty"),
        flag("--pages"),
        MultiPathArg(values=u.inputs, must_exist=True, mode=MultiPathMode.POSITIONAL),
        flag("--"),
        PathArg(value=Out.MERGED),
    ],
)

extract_pages_spec = QpdfSpec[ExtractPagesInput](
    id="qpdf_extract_pages",
    label="Extraire des pages",
    description="Crée un nouveau PDF contenant uniquement les pages choisies.",
    input_cls=ExtractPagesInput,
    output_filename_template=Out.EXTRACTED,
    build_args=lambda u: [
        *_pages_group(u.input_file, u.pages),
        PathArg(value=Out.EXTRACTED),
    ],
)


def _delete_range(pages: str) -> str:
    """Toutes les pages, sauf celles listées (syntaxe qpdf : `1-z,x2,x4-5`)."""
    return "1-z," + ",".join(f"x{part}" for part in pages.split(","))


delete_pages_spec = QpdfSpec[DeletePagesInput](
    id="qpdf_delete_pages",
    label="Supprimer des pages",
    description="Retire les pages indiquées et conserve toutes les autres.",
    input_cls=DeletePagesInput,
    output_filename_template=Out.TRIMMED,
    build_args=lambda u: [
        *_pages_group(u.input_file, _delete_range(u.pages)),
        PathArg(value=Out.TRIMMED),
    ],
)

reverse_pages_spec = QpdfSpec[ReversePagesInput](
    id="qpdf_reverse_pages",
    label="Inverser l'ordre des pages",
    description="Dernière page en premier — utile pour un scan fait à l'envers.",
    input_cls=ReversePagesInput,
    output_filename_template=Out.REVERSED,
    build_args=lambda u: [
        *_pages_group(u.input_file, "z-1"),
        PathArg(value=Out.REVERSED),
    ],
)

QPDF_PAGES_ACTIONS = ordered(
    merge_spec, extract_pages_spec, delete_pages_spec, reverse_pages_spec
)
__all__ = ["QPDF_PAGES_ACTIONS"]
