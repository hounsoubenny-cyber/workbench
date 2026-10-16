"""
Docukit — middlewares ASGI : taille maximale des requêtes, en-têtes de sécurité.

Écrits en ASGI pur (pas de BaseHTTPMiddleware) : compatibles avec les
téléchargements en streaming et les WebSockets.
"""

import json


class RequestTooLarge(Exception):
    pass


class MaxBodySizeMiddleware:
    """
    Refuse (413) toute requête dont le corps dépasse `max_bytes`.

    Deux protections : l'en-tête Content-Length (refus immédiat, avant de lire
    quoi que ce soit) ET un compteur sur le flux réel (un client peut mentir
    sur Content-Length ou envoyer en `chunked` sans l'indiquer).
    """

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        for key, value in scope.get("headers", []):
            if key == b"content-length":
                try:
                    if int(value) > self.max_bytes:
                        await self._reject(send)
                        return
                except ValueError:
                    pass
                break

        received = 0
        started = False

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise RequestTooLarge
            return message

        async def tracking_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except RequestTooLarge:
            if not started:
                await self._reject(send)

    async def _reject(self, send):
        body = json.dumps({
            "error_code": "REQUEST_TOO_LARGE",
            "message": f"Fichier trop volumineux (limite : {self.max_bytes // (1024 * 1024)} Mo).",
        }).encode()
        await send({
            "type": "http.response.start", "status": 413,
            "headers": [(b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode())],
        })
        await send({"type": "http.response.body", "body": body})


# `blob:` : l'interface prévisualise le résultat (PDF / image) via une URL blob
# locale. Aucun script, style ni ressource externe : tout est servi par l'app.
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self'",
    "img-src 'self' blob: data:",
    "connect-src 'self' ws://127.0.0.1:* ws://localhost:*",
    "frame-src blob:",
    "object-src blob:",
    "base-uri 'none'",
    "form-action 'none'",
    "frame-ancestors 'none'",
])

SECURITY_HEADERS = [
    (b"content-security-policy", CSP.encode()),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"cache-control", b"no-store"),
]


class SecurityHeadersMiddleware:
    """Ajoute CSP & co. à toute réponse HTTP (sans écraser un header déjà posé)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                existing = {k.lower() for k, _ in message.get("headers", [])}
                message = {
                    **message,
                    "headers": [
                        *message.get("headers", []),
                        *[(k, v) for k, v in SECURITY_HEADERS if k not in existing],
                    ],
                }
            await send(message)

        await self.app(scope, receive, send_with_headers)
