"""
Mediakit — texte libre passé à un outil (filigrane, badge de pipeline).

ImageMagick interprète certains caractères du texte d'`-annotate` : `%w`, `%[fx:...]`
(substitutions) et un `@` initial (lire le texte depuis un FICHIER). La liste blanche
ci-dessous écarte ces cas (pas de `%`, `@`, `\\`, guillemets, `:`...).

Elle accepte les LETTRES de toutes les langues (`\\w` est Unicode en Python 3) : un outil en
français doit pouvoir écrire « Café », « NOUVEL ÉPISODE » ou « Photo © Bénin ».
"""

import re

OVERLAY_TEXT_PATTERN = r"^[\w\- #\.\+©']+$"
_RE = re.compile(OVERLAY_TEXT_PATTERN)

OVERLAY_TEXT_HELP = (
    "lettres (accents compris), chiffres, espace et les signes - _ . + # © ' uniquement"
)


def check_overlay_text(value: str) -> str:
    """Valide un texte de filigrane dès l'entrée (refus clair, avant toute exécution)."""
    if not value or not _RE.fullmatch(value) or value.startswith("-"):
        raise ValueError(f"texte non autorisé : {OVERLAY_TEXT_HELP}")
    return value
