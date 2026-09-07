#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep  5 11:34:36 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Spécifications et catalogue complet de tous les Pipelines.
"""

from workbench.products.mediakit.specs.pipelines.pipelines_video import PIPELINES_VIDEO_ACTIONS
from workbench.products.mediakit.specs.pipelines.pipelines_image import PIPELINES_IMAGE_ACTIONS
from workbench.products.mediakit.specs.pipelines.pipelines_audio import PIPELINES_AUDIO_ACTIONS
from workbench.products.mediakit.specs.pipelines.pipelines_combo import PIPELINES_COMBO_ACTIONS
from workbench.wb_utils.merger import merge

# ─── DICT 1 : MERGE TOTAL À PLAT (Recherche rapide par pipeline_id) ────
PIPELINE_ACTIONS = merge(
    PIPELINES_VIDEO_ACTIONS,
    PIPELINES_IMAGE_ACTIONS,
    PIPELINES_AUDIO_ACTIONS,
    PIPELINES_COMBO_ACTIONS,
)


# ─── DICT 2 : CATALOGUE GRANULAIRE STRUCTURÉ (Pour les onglets et l'UI) ─────
PIPELINE_CATALOG = {
    "all_cat": PIPELINE_ACTIONS,
    "categories": {
        "video": {
            "description": (
                "Workflows vidéo complets 100% FFmpeg : adaptation automatique pour TikTok/Shorts (9:16 vertical "
                "avec flou d'arrière-plan et logo), optimisation de poids pour streaming web (720p + CRF + Faststart), "
                "création de GIF haute fidélité avec palette 256 couleurs, et vidéos sous-titrées en dur (hardsub)."
            ),
            "values": PIPELINES_VIDEO_ACTIONS,
        },
        "image": {
            "description": (
                "Workflows image complets 100% ImageMagick : packaging e-commerce (redressement EXIF, miniature carrée, "
                "suppression des métadonnées GPS et compression WebP), composition de cartes postales rétro (sépia + "
                "vignettage + cadre), génération de suites d'icônes Favicon ICO, et floutage d'anonymisation."
            ),
            "values": PIPELINES_IMAGE_ACTIONS,
        },
        "audio": {
            "description": (
                "Workflows audio complets 100% SoX : mastering studio pour podcasts et interviews (coupe des silences, "
                "filtre anti-rumble, compresseur multi-bandes et normalisation de crête), préparation optimale pour "
                "l'IA de transcription Whisper (mono 16 kHz), jingles radio et colorisation Lo-Fi rétro."
            ),
            "values": PIPELINES_AUDIO_ACTIONS,
        },
        "combo": {
            "description": (
                "Super-Pipelines croisés multi-outils (SoX + ImageMagick + FFmpeg) : génération de vidéos YouTube "
                "à partir d'un podcast et d'une pochette d'album, remasterisation de bande-son vidéo sans altération "
                "visuelle, création d'affiches teaser promotionnelles et animations WebP ultra-légères."
            ),
            "values": PIPELINES_COMBO_ACTIONS,
        },
    },
}


__all__ = [
    "PIPELINE_ACTIONS",
    "PIPELINE_CATALOG",
]