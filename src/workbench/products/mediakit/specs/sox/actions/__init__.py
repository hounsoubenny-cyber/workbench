#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 10:43:04 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Spécifications et catalogue complet SoX.
"""

from workbench.products.mediakit.specs.sox.actions.actions_convert import SOX_CONVERT_ACTIONS
from workbench.products.mediakit.specs.sox.actions.actions_dynamics import SOX_DYNAMICS_ACTIONS
from workbench.products.mediakit.specs.sox.actions.actions_timing import SOX_TIMING_ACTIONS
from workbench.products.mediakit.specs.sox.actions.actions_eq import SOX_EQ_ACTIONS
from workbench.products.mediakit.specs.sox.actions.actions_effects import SOX_EFFECTS_ACTIONS
from workbench.wb_utils.merger import merge

# ─── DICT 1 : MERGE TOTAL À PLAT (Recherche O(1) rapide par action_id) ───────
SOX_ACTIONS = merge(
    SOX_CONVERT_ACTIONS,
    SOX_DYNAMICS_ACTIONS,
    SOX_TIMING_ACTIONS,
    SOX_EQ_ACTIONS,
    SOX_EFFECTS_ACTIONS,
)


# ─── DICT 2 : CATALOGUE GRANULAIRE STRUCTURÉ (Pour les onglets et l'UI) ──────
SOX_CATALOG = {
    "all_cat": SOX_ACTIONS,
    "categories": {
        "convert": {
            "description": (
                "Transcodage et structure de flux : conversion entre formats audio (MP3, WAV, FLAC, OGG), "
                "rééchantillonnage de haute fidélité (48kHz, 44.1kHz, 16kHz pour Whisper/IA), "
                "gestion des canaux stéréo/mono, extraction de canal isolé et ajustement du bit-depth (16/24/32 bits)."
            ),
            "values": SOX_CONVERT_ACTIONS,
        },
        "dynamics": {
            "description": (
                "Contrôle de la dynamique et volume : normalisation de crête (norm) pour maximiser le son "
                "sans écrêtage numérique, gain manuel en décibels, compresseur multi-bandes professionnel (compand) "
                "pour un son percutant type podcast/radio, et suppression automatique des silences et blancs."
            ),
            "values": SOX_DYNAMICS_ACTIONS,
        },
        "timing": {
            "description": (
                "Gestion temporelle et tonalité : découpage précis de segments audio (trim), application de "
                "fondus sonores en entrée et sortie (fade in/out), ajout de silences (pad), modification indépendante "
                "du tempo sans altérer la voix, changement de tonalité (pitch), et lecture inversée (reverse)."
            ),
            "values": SOX_TIMING_ACTIONS,
        },
        "eq": {
            "description": (
                "Égalisation et filtrage fréquentiel : contrôle rapide des basses et aigus (Bass & Treble en dB), "
                "filtre passe-bas pour adoucir le son, filtre passe-haut pour éliminer les résonances sourdes et bruits "
                "de manipulation micro (< 100 Hz), et égaliseur paramétrique chirurgical."
            ),
            "values": SOX_EQ_ACTIONS,
        },
        "effects": {
            "description": (
                "Effets sonores acoustiques et créatifs : réverbération d'espace acoustique de studio, délai et écho "
                "rythmique, effet Chorus pour épaissir la voix et donner du relief, et saturation Overdrive analogique."
            ),
            "values": SOX_EFFECTS_ACTIONS,
        },
    },
}


__all__ = [
    "SOX_ACTIONS",
    "SOX_CATALOG",
]