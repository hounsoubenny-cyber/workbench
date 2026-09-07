#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 18:18:00 2026

@author: hounsousamuel
"""

import os
import magic

def is_video_file(filepath: str) -> bool:
    """Vérifie si le fichier est une vidéo"""
    if not os.path.exists(filepath):
        return False
    
    try:
        mime = magic.from_file(filepath, mime=True)
        return mime is not None and mime.startswith('video/')
    except Exception:
        return False

def is_image_file(filepath: str) -> bool:
    """Vérifie si le fichier est une image"""
    if not os.path.exists(filepath):
        return False
    
    try:
        mime = magic.from_file(filepath, mime=True)
        return mime is not None and mime.startswith('image/')
    except Exception:
        return False

def is_audio_file(filepath: str) -> bool:
    """Vérifie si le fichier est un fichier audio"""
    if not os.path.exists(filepath):
        return False
    
    try:
        mime = magic.from_file(filepath, mime=True)
        return mime is not None and mime.startswith('audio/')
    except Exception:
        return False

