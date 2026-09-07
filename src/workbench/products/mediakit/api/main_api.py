#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 14:31:19 2026

@author: hounsousamuel
"""

import os
import re
import sys
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from workbench.api.create_routes import (  # noqa
    create_router, start, stop, 
    _server_error
) 
from workbench.api.config import StartConfig
from workbench.core.orchestrator import MainEngine
from workbench.wb_utils.job_file_cleaner import AsyncJobFileCleaner
from workbench.products.mediakit.api.config import load_config, save_config, PORT
from workbench.products.mediakit.specs.utils import get_catalog, get_spec, get_binary_config
from workbench.wb_utils.error_mapper import map_orchestrator_error # noqa
from workbench.core.subprocess.version_checker import (
    get_binary_version_async,
    BinaryNotFoundError
)

__version__ = "1.0.0"
__author__ = "HOUNSOU Benny"

if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS
    FRONTEND_DIR = os.path.abspath(os.path.join(
        BASE_PATH,
        "frontend"
    ))
else:
    BASE_PATH = os.path.dirname(__file__)
    FRONTEND_DIR = os.path.abspath(os.path.join(
        BASE_PATH,
        "..", "frontend"
    ))
    
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")
INDEX_FILE = os.path.join(DIST_DIR, "index.html")
FRONTEND_EXISTS = os.path.isdir(DIST_DIR) and os.path.isfile(INDEX_FILE)

start_config = StartConfig(
    server=None,
    host="0.0.0.0",
    port=PORT,
    log_level=logging.ERROR,
    access_log=False
)

config = load_config()
orchestrator = MainEngine(config)
job_file_cleaner = AsyncJobFileCleaner(default_ttl=config.file_ttl)

def get_orchestrator(app: FastAPI) -> MainEngine:
    return app.state.orchestrator

def get_job_file_cleaner(app: FastAPI) -> AsyncJobFileCleaner:
    return app.state.job_file_cleaner

async def lifespan_start(app: FastAPI):
    app.state.orchestrator = orchestrator
    app.state.job_file_cleaner = job_file_cleaner
    app.state.config = config
    job_file_cleaner.start()
    orchestrator.start()
    print("Mediakit démarré !")
    return

async def lifespan_end(app: FastAPI):
    print("Mediakit stoppé !")
    await get_orchestrator(app).stop(stop_tasks=True)
    await get_job_file_cleaner(app).stop()
    return

@asynccontextmanager
async def lifespan(app: FastAPI):
    await lifespan_start(app)    
    yield
    await lifespan_end(app)
    
app = FastAPI(
    version=__version__,
    title="WorkBench Mediakit",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_methods=["POST", "GET", "HEAD"],
    allow_origins=[
        f"http://localhost:{PORT}",
        f"http://127.0.0.1:{PORT}",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "https://fonts.googleapis.com",
        "https://fonts.gstatic.com"
    ]
)

if FRONTEND_EXISTS:
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="frontend_assets")
    
@app.get("/api/binary/{name}/check")
async def check_tool(request: Request, name: str):
    try:
        try:
            config = get_binary_config(name)
        except KeyError:
            raise BinaryNotFoundError(name) from None
            
        if not name:
            raise BinaryNotFoundError(name)
            
        await get_binary_version_async(
            binary_path=name,
            config=config,
            check_marker=True,
            check_version=False
        )
        return {"find": True}
    
    except HTTPException:
        raise
    
    except Exception as e:
        raise _server_error(e)
    
router = create_router(
    orchestrator=orchestrator,
    job_file_cleaner=job_file_cleaner,
    show_specs_func=get_catalog,
    get_spec_func=get_spec,
    get_binary_config=get_binary_config,
    save_config_func=save_config
)
app.include_router(
    router=router,
    prefix="/api",
)
 
@app.get("/api/status")
def status():
    return {"status": "ok"}


@app.get("/")
def home():
    if not FRONTEND_EXISTS:
        return {"status": "ok"}
    
    return FileResponse(INDEX_FILE)

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Sert le frontend buildé (Vite) et gère le fallback SPA pour React Router.

    Toute route qui ne correspond ni à l'API ni à un fichier statique
    connu retombe sur index.html, pour laisser React Router gérer le
    routing côté client.

    Args:
        full_path (str): Le chemin complet demandé.

    Returns:
        FileResponse: Le fichier demandé s'il existe dans dist/ (ex: favicon.ico
            copié depuis public/ à la racine du build), sinon index.html.

    Raises:
        HTTPException: 404 si le frontend n'est pas buildé.
    """
    if not FRONTEND_EXISTS:
        raise HTTPException(status_code=404, detail="Frontend non buildé")

    # Fichiers copiés tels quels depuis public/ à la racine de dist/
    # (favicon.ico, robots.txt, manifest.json, images référencées en chemin direct...)
    candidate = os.path.join(DIST_DIR, full_path)
    if full_path and os.path.isfile(candidate):
        return FileResponse(candidate)

    return FileResponse(INDEX_FILE)
