#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 10:43:04 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Spécifications et catalogue complet ImageMagick.
"""

from workbench.products.mediakit.specs.magick.actions.actions_convert import MAGICK_CONVERT_ACTIONS
from workbench.products.mediakit.specs.magick.actions.actions_geometry import MAGICK_GEOMETRY_ACTIONS
from workbench.products.mediakit.specs.magick.actions.actions_color import MAGICK_COLOR_ACTIONS
from workbench.products.mediakit.specs.magick.actions.actions_effects import MAGICK_EFFECTS_ACTIONS
from workbench.products.mediakit.specs.magick.actions.actions_overlays import MAGICK_OVERLAYS_ACTIONS
from workbench.wb_utils.merger import merge

# ─── DICT 1 : MERGE TOTAL À PLAT (Recherche O(1) rapide par action_id) ───────
MAGICK_ACTIONS = merge(
    MAGICK_CONVERT_ACTIONS,
    MAGICK_GEOMETRY_ACTIONS,
    MAGICK_COLOR_ACTIONS,
    MAGICK_EFFECTS_ACTIONS,
    MAGICK_OVERLAYS_ACTIONS,
)


# ─── DICT 2 : CATALOGUE GRANULAIRE STRUCTURÉ (Pour les onglets et l'UI) ──────
MAGICK_CATALOG = {
    "all_cat": MAGICK_ACTIONS,
    "categories": {
        "convert": {
            "description": (
                "Transcodage et optimisation de formats : conversion vers les formats modernes du web "
                "(WebP, AVIF, PNG, JPG, TIFF, BMP), compression par réduction de qualité, suppression des métadonnées "
                "privées EXIF/GPS pour alléger les fichiers et génération de favicons multi-tailles ICO."
            ),
            "values": MAGICK_CONVERT_ACTIONS,
        },
        "geometry": {
            "description": (
                "Transformations spatiales et dimensions : redimensionnement par pourcentages ou résolutions cibles, "
                "rognage manuel rectangulaire (crop), création d'avatars carrés centrés sans déformation, extension de "
                "toile avec bandes de couleur (letterbox), rotations, effet miroir et correction d'orientation EXIF."
            ),
            "values": MAGICK_GEOMETRY_ACTIONS,
        },
        "color": {
            "description": (
                "Étalonnage colorimétrique et exposition : conversion en noir et blanc pur, effet virage sépia vintage, "
                "ajustement précis de luminosité et contraste, égalisation dynamique automatique des niveaux (Auto-Level), "
                "inversion en négatif et colorisation par teinte monochrome."
            ),
            "values": MAGICK_COLOR_ACTIONS,
        },
        "effects": {
            "description": (
                "Filtres visuels et dégradations artistiques : flou gaussien (adoucissement ou anonymisation), "
                "accentuation de netteté des détails, mosaïque de pixellisation (censure), effet vignettage sombre aux coins, "
                "rendu artistique de peinture à l'huile et esquisse au fusain."
            ),
            "values": MAGICK_EFFECTS_ACTIONS,
        },
        "overlays": {
            "description": (
                "Superpositions et enrichissements graphiques : incrustation de logos transparents en filigrane (Watermark PNG), "
                "ajout de mentions textuelles de copyright avec positionnement paramétrable, et ajout de cadres ou bordures épaisses."
            ),
            "values": MAGICK_OVERLAYS_ACTIONS,
        },
    },
}


__all__ = [
    "MAGICK_ACTIONS",
    "MAGICK_CATALOG",
]