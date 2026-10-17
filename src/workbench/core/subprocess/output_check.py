"""
Workbench — vérification du fichier produit par un outil.

Problème corrigé : un outil peut se terminer avec un code « acceptable » (0, ou 1 que
`ExecResult.ok` tolère) sans avoir produit son fichier — ou en produisant un fichier
VIDE (encodage qui échoue après avoir créé le fichier, image demandée au-delà de la
fin d'une vidéo...). Le job était alors déclaré réussi, et l'étape suivante d'un
pipeline échouait avec un message sans rapport avec la cause.

Règle :
  - le fichier déclaré doit EXISTER ;
  - il doit être NON VIDE quand c'est l'outil qui l'écrit. Une sortie texte capturée
    (`capture_stdout=True`) peut légitimement être vide (ex : grep sans résultat).
"""

from pathlib import Path


class OutputError(Exception):
    """Le fichier de sortie déclaré est absent ou vide."""

    def __init__(self, filename: str, reason: str):
        self.filename = filename
        self.reason = reason
        super().__init__(reason)


class OutputMissingError(OutputError):
    def __init__(self, filename: str):
        super().__init__(filename, f"l'outil s'est terminé sans produire le fichier « {filename} »")


class OutputEmptyError(OutputError):
    def __init__(self, filename: str):
        super().__init__(filename, f"le fichier « {filename} » produit par l'outil est vide")


def verify_output(path: Path, filename: str, *, allow_empty: bool) -> None:
    """Lève OutputMissingError / OutputEmptyError si le fichier déclaré n'est pas exploitable."""
    path = Path(path)
    if not path.is_file():
        raise OutputMissingError(filename)
    if not allow_empty and path.stat().st_size == 0:
        raise OutputEmptyError(filename)
