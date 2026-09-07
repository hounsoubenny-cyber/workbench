#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 23:46:26 2026

@author: hounsousamuel
"""

"""
Workbench — point d'entree ASGI "pour de vrai".

A la difference de test_api_client_full.py (TestClient, in-process, pas de
vrai reseau), ce module expose une vraie `app` FastAPI, lancable par un vrai
serveur uvicorn qui ecoute sur un vrai port TCP, avec le catalogue reel
(workbench/examples/demo_catalog.py).

Lancement direct :
    python3 -m uvicorn workbench.api.server_app:app --port 8000

C'est ce module que test_live_client.py demarre en sous-processus pour le
test "interactif / vivant".
"""

from fastapi import FastAPI

from workbench.api.config import WbConfig
from workbench.core.orchestrator import MainEngine
from workbench.wb_utils.job_file_cleaner import AsyncJobFileCleaner
from workbench.api.create_routes import create_router
from workbench.examples.demo_catalog import get_spec, show_catalog

config = WbConfig(max_concurrent_job=5, buffer_max_lines=2_000, buffer_clear_delay=15)
orchestrator = MainEngine(config)
job_file_cleaner = AsyncJobFileCleaner(default_ttl=300, every=30)

router = create_router(
    orchestrator=orchestrator,
    show_specs_func=show_catalog,
    get_spec_func=get_spec,
    job_file_cleaner=job_file_cleaner,
)

app = FastAPI(title="Workbench (demo)")
app.include_router(router)


@app.on_event("startup")
async def _startup():
    orchestrator.start()
    job_file_cleaner.start()


@app.on_event("shutdown")
async def _shutdown():
    await orchestrator.stop()
    await job_file_cleaner.stop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)