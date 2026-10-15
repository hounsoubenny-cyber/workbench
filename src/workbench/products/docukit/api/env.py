"""
Docukit — réglages d'exécution, lus dans les variables d'environnement.

Aucun effet de bord à l'import (contrairement à un module qui lèverait si une
variable manque) : tout passe par `Settings.from_env()`, donc l'application
est instanciable dans un test sans rien configurer.

  DOCUKIT_HOST            interface d'écoute        (défaut 127.0.0.1)
  DOCUKIT_PORT            port ; 0 = port libre     (défaut 0)
  DOCUKIT_MAX_UPLOAD_MB   taille max d'une requête  (défaut 200)
  DOCUKIT_CONFIG_FILE     fichier de config TOML    (défaut : dossier de config utilisateur)
  DOCUKIT_ALLOWED_HOSTS   hôtes supplémentaires acceptés dans l'en-tête Host
                          (séparés par des virgules) — seulement si DOCUKIT_HOST
                          n'est pas une adresse locale
  DOCUKIT_OPEN_BROWSER    1/0 : ouvrir le navigateur au démarrage (défaut 1)
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

_TRUE = {"1", "true", "yes", "on"}


def default_config_path() -> Path:
    """Fichier de config dans le dossier de config de l'utilisateur (par plateforme)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "docukit" / "config.toml"


@dataclass(frozen=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 0
    max_upload_mb: int = 200
    config_path: Path = field(default_factory=default_config_path)
    allowed_hosts: tuple[str, ...] = ()
    open_browser: bool = True

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if environ is None else environ
        defaults = cls()

        def _int(key: str, default: int, minimum: int, maximum: int) -> int:
            raw = env.get(key)
            if raw is None or not raw.strip():
                return default
            try:
                value = int(raw)
            except ValueError:
                raise ValueError(f"{key} doit être un entier (reçu {raw!r})") from None
            if not minimum <= value <= maximum:
                raise ValueError(f"{key} doit être entre {minimum} et {maximum} (reçu {value})")
            return value

        config_file = env.get("DOCUKIT_CONFIG_FILE", "").strip()
        hosts = tuple(h.strip() for h in env.get("DOCUKIT_ALLOWED_HOSTS", "").split(",") if h.strip())
        return cls(
            host=env.get("DOCUKIT_HOST", "").strip() or defaults.host,
            port=_int("DOCUKIT_PORT", defaults.port, 0, 65535),
            max_upload_mb=_int("DOCUKIT_MAX_UPLOAD_MB", defaults.max_upload_mb, 1, 100_000),
            config_path=Path(config_file) if config_file else defaults.config_path,
            allowed_hosts=hosts,
            open_browser=env.get("DOCUKIT_OPEN_BROWSER", "1").strip().lower() in _TRUE,
        )
