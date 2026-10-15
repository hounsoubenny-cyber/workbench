"""
Docukit — classes de base des specs.

`DocukitSpec` ajoute à `ActionSpec` :
  - un champ `description` (texte d'aide affiché au-dessus du formulaire) ;
  - la vérification du TYPE RÉEL des fichiers uploadés (par signature),
    branchée sur le hook `validate_args` du socle (voir ActionSpec) ;
  - les arguments communs de l'outil (`COMMON_ARGS`), toujours inclus par
    `full_args()` — exactement comme SECURITY_ARGS dans Mediakit.

⚠️ Toujours construire la commande via `full_args()`, jamais `build_args()`.
"""

from pathlib import Path
from typing import ClassVar

from workbench.core.subprocess.engine import resolve_sandboxed_path
from workbench.core.subprocess.wb_subprocess_types import Arg
from workbench.specs.pipeline_spec import PipelineSpec
from workbench.specs.specs import ActionSpec, InputT
from workbench.specs.uploads import collect_upload_filenames
from workbench.products.docukit.dk_utils.files import is_image_file, is_pdf_file


class InvalidDocumentError(Exception):
    """Le fichier fourni n'est pas du type attendu (ou a disparu du workdir)."""


_CHECKS = {
    "pdf": (is_pdf_file, "un document PDF"),
    "image": (is_image_file, "une image (PNG, JPEG, TIFF, BMP, GIF ou WebP)"),
}


class DocukitSpec(ActionSpec[InputT]):
    description: str = ""
    validate_arg: bool = True

    # Type attendu pour TOUS les champs UploadRef du modèle : "pdf", "image"
    # ou None (aucune vérification de contenu).
    upload_kind: ClassVar[str | None] = None
    # Arguments ajoutés devant ceux de l'action.
    COMMON_ARGS: ClassVar[list] = []

    def full_args(self, user_input: InputT) -> list[Arg]:
        return [*self.COMMON_ARGS, *self.build_args(user_input)]

    def validate_args(self, user_input: InputT, workdir: Path) -> None:
        kind = self.upload_kind
        if kind:
            check, human = _CHECKS[kind]
            for name in collect_upload_filenames(user_input):
                path = resolve_sandboxed_path(name, workdir)
                if not path.is_file():
                    raise InvalidDocumentError(f"fichier introuvable : {name}")
                if not check(path):
                    raise InvalidDocumentError(
                        f"« {name} » n'est pas {human} valide "
                        "(le contenu ne correspond pas)"
                    )
        self.extra_validation(user_input, workdir)

    def extra_validation(self, user_input: InputT, workdir: Path) -> None:
        """Hook pour les contrôles propres à une action (langue OCR, etc.)."""


class DocukitPipelineSpec(PipelineSpec[InputT]):
    """PipelineSpec + texte d'aide pour l'interface."""

    description: str = ""
