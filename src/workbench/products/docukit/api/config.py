"""
Docukit — configuration du moteur (fichier TOML).

Hérite de `WbConfig` (jobs simultanés, buffers, durée de vie des fichiers).
Chargement / sauvegarde via le gestionnaire du socle : fichier absent =
valeurs par défaut (premier lancement).
"""

from workbench.api.config import WbConfig
from workbench.api.config_manager import load_config, save_config


class WbDocukitConfig(WbConfig):
    pass


def load(path) -> WbDocukitConfig:
    return load_config(str(path), WbDocukitConfig)


def save(config: WbConfig, path) -> bool:
    return save_config(config, str(path))
