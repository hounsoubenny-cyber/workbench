#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug  3 00:30:38 2026

@author: hounsousamuel
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Optional, Deque
from fastapi import WebSocket, WebSocketDisconnect, WebSocketException
from collections import deque
from enum import StrEnum
from workbench.api.config import WbConfig

class JobStatus(StrEnum):
    RUNNING  =   "running"
    STOP     =   "stop"
    FAILED   =   "failed"
    FINISHED =   "finished"
    
class JobBufferManager:
    def __init__(self, config: WbConfig) -> None:
        self.ws: WebSocket | None = None
        self._buffer: Deque[dict] | None = None
        self._cleanup_task: asyncio.Task | None = None
        self.config = config
        self.status = JobStatus.RUNNING.value

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accepte la connexion WS.
        Si un buffer existe déjà → replay avant de commencer le stream live.
        """
        await websocket.accept()
        self.ws = websocket
        
        # Annuler un éventuel cleanup programmé (user reconnecte avant expiry)
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            

        # Replay du buffer existant
        if self._buffer:
            await self._replay(websocket, self._buffer)
        
        return True
    
    async def _send(self, ws: WebSocket, message: dict, raise_: bool = False):
        try:
            payload = json.dumps(message, default=str)   
        except Exception as e:
            print(f"⚠️ Message '{message.get('type')}' non sérialisable: {e!r}")
            return
        
        try:
            await ws.send_text(payload)
        except Exception as e:
            if raise_:
                raise e
            
            
    async def _replay(
        self,
        websocket:  WebSocket,
        buffer:     Deque[dict],
    ) -> None:
        if not self.status in (JobStatus.RUNNING, JobStatus.FINISHED):
            return 
        
        try:
            await websocket.send_json({
                "type":    "replay_start",
                "count":   len(buffer),
                "message": f"Replay de {len(buffer)} message(s) précédent(s)",
            })
            for msg in buffer:
                await self._send(websocket, msg)
            await websocket.send_json({"type": "replay_end"})
        except Exception:
            pass

    async def disconnect(self) -> None:
        self.status = JobStatus.FINISHED.value
        if self.ws:
            try:
                from starlette.websockets import WebSocketState
                if self.ws.client_state == WebSocketState.CONNECTED:
                    await self.ws.close()
            except Exception:
                pass
        self.ws = None
    
    def clear_buffer(self):
        if self._buffer:
            self._buffer.clear()
            
    async def callback(self, data: dict, *args, **kwargs):
        data.setdefault("type", "run_log")
        self.status = JobStatus.RUNNING.value
        await self.send(data)
        
    # ── Envoi de messages ───────────────────────────────────────────────────

    async def send(self, message: dict, store: bool = True) -> None:
        """
        Envoie un message au client connecté ET le met en buffer.
        Si le client est déconnecté, on continue de buffer silencieusement.
        """
        # Ajout timestamp si absent
        if "timestamp" not in message:
            message = {**message, "timestamp": datetime.now(tz=timezone.utc).isoformat()}

        # Buffer
        if store:
            if not self._buffer:
                self._buffer = deque(maxlen=self.config.buffer_max_lines)
            self._buffer.append(message) 

        # Tentative d'envoi live
        ws = self.ws
        if not ws:
            return

        if ws is not None:
            await self._send(ws, message)

    async def receive(self) -> Optional[dict]:
        """
        Attend le prochain message JSON envoyé par le client.
        Retourne None si la connexion est fermée.
        """
        ws = self.ws
        if ws is None:
            return None
        try:
            return await ws.receive_text()
        
        except (WebSocketDisconnect, WebSocketException) as e:
            await self.disconnect()
            raise e
            
        except Exception as e:
            raise e

    # ── Cleanup ─────────────────────────────────────────────────────────────

    async def schedule_cleanup(self, delay: int = None) -> None:
        """
        Programme la suppression du buffer N secondes après la fin d'une sim.
        Si le user se reconnecte avant l'expiry, le cleanup est annulé.
        """
        delay = delay or self.config.buffer_clear_delay
        async def _do_cleanup():
            try:
                await asyncio.sleep(delay)
                if self._buffer:
                    self._buffer.clear()
                self._buffer = None
            except asyncio.CancelledError:
                pass

        # Annuler l'ancien si existant
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            
        task = asyncio.create_task(_do_cleanup())
        self._cleanup_task = task

    def buffer_size(self) -> int:
        return len(self._buffer) if self._buffer else 0
