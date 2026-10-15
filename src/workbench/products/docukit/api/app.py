"""
Docukit — fabrique de l'application FastAPI.

`create_app()` ne fait RIEN à l'import et ne lit aucune variable
d'environnement tant qu'on ne lui en demande pas : c'est ce qui rend
l'application testable (TestClient) sans configuration préalable.

Défenses en profondeur, de l'extérieur vers l'intérieur :
  1. LocalOnlyGuard        — Host / Origin locaux (CSRF, DNS rebinding, WebSocket cross-site)
  2. SecurityHeaders       — CSP stricte, nosniff, pas de cache
  3. MaxBodySize           — plafond de taille des uploads
  4. routeur du socle      — validation Pydantic, sandbox des chemins, pas de shell
  5. `enable_advanced_jobs=False` — les drapeaux des binaires ne sont jamais choisis par le client
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from workbench.api.create_routes import create_router
from workbench.core.orchestrator import MainEngine
from workbench.core.subprocess.version_checker import get_binary_version_async
from workbench.wb_utils.job_file_cleaner import AsyncJobFileCleaner
from workbench.wb_utils.local_guard import LocalOnlyGuard, TAURI_ORIGINS

from workbench.products.docukit import PRODUCT_NAME, __version__
from workbench.products.docukit.api import config as dk_config
from workbench.products.docukit.api.env import Settings
from workbench.products.docukit.api.limits import MaxBodySizeMiddleware, SecurityHeadersMiddleware
from workbench.products.docukit.dk_utils.tools import (
    find_trusted_binary, pandoc_sandbox_supports, tesseract_languages,
)
from workbench.products.docukit.specs.utils import (
    BINARY_CONFIGS, INSTALL_HINTS, get_binary_config, get_catalog, get_spec,
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


async def tool_status(name: str) -> dict:
    """État d'un binaire : trouvé ?, version, et capacités qui changent l'UI."""
    status: dict = {"name": name, "find": False, "install": INSTALL_HINTS[name]}
    path = find_trusted_binary(name)
    if not path:
        return status
    try:
        version = await get_binary_version_async(
            binary_path=path, config=BINARY_CONFIGS[name],
            check_marker=True, check_version=True,
        )
    except Exception:
        return {**status, "reason": "binaire non reconnu"}

    status.update(find=True, version=".".join(map(str, version)) if version else None)
    # Capacités propres à certains outils (sondes mises en cache, hors boucle d'événements).
    if name == "tesseract":
        status["languages"] = sorted(await asyncio.to_thread(tesseract_languages))
    elif name == "pandoc":
        status["office_output"] = all([
            await asyncio.to_thread(pandoc_sandbox_supports, fmt)
            for fmt in ("docx", "odt", "epub")
        ])
    return status


def create_app(settings: Settings | None = None, frontend_dir: Path | None = None) -> FastAPI:
    settings = settings or Settings()
    frontend = Path(frontend_dir) if frontend_dir else FRONTEND_DIR

    config = dk_config.load(settings.config_path)
    orchestrator = MainEngine(config)
    cleaner = AsyncJobFileCleaner(default_ttl=15 * 60, every=60)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        orchestrator.start()
        cleaner.start()
        yield
        await orchestrator.stop()
        await cleaner.stop()

    app = FastAPI(title=PRODUCT_NAME, version=__version__, lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)

    router = create_router(
        orchestrator=orchestrator,
        job_file_cleaner=cleaner,
        show_specs_func=get_catalog,
        get_spec_func=get_spec,
        get_binary_config=get_binary_config,
        save_config_func=lambda cfg: dk_config.save(cfg, settings.config_path),
        enable_advanced_jobs=False,
    )
    app.include_router(router, prefix="/api")

    @app.get("/api/status")
    async def status():
        return {"status": "ok", "product": PRODUCT_NAME, "version": __version__}

    @app.get("/api/binary/{name}/check")
    async def check_tool(name: str):
        if name not in BINARY_CONFIGS:
            raise HTTPException(status_code=404, detail="Outil inconnu")
        return await tool_status(name)

    @app.get("/api/tools")
    async def tools():
        """Statut de tous les binaires en une requête (l'UI grise les actions indisponibles)."""
        results = await asyncio.gather(*(tool_status(n) for n in BINARY_CONFIGS))
        return {r["name"]: r for r in results}

    # Interface : StaticFiles borne l'accès au dossier (pas de traversée de chemin).
    if (frontend / "index.html").is_file():
        app.mount("/static", StaticFiles(directory=frontend), name="static")

        @app.get("/", include_in_schema=False)
        async def index():
            return FileResponse(frontend / "index.html")

    # Ordre d'ajout : le DERNIER ajouté est le plus EXTERNE.
    app.add_middleware(MaxBodySizeMiddleware, max_bytes=settings.max_upload_mb * 1024 * 1024)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        LocalOnlyGuard, extra_hosts=settings.allowed_hosts, extra_origins=TAURI_ORIGINS,
    )
    app.state.settings = settings
    app.state.orchestrator = orchestrator
    return app
