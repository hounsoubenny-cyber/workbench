"""
Docukit — détection du type réel d'un fichier par sa signature (magic bytes).

Volontairement sans dépendance à libmagic : les signatures utiles à Docukit
(PDF, images raster) sont triviales à reconnaître, et ne pas dépendre d'une
bibliothèque système évite un point de défaillance à l'installation
(notamment dans le binaire PyInstaller / Tauri).

On ne se fie JAMAIS à l'extension fournie par le client : elle ne sert qu'à
nommer le fichier dans le workdir, la vérité est dans le contenu.
"""

from pathlib import Path

# La spec PDF tolère jusqu'à 1024 octets de "bruit" avant l'en-tête %PDF-.
_PDF_SCAN_BYTES = 1024


def _head(path: str | Path, n: int) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except OSError:
        return b""


def is_pdf_file(path: str | Path) -> bool:
    """Vrai si l'en-tête `%PDF-` apparaît dans les 1024 premiers octets."""
    return b"%PDF-" in _head(path, _PDF_SCAN_BYTES)


def is_image_file(path: str | Path) -> bool:
    """Vrai pour PNG, JPEG, GIF, BMP, TIFF et WebP (reconnus par signature)."""
    head = _head(path, 16)
    if len(head) < 4:
        return False
    return (
        head.startswith(b"\x89PNG\r\n\x1a\n")
        or head.startswith(b"\xff\xd8\xff")                       # JPEG
        or head.startswith((b"GIF87a", b"GIF89a"))
        or head.startswith(b"BM")                                 # BMP
        or head.startswith((b"II*\x00", b"MM\x00*"))              # TIFF
        or (head.startswith(b"RIFF") and head[8:12] == b"WEBP")   # WebP
    )
