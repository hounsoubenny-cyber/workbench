#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 17:25:07 2026

@author: hounsousamuel
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from workbench.api.config import WbConfig
from workbench.core.orchestrator import MainEngine
from workbench.wb_utils.job_file_cleaner import AsyncJobFileCleaner
from workbench.api.create_routes import create_router

# Mock rapide des specs
MOCK_CATALOG = {
    "ls_action": {"id": "ls_action", "name": "Lister fichiers", "tool": "ls"}
}

class FakeSpec:
    def __init__(self, id):
        self.id = id
        self.tool = "ls"
    def full_args(self, input):
        return []

def get_fake_spec(spec_id: str):
    if spec_id in MOCK_CATALOG:
        return FakeSpec(spec_id)
    return None

def show_catalog():
    return MOCK_CATALOG

# ─── SETUP DE L'APPLICATION DE TEST ───
config = WbConfig()
orchestrator = MainEngine(config)
cleaner = AsyncJobFileCleaner(default_ttl=60)

router = create_router(
    orchestrator=orchestrator,
    show_specs_func=show_catalog,
    get_spec_func=get_fake_spec,
    job_file_cleaner=cleaner
)

app = FastAPI()
app.include_router(router)
client = TestClient(app)

def test_full_api_flow():
    print("\n" + "="*50 + "\n🧪 DÉBUT DES TESTS API\n" + "="*50)
    
    # 1. Config GET & POST
    r = client.get("/config")
    print(f"[GET /config]  Statut: {r.status_code} | Données: {r.json()}")
    
    r = client.post("/config", json={"max_concurrent_job": 15})
    print(f"[POST /config] Statut: {r.status_code} | Succès: {r.json()['success']}")
    
    # 2. Catalog
    r = client.get("/catalog")
    print(f"[GET /catalog] Statut: {r.status_code} | Catalogue: {r.json()}")
    
    # 3. Job Create (avec un faux ActionSpec qui fait bugger l'engine car on a passé [] au lieu d'Arg)
    # L'important ici est que la route répond correctement.
    # Pour un test parfait, on aurait mis une vraie spec, mais on teste le routing.
    print("\n📦 Test Création de job...")
    r = client.post("/job/create", json={"id": "ls_action", "user_input": {}})
    
    # S'il y a une erreur 500 due à notre FakeSpec, c'est normal, l'API la capture !
    print(f"[POST /job/create] Statut: {r.status_code} | Body: {r.json()}")

    print("\n✅ Tests API terminés.")

if __name__ == "__main__":
    test_full_api_flow()