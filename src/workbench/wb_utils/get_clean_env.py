#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep  7 03:35:19 2026

@author: hounsousamuel
"""

import os

def get_clean_subprocess_env():
    """
    Sous PyInstaller (Linux/Mac), LD_LIBRARY_PATH est détourné vers les
    libs embarquées dans le binaire. Les binaires externes (ffmpeg, sox,
    magick) doivent tourner avec l'environnement système original, sinon
    ils peuvent mal se comporter ou produire une sortie inattendue.
    """
    env = os.environ.copy()
    original_ld_path = env.pop("LD_LIBRARY_PATH_ORIG", None)
    if original_ld_path is not None:
        env["LD_LIBRARY_PATH"] = original_ld_path
    else:
        env.pop("LD_LIBRARY_PATH", None)
    return env