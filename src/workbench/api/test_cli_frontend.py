#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 17:30:56 2026

@author: hounsousamuel
"""

import json
import asyncio
import aiohttp
from typing import Dict, Any

API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

async def fetch_catalog(session: aiohttp.ClientSession) -> Dict:
    print("\n📦 Récupération du catalogue...")
    async with session.get(f"{API_URL}/catalog") as resp:
        if resp.status == 200:
            return await resp.json()
        else:
            print(f"❌ Erreur {resp.status} : {await resp.text()}")
            return {}

async def create_job(session: aiohttp.ClientSession, spec_id: str, inputs: dict) -> Dict:
    print(f"\n🚀 Lancement du job '{spec_id}'...")
    payload = {"id": spec_id, "user_input": inputs, "timeout": 30.0}
    async with session.post(f"{API_URL}/job/create", json=payload) as resp:
        if resp.status == 200:
            data = await resp.json()
            print(f"✅ Job créé avec succès ! ID: {data['job_id']}")
            return data
        else:
            print(f"❌ Erreur création job : {await resp.text()}")
            return {}

async def stream_logs(job_id: str):
    """Se connecte au WebSocket et affiche les logs en direct comme un vrai Terminal."""
    print(f"\n📡 Connexion WebSocket pour le job {job_id}...\n" + "-"*50)
    
    import websockets # pip install websockets
    ws_uri = f"{WS_URL}/job/ws/logs?job_id={job_id}"
    
    try:
        async with websockets.connect(ws_uri) as ws:
            while True:
                msg_str = await ws.recv()
                msg = json.loads(msg_str)
                
                msg_type = msg.get("type")
                
                if msg_type == "run_log":
                    stream = msg.get("stream", "info")
                    text = msg.get("text", "").rstrip()
                    prefix = "🟢 STDOUT" if stream == "stdout" else "🔴 STDERR"
                    print(f"[{prefix}] {text}")
                    
                elif msg_type == "job_result":
                    print("-" * 50)
                    print(f"🏁 RÉSULTAT FINAL DU JOB :")
                    res = msg.get("result", {})
                    print(f"Code de retour : {res.get('returncode')}")
                    print(f"Succès         : {res.get('ok')}")
                    
                elif msg_type == "job_end":
                    print("🚪 Fin de la connexion (Job terminé).")
                    break
                else:
                    print(f"[SYS] {msg}")
                    
    except websockets.exceptions.ConnectionClosed:
        print("🔌 Connexion fermée par le serveur.")
    except Exception as e:
        print(f"⚠️ Erreur WS : {e}")

async def download_file(session: aiohttp.ClientSession, workdir: str, filename: str):
    print(f"\n📥 Tentative de téléchargement de {filename}...")
    url = f"{API_URL}/download?workdir={workdir}&path={filename}"
    async with session.get(url) as resp:
        if resp.status == 200:
            content = await resp.read()
            print(f"✅ Fichier téléchargé avec succès ({len(content)} octets) !")
            print("📜 Aperçu du contenu :\n", content.decode(errors="ignore")[:200])
        else:
            print(f"❌ Erreur de téléchargement : {await resp.text()}")

async def interactive_frontend():
    print("=" * 60)
    print("🖥️  WORKBENCH - TERMINAL FRONTEND INTERACTIF")
    print("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        # 1. On récupère les actions possibles (Katalog)
        # Supposons que tu as une action "ls_action" sur ton serveur
        spec_id = input("\n👉 Entrez l'ID du spec à lancer (ex: 'list_directory') : ").strip()
        if not spec_id:
            return
            
        print("💡 Appuyez sur Entrée pour utiliser les valeurs par défaut.")
        show_all = input("Montrer les fichiers cachés (True/False) [True] : ") or "True"
        
        inputs = {
            "show_all": show_all.lower() == "true",
            "long_format": True
        }
        
        # 2. Création du Job via API HTTP
        job_data = await create_job(session, spec_id, inputs)
        if not job_data:
            return
            
        job_id = job_data["job_id"]
        workdir = job_data["workdir"]
        
        # 3. Affichage en direct via WebSockets
        await stream_logs(job_id)
        
        # 4. Téléchargement d'un fichier produit
        dl = input("\n👉 Voulez-vous télécharger le fichier de sortie (ex: ls_output.txt) ? (y/N) : ")
        if dl.lower() == 'y':
            file_name = input("Nom du fichier : ").strip()
            await download_file(session, workdir, file_name)

if __name__ == "__main__":
    try:
        asyncio.run(interactive_frontend())
    except KeyboardInterrupt:
        print("\n👋 Au revoir !")