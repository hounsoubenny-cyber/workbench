"""
Docukit — lanceur : démarre le serveur local, annonce le port, ouvre le navigateur.

Protocole identique à Mediakit : la ligne `WORKBENCH_PORT=<port>` sur stdout
permet à une coquille (Tauri, script) de retrouver le port choisi.
"""

import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from workbench.products.docukit import PRODUCT_NAME, __version__
from workbench.products.docukit.api.app import create_app
from workbench.products.docukit.api.env import Settings

STARTUP_TIMEOUT = 30.0   # secondes


def find_free_port(host: str) -> int:
    """Demande un port libre au système (le port 0 est attribué par l'OS)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


def run(settings: Settings | None = None) -> int:
    settings = settings or Settings.from_env()
    port = settings.port or find_free_port(settings.host)
    app = create_app(settings)

    server = uvicorn.Server(uvicorn.Config(
        app, host=settings.host, port=port, log_level="warning", access_log=False,
    ))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Attente du démarrage — sans boucle active, et avec une issue de secours.
    deadline = time.monotonic() + STARTUP_TIMEOUT
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            print(f"❌ {PRODUCT_NAME} n'a pas pu démarrer sur {settings.host}:{port}.", file=sys.stderr)
            return 1
        time.sleep(0.05)

    url = f"http://{'127.0.0.1' if settings.host in ('0.0.0.0', '') else settings.host}:{port}"
    print(f"{PRODUCT_NAME} {__version__} — {url}")
    print(f"WORKBENCH_PORT={port}", flush=True)
    if settings.open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            print(f"👉 Ouvrez manuellement : {url}")

    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.should_exit = True
        thread.join(5)
    return 0
