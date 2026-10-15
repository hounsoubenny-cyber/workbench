#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 14:40:50 2026

@author: hounsousamuel
"""

import os
import tempfile
import tomli
import tomli_w
from dotenv import load_dotenv
from workbench.api.config import WbConfig

load_dotenv()

def load_config(path: str, config_cls: type[WbConfig] = WbConfig):
    """
    Charge la config TOML dans `config_cls` (les clés inconnues sont ignorées).

    Fichier absent (premier lancement) -> configuration PAR DÉFAUT, jamais None.
    FIX : avant, la fonction renvoyait None dans ce cas (crash au démarrage) et
    construisait toujours un `WbConfig`, ignorant `config_cls`.
    """
    if not os.path.exists(path):
        return config_cls()
    with open(path, "rb") as f:
        conf = dict(tomli.load(f))
    keys = set(config_cls.model_fields)
    return config_cls(**{k: v for k, v in conf.items() if k in keys})

def save_config(config: WbConfig, path: str):
    """
    Écrit la config en TOML, de façon atomique (fichier temporaire puis
    remplacement) pour ne jamais laisser un fichier tronqué, et crée les
    dossiers parents si besoin (FIX : échouait si le dossier n'existait pas).
    """
    conf = dict(config.model_dump())
    to_save = {k: v for k, v in conf.items() if v is not None}
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            tomli_w.dump(to_save, f)
        os.replace(tmp_path, path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
    return True
