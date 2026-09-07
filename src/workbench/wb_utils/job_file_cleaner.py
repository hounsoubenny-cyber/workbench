#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 17:56:04 2026

@author: hounsousamuel
"""

import time
import asyncio
import threading
import shutil
from pathlib import Path
from dataclasses import dataclass
from workbench.wb_utils.tasks_utils import stop_task


@dataclass
class TrackedItem:
    path: str
    created_at: float
    ttl: float
    is_dir: bool
    empty_count: int = 0


class JobFileCleaner:
    def __init__(self, default_ttl: float, every: float = 60, auto_start: bool = False):
        self.default_ttl = default_ttl
        self.tracked_items: dict[str, TrackedItem] = {}
        self._lock = threading.Lock()
        self.thread: threading.Thread | None = None
        self.task: asyncio.Task | None = None
        self.every = every
        if auto_start:
            self.start()

    def register(self, path: Path | str, is_dir: bool = False, ttl: float | None = None):
        """
        Enregistre un fichier ou dossier à surveiller.
        Si ttl n'est pas fourni, utilise self.default_ttl.
        """
        actual_ttl = ttl if ttl is not None else self.default_ttl
        with self._lock:
            self.tracked_items[str(path)] = TrackedItem(
                path=str(path),
                created_at=time.time(),
                ttl=actual_ttl,
                is_dir=is_dir
            )

    def _delete_item(self, path_str: str, force: bool = False) -> bool:
        """
        force=True : Supprime de force (shutil.rmtree) même si le dossier n'est pas vide.
        force=False : Supprime un dossier UNIQUEMENT s'il est vide.
        """
        try:
            p = Path(path_str)
            if p.exists():
                if p.is_file():
                    p.unlink(missing_ok=True)
                    
                elif p.is_dir():
                    if force:
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        if not any(p.iterdir()):
                            p.rmdir()
                        else:
                            return False  

            with self._lock:
                self.tracked_items.pop(path_str, None)
            return True
            
        except Exception as e:
            print(f"Erreur lors du nettoyage de {path_str!r}: {e!r}")
            return False

    def mark_downloaded(self, file_path: Path | str):
        """Supprime immédiatement un fichier spécifique (ex: après l'avoir streamé au client)."""
        self._delete_item(str(file_path), force=True)

    def _cleanup_cycle(self):
        """Logique centrale de nettoyage exécutée à chaque itération."""
        now = time.time()
        to_delete_force = []
        to_delete_empty = []

        with self._lock:
            for path_str, item in self.tracked_items.items():
                if now - item.created_at > item.ttl:
                    to_delete_force.append(path_str)
                elif item.is_dir:
                    to_delete_empty.append(path_str)

        for path_str in to_delete_force:
            self._delete_item(path_str, force=True)
            
        for path_str in to_delete_empty:
            self._delete_item(path_str, force=False)

    def _loop(self):
        while True:
            try:
                self._cleanup_cycle()
            except Exception as e:
                print(f"⚠️ Cleanup cycle error: {e!r}")
            
            time.sleep(self.every)
            
    def start(self):
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return True

    def stop(self, timeout: float | None = 2.0):
        if self.thread:
            self.thread.join(timeout)
        return True

    def is_tracked(self, path):
        return path in self.tracked_items
    
    
class AsyncJobFileCleaner(JobFileCleaner):
    def __init__(self, default_ttl: float, every: float = 60):
        super().__init__(default_ttl=default_ttl, every=every, auto_start=False)

    async def _loop(self):
        while True:
            try:
                self._cleanup_cycle()
            except Exception as e:
                print(f"⚠️ Cleanup cycle error: {e!r}")
            
            await asyncio.sleep(self.every)
            
    def start(self):
        self.task = asyncio.create_task(self._loop())
        return True

    async def stop(self, timeout: float | None = None):
        if self.task:
            await stop_task(self.task, timeout)