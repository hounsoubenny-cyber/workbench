"""
Docukit — briques communes à toutes les specs.

Contient :
  - `Out`            : les noms de fichiers produits (source de vérité unique) ;
  - les validateurs  : noms de fichiers, plages de pages, mots de passe ;
  - `attached_option`: option CLI "collée" `--nom=valeur` (voir sa docstring) ;
  - `ordered`        : construit un catalogue {id: spec} dans un ordre voulu.

Principe : toute valeur issue du client est validée ICI, avant même d'être
transformée en `Arg` typé. Le moteur (CommandEngine) reste la dernière ligne
de défense (sandbox des chemins, pas de shell), pas la seule.
"""

import re

from workbench.core.subprocess.wb_subprocess_types import BoolArg, EnumArg

# =============================================================================
# 1. NOMS DES FICHIERS PRODUITS
# =============================================================================


class Out:
    """Noms des fichiers de sortie. Un seul endroit : jamais de doublon."""

    MERGED = "merged.pdf"
    EXTRACTED = "extracted.pdf"
    TRIMMED = "trimmed.pdf"
    REVERSED = "reversed.pdf"
    ROTATED = "rotated.pdf"
    STAMPED = "stamped.pdf"
    PROTECTED = "protected.pdf"
    UNLOCKED = "unlocked.pdf"
    REPAIRED = "repaired.pdf"
    OPTIMIZED = "optimized.pdf"
    CHECK_REPORT = "check_report.txt"
    INFO = "info.txt"
    TEXT = "text.txt"
    IMAGES_LIST = "images_list.txt"
    PAGE_PNG = "page.png"
    PAGE_JPG = "page.jpg"
    OCR_TEXT = "ocr_text.txt"
    OCR_PDF = "ocr_searchable.pdf"


PANDOC_OUT_EXT = {
    "html": "html", "gfm": "md", "markdown": "md", "plain": "txt",
    "rst": "rst", "docx": "docx", "odt": "odt", "epub": "epub",
}

# Un fichier uploadé NE DOIT JAMAIS porter le nom d'un fichier de sortie :
# l'outil lirait et écrirait le même chemin (corruption silencieuse).
# Comparaison en minuscules (systèmes de fichiers insensibles à la casse).
RESERVED_NAMES = frozenset(
    {v.lower() for k, v in vars(Out).items() if not k.startswith("_")}
    | {f"converted.{ext}" for ext in PANDOC_OUT_EXT.values()}
)

PDF_EXTS = (".pdf",)
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp")
PANDOC_IN_EXTS = (
    ".md", ".markdown", ".txt", ".html", ".htm", ".docx", ".odt",
    ".epub", ".rst", ".tex",
)

# Aucun séparateur de chemin, aucun ':' (protocoles CLI), aucun caractère de
# contrôle ; 1 à 100 caractères.
_NAME_RE = re.compile(r"[^/\\:\x00-\x1f\x7f]{1,100}")


def check_filename(value: str, exts: tuple[str, ...] | None = None) -> str:
    """Valide un nom de fichier uploadé. Retourne la valeur inchangée."""
    if not isinstance(value, str) or not _NAME_RE.fullmatch(value):
        raise ValueError(
            "nom de fichier invalide (1 à 100 caractères, sans / \\ : ni "
            "caractère de contrôle)"
        )
    if value.startswith(("-", ".")) or value != value.strip() or value.endswith("."):
        raise ValueError(
            "nom de fichier invalide (ne doit pas commencer par '-' ou '.', "
            "ni se terminer par un point ou une espace)"
        )
    if value.lower() in RESERVED_NAMES:
        raise ValueError(f"nom de fichier réservé par Docukit : {value!r}")
    if exts and not value.lower().endswith(exts):
        raise ValueError(f"extension attendue : {', '.join(exts)}")
    return value


def check_filenames(values: list[str], exts: tuple[str, ...] | None = None) -> list[str]:
    """Valide une liste de noms ; refuse les doublons (insensible à la casse)."""
    for v in values:
        check_filename(v, exts)
    lowered = [v.lower() for v in values]
    if len(set(lowered)) != len(lowered):
        raise ValueError("noms de fichiers en double dans la liste")
    return values


# =============================================================================
# 2. PLAGES DE PAGES (syntaxe qpdf)
# =============================================================================
#   1-3,5,8-z   (z = dernière page)   r1 = dernière page, r2 = avant-dernière
#   :odd / :even                        x = exclusion (ex : 1-z,x3)
# Pas de page 0 : `[1-9]\d{0,5}`.

_NUM = r"(?:r?[1-9]\d{0,5}|z)"
_ITEM = rf"{_NUM}(?:-{_NUM})?(?::(?:odd|even))?"
PAGE_RANGE_PATTERN = rf"x?{_ITEM}(?:,x?{_ITEM})*"          # exclusions autorisées
PAGE_SELECT_PATTERN = rf"{_ITEM}(?:,{_ITEM})*"             # sans 'x'
_RANGE_RE = re.compile(PAGE_RANGE_PATTERN)
_SELECT_RE = re.compile(PAGE_SELECT_PATTERN)

PAGE_RANGE_HELP = "ex : 1-3,5,8-z  (z = dernière page ; :odd / :even = impaires / paires)"


def check_page_range(value: str, allow_exclusion: bool = True) -> str:
    """Valide une plage de pages qpdf (longueur max 200)."""
    regex = _RANGE_RE if allow_exclusion else _SELECT_RE
    if len(value) > 200 or not regex.fullmatch(value):
        raise ValueError(f"plage de pages invalide : {value!r} — {PAGE_RANGE_HELP}")
    return value


# =============================================================================
# 3. MOTS DE PASSE
# =============================================================================

def check_password(value: str, label: str = "mot de passe") -> str:
    """1 à 128 caractères, sans contrôle, ne commence pas par '-'."""
    if not 1 <= len(value) <= 128:
        raise ValueError(f"{label} : 1 à 128 caractères")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f"{label} : caractères de contrôle interdits")
    if value.startswith("-"):
        raise ValueError(f"{label} : ne peut pas commencer par '-'")
    return value


# =============================================================================
# 4. ARGUMENTS TYPÉS
# =============================================================================

def flag(name: str) -> BoolArg:
    """Un drapeau seul (`--empty`, `--`, `-layout`...), toujours présent."""
    return BoolArg(flag=name, value=True)


def attached_option(name: str, value: str, allowed: str) -> EnumArg:
    """
    Option "collée" `--nom=valeur`, en UN seul argv.

    Certains outils (qpdf : --rotate, --password, --to, --repeat...) REFUSENT
    la forme `--nom valeur` (deux argv) : "--rotate must be given as
    --rotate=angle". Le moteur n'a pas de type pour ça, et `PatternArg`
    interdit à juste titre qu'un positionnel commence par '-'.

    On emploie donc le même idiome que les arguments de sécurité de Mediakit :
    un `EnumArg` dont la liste de valeurs autorisées ne contient QUE la
    chaîne finale. Mais ici la valeur vient du client, donc on la valide
    d'abord, strictement, avec l'expression régulière `allowed` (fullmatch).
    """
    if not re.fullmatch(allowed, value):
        raise ValueError(f"valeur invalide pour {name} : {value!r}")
    full = f"{name}={value}"
    return EnumArg(value=full, enum_values=[full])


def ordered(*specs) -> dict:
    """{id: spec} dans l'ordre donné (ordre d'affichage dans l'UI), ids uniques."""
    out: dict = {}
    for spec in specs:
        if spec.id in out:
            raise ValueError(f"Deux specs partagent l'id {spec.id!r}")
        out[spec.id] = spec
    return out
