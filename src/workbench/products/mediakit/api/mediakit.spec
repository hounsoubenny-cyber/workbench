# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Résolution des racines par rapport à l'emplacement du fichier .spec
SPECPATH_DIR = Path(SPECPATH).resolve()
MEDIAKIT_ROOT = SPECPATH_DIR if (SPECPATH_DIR / "api").exists() else SPECPATH_DIR.parent
SRC_ROOT = (MEDIAKIT_ROOT / ".." / ".." / "..").resolve()
FRONTEND_DIST = MEDIAKIT_ROOT / "frontend" / "dist"
CONFIGS_DIR = MEDIAKIT_ROOT / "configs"

print(f"📦 [BUILD] Racine Mediakit : {MEDIAKIT_ROOT}")
print(f"📦 [BUILD] Racine Source   : {SRC_ROOT}")
print(f"📦 [BUILD] Frontend Dist   : {FRONTEND_DIST}")

# ─── Données embarquées dans sys._MEIPASS ───
datas = []
if FRONTEND_DIST.exists():
    datas.append((str(FRONTEND_DIST), "frontend/dist"))
if CONFIGS_DIR.exists():
    datas.append((str(CONFIGS_DIR), "configs"))

# ─── Imports cachés nécessaires ───
hiddenimports = [
    "fastapi",
    "fastapi.staticfiles",
    "fastapi.responses",
    "fastapi.middleware.cors",
    "starlette",
    "starlette.staticfiles",
    "starlette.responses",
    "starlette.websockets",
    "starlette.middleware.cors",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.uvloop",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "websockets",
    "wsproto",
    "httptools",
    "uvloop",
    "anyio",
    "anyio._backends._asyncio",
    "nest_asyncio",
    "pydantic",
    "pydantic_core",
    "tomli",
    "tomli_w",
    "magic",
    "dotenv",
    "python_multipart",
]

# ─── Exclusions des paquets lourds inutiles (Gain > 3 Go) ───
excludes = [
    "PySide6", "PyQt5", "PyQt6", "shiboken6", "tkinter", "kivy",
    "torch", "torchvision", "torchaudio", "triton", "tensorflow", "keras",
    "transformers", "datasets", "onnx", "onnxruntime", "scipy", "sklearn",
    "scikit-learn", "spacy", "nltk", "gensim", "faiss", "langchain",
    "cv2", "PIL", "Pillow", "matplotlib", "seaborn", "pandas",
    "jupyter", "ipython", "notebook", "playwright", "selenium",
]

a = Analysis(
    [str(MEDIAKIT_ROOT / "api" / "run_api.py")],
    pathex=[str(SRC_ROOT), str(MEDIAKIT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="mediakit-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
