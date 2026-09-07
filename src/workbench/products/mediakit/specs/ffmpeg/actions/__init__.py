#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 22:30:16 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Spécifications et catalogue complet FFmpeg.
"""

from workbench.products.mediakit.specs.ffmpeg.actions.actions_convert import FFMPEG_CONVERT_ACTIONS
from workbench.products.mediakit.specs.ffmpeg.actions.actions_extract import FFMPEG_EXTRACT_ACTIONS
from workbench.products.mediakit.specs.ffmpeg.actions.actions_timing import FFMPEG_TIMING_ACTIONS
from workbench.products.mediakit.specs.ffmpeg.actions.actions_geometry import FFMPEG_GEOMETRY_ACTIONS
from workbench.products.mediakit.specs.ffmpeg.actions.actions_audio import FFMPEG_AUDIO_ACTIONS
from workbench.products.mediakit.specs.ffmpeg.actions.actions_effects import FFMPEG_EFFECTS_ACTIONS
from workbench.products.mediakit.specs.ffmpeg.actions.actions_multi import FFMPEG_MULTI_ACTIONS
from workbench.wb_utils.merger import merge

# ─── DICT 1 : MERGE TOTAL À PLAT (Recherche O(1) rapide par action_id) ───────
FFMPEG_ACTIONS = merge(
    FFMPEG_CONVERT_ACTIONS,
    FFMPEG_EXTRACT_ACTIONS,
    FFMPEG_TIMING_ACTIONS,
    FFMPEG_GEOMETRY_ACTIONS,
    FFMPEG_AUDIO_ACTIONS,
    FFMPEG_EFFECTS_ACTIONS,
    FFMPEG_MULTI_ACTIONS,
)


# ─── DICT 2 : CATALOGUE GRANULAIRE STRUCTURÉ (Pour les onglets et l'UI) ──────
FFMPEG_CATALOG = {
    "all_cat": FFMPEG_ACTIONS,
    "categories": {
        "convert": {
            "description": (
                "Transcodage de formats vidéo (MP4, WebM, MKV, AVI, MOV), compression "
                "intelligente par CRF ou taille cible en Mo, optimisation du streaming web (faststart) "
                "et création de GIF animés haute fidélité avec palette 256 couleurs."
            ),
            "values": FFMPEG_CONVERT_ACTIONS,
        },
        "extract": {
            "description": (
                "Extraction de flux spécifiques : capture de miniatures uniques ou en série (planches contact), "
                "démultiplexage audio sans perte ou avec conversion (MP3, WAV, AAC, FLAC), et extraction de "
                "pistes de sous-titres intégrées (SRT, VTT)."
            ),
            "values": FFMPEG_EXTRACT_ACTIONS,
        },
        "timing": {
            "description": (
                "Gestion du temps et de la cadence : découpage rapide sans ré-encodage (calé sur keyframes) "
                "ou précis à la frame près, accélération et ralentissement synchronisés audio/vidéo, inversion "
                "de lecture (reverse) et conversion du framerate (FPS)."
            ),
            "values": FFMPEG_TIMING_ACTIONS,
        },
        "geometry": {
            "description": (
                "Transformation spatiale et cadrage : redimensionnement (1080p, 720p, etc.), recadrage libre "
                "(crop rectangulaire), adaptation aux formats verticaux 9:16 pour les réseaux sociaux (TikTok, Reels, "
                "Shorts avec flou d'arrière-plan), rotations et effets miroir."
            ),
            "values": FFMPEG_GEOMETRY_ACTIONS,
        },
        "audio": {
            "description": (
                "Traitement de la bande sonore dans la vidéo : coupure du son (mute), amplification et "
                "atténuation de volume, normalisation broadcast EBU R128 (standard YouTube/Spotify), fondus audio, "
                "correction de désynchronisation voix/image et remplacement complet de la piste audio."
            ),
            "values": FFMPEG_AUDIO_ACTIONS,
        },
        "effects": {
            "description": (
                "Filtres et incrustations visuelles : ajout de filigranes ou logos PNG transparents avec positionnement "
                "paramétrable, incrustation de sous-titres en dur dans l'image (hardsub), ajustements colorimétriques "
                "(luminosité, contraste, saturation) et flou d'anonymisation."
            ),
            "values": FFMPEG_EFFECTS_ACTIONS,
        },
        "multi": {
            "description": (
                "Opérations multi-fichiers et assemblage : concaténation de plusieurs clips vidéo dans un ordre "
                "défini (avec ou sans ré-encodage) et génération de vidéos de type podcast à partir d'une image fixe "
                "et d'un fichier audio."
            ),
            "values": FFMPEG_MULTI_ACTIONS,
        },
    },
}


__all__ = [
    "FFMPEG_ACTIONS",
    "FFMPEG_CATALOG",
]