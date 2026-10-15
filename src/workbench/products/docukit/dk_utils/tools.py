"""
Docukit — utilitaires autour des binaires système.

Tout passe par les MÊMES dossiers de confiance que le moteur d'exécution
(`TRUSTED_DIRS` de workbench.core.subprocess.engine) : on ne sonde jamais un
binaire que le moteur refuserait de lancer.
"""

import os
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from workbench.core.subprocess.engine import TRUSTED_DIRS
from workbench.wb_utils.get_clean_env import get_clean_subprocess_env


def find_trusted_binary(name: str) -> str | None:
    """Chemin du binaire `name` dans les dossiers de confiance, sinon None."""
    return shutil.which(name, path=os.pathsep.join(TRUSTED_DIRS))


@lru_cache(maxsize=1)
def tesseract_languages() -> frozenset[str]:
    """
    Langues réellement installées pour tesseract (`--list-langs`), sans le
    pseudo-modèle `osd` (détection d'orientation, pas une langue d'OCR).
    Mis en cache : la liste ne change pas pendant la vie du process.
    """
    binary = find_trusted_binary("tesseract")
    if not binary:
        return frozenset()
    try:
        result = subprocess.run(
            [binary, "--list-langs"],
            capture_output=True, text=True, timeout=15,
            env=get_clean_subprocess_env(),
        )
    except (OSError, subprocess.SubprocessError):
        return frozenset()
    # La 1re ligne est un en-tête ("List of available languages in ...").
    lines = (result.stdout or result.stderr).splitlines()[1:]
    return frozenset(
        ln.strip() for ln in lines if ln.strip() and ln.strip() != "osd"
    )


@lru_cache(maxsize=32)
def pandoc_sandbox_supports(fmt: str, binary: str | None = None) -> bool:
    """
    Vrai si ce pandoc sait produire le format `fmt` EN MODE `--sandbox`.

    Pourquoi : sur les paquets de distribution (Debian/Ubuntu), les fichiers
    de données de pandoc sont externes au binaire, et `--sandbox` interdit de
    les lire -> les sorties docx / odt / epub échouent. Les binaires
    officiels (embarqués) fonctionnent. Docukit refuse de contourner le
    sandbox (sans lui, un document piégé peut faire embarquer un fichier
    local ou déclencher une requête réseau pendant la conversion) : on
    sonde donc une fois, et on échoue proprement avec un message clair.
    """
    binary = binary or find_trusted_binary("pandoc")
    if not binary:
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="dk-probe-") as tmp:
            out = Path(tmp) / f"probe.{fmt}"
            result = subprocess.run(
                [binary, "--sandbox", "-f", "markdown", "-t", fmt, "-o", str(out)],
                input=b"# probe\n", cwd=tmp, capture_output=True, timeout=20,
                env=get_clean_subprocess_env(),
            )
            return result.returncode == 0 and out.exists() and out.stat().st_size > 0
    except (OSError, subprocess.SubprocessError):
        return False
