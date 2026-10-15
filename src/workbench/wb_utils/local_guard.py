"""
Workbench — garde pour les serveurs LOCAUX (Host + Origin).

Une application Workbench installée écoute sur 127.0.0.1 : personne d'autre
sur le réseau ne peut s'y connecter... mais n'importe quelle PAGE WEB ouverte
dans le navigateur de l'utilisateur le peut :

  - requête cross-origin (CSRF) : `fetch("http://127.0.0.1:PORT/api/job/create",
    {method: "POST", body: formData})` part sans pré-vol CORS (« requête
    simple ») et le serveur l'exécute — la page ne lit pas la réponse mais le
    job a tourné (voire `/job/advanced/create` : commande arbitraire) ;
  - WebSocket cross-site : aucun contrôle CORS sur les WebSockets ;
  - DNS rebinding : `evil.com` re-résolu vers 127.0.0.1 devient « same-origin ».

Ce middleware ASGI ferme ces trois portes :
  - le header `Host` doit désigner la machine locale (anti-rebinding) ;
  - si un header `Origin` est présent (les navigateurs l'envoient sur les
    requêtes cross-origin et les WebSockets), il doit être local lui aussi.
Les clients hors navigateur (curl, tests, sidecar) n'envoient pas `Origin` et
restent acceptés tant que `Host` est local.
"""

import json
from typing import Iterable
from urllib.parse import urlsplit

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
# Webviews Tauri : `tauri://localhost` (macOS / Linux), `http(s)://tauri.localhost` (Windows).
TAURI_ORIGINS = frozenset({
    "tauri://localhost", "http://tauri.localhost", "https://tauri.localhost",
})


def _hostname(host_header: str) -> str:
    """`Host: 127.0.0.1:8000` -> `127.0.0.1` ; `[::1]:8000` -> `::1`."""
    host = host_header.strip().lower()
    if host.startswith("["):
        host = host[1:].split("]", 1)[0]
    elif host.count(":") == 1:
        host = host.split(":", 1)[0]
    return host.rstrip(".")


class LocalOnlyGuard:
    def __init__(
        self,
        app,
        extra_hosts: Iterable[str] = (),
        extra_origins: Iterable[str] = TAURI_ORIGINS,
    ):
        self.app = app
        self.hosts = LOOPBACK_HOSTS | {h.lower() for h in extra_hosts}
        self.origins = {o.lower().rstrip("/") for o in extra_origins}

    def _refusal(self, headers: dict[str, str]) -> str | None:
        host = headers.get("host")
        if not host or _hostname(host) not in self.hosts:
            return "Host non autorisé"
        origin = headers.get("origin")
        if origin is None:
            return None
        origin = origin.strip().lower().rstrip("/")
        if origin in self.origins:
            return None
        parts = urlsplit(origin)
        if parts.scheme in ("http", "https") and (parts.hostname or "") in self.hosts:
            return None
        return "Origin non autorisé"

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers: dict[str, str] = {}
        for key, value in scope.get("headers", []):
            headers.setdefault(key.decode("latin-1").lower(), value.decode("latin-1"))

        reason = self._refusal(headers)
        if reason is None:
            await self.app(scope, receive, send)
            return

        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008, "reason": reason})
            return

        body = json.dumps({"error_code": "FORBIDDEN_ORIGIN", "message": reason}).encode()
        await send({
            "type": "http.response.start", "status": 403,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})
