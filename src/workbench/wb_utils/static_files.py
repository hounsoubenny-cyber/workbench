"""
Workbench — résolution SÛRE d'un fichier statique (frontend servi par l'API).

Les produits servent leur interface (dossier `dist/`) avec une route
fourre-tout. Faire `os.path.join(DIST_DIR, chemin_demandé)` sans borne permet
de sortir du dossier avec `../../...` (ou un chemin absolu, ou un lien
symbolique) et de lire N'IMPORTE QUEL fichier de la machine. Cette fonction
est LA façon de faire.
"""

from pathlib import Path


def resolve_static_file(root: str | Path, relative: str) -> Path | None:
    """
    Retourne le chemin du fichier régulier `relative` situé SOUS `root`,
    ou None s'il n'existe pas ou si le chemin tente de sortir de `root`
    (`..`, chemin absolu, lien symbolique sortant, octet nul).
    """
    if not relative or "\x00" in relative:
        return None
    try:
        root_resolved = Path(root).resolve()
        candidate = (root_resolved / relative).resolve()
    except (OSError, ValueError):
        return None
    if not candidate.is_relative_to(root_resolved):
        return None
    return candidate if candidate.is_file() else None
