#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 22:30:29 2026

@author: hounsousamuel
"""

import re
import asyncio
import subprocess
from pydantic import BaseModel
from workbench.wb_utils.stop_process import kill_process_async

class BinaryNotFoundError(Exception):
    pass

class SuspiciousBinaryError(Exception):
    pass

class VersionParseError(Exception):
    pass

class Config(BaseModel):
    cmd: str
    marker: str
    tool_name: str


VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def get_binary_version(
    binary_path: str, 
    config: dict | Config, 
    check_version: bool = True,
    check_marker: bool = True
) -> tuple[int, int, int] | None:
    config = Config.model_validate(config)
    result = subprocess.run(
        [binary_path, config.cmd],
        capture_output=True, text=True, timeout=5,
    )
    output = (result.stdout + result.stderr).lower()
    
    if not check_marker:
        if result.returncode != 0:
            raise BinaryNotFoundError("Binaire {binary_path} introuvable !")
        
    idx = output.find(config.marker.lower())
    if idx == -1:
        raise SuspiciousBinaryError(f"Le fichier '{binary_path}' est suspect !")

    # On cherche le numéro de version juste APRÈS le marqueur, pas n'importe où
    zone = output[idx : idx + 100]
    match = VERSION_PATTERN.search(zone)
    if not match:
        if check_version:
            raise VersionParseError(f"Impossible de lire la version de {config.tool_name}")
        else:
            return None
    
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or 0))


async def get_binary_version_async(
    binary_path: str, 
    config: dict | Config, 
    check_version: bool = True,
    check_marker: bool = True
) -> tuple[int, int, int] | None:
    config = Config.model_validate(config)
    process = await asyncio.create_subprocess_exec(
        binary_path, config.cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=5)
    except asyncio.TimeoutError:
        await kill_process_async(process)
        raise
    
    output = (stdout_bytes + stderr_bytes).decode(errors="replace").lower()
    
    if not check_marker:
        if process.returncode != 0:
            raise BinaryNotFoundError("Binaire {binary_path} introuvable !")
            
    idx = output.find(config.marker.lower())
    if idx == -1:
        raise SuspiciousBinaryError(f"Le fichier '{binary_path}' est suspect !")

    # On cherche le numéro de version juste APRÈS le marqueur, pas n'importe où
    zone = output[idx : idx + 100]
    match = VERSION_PATTERN.search(zone)
    if not match:
        if check_version:
            raise VersionParseError(f"Impossible de lire la version de {config.tool_name}")
        else:
            return None

    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or 0))


def version_at_least(current: tuple, required: tuple) -> bool:
    length = max(len(current), len(required))
    current_padded = current + (0,) * (length - len(current))
    required_padded = required + (0,) * (length - len(required))
    return current_padded >= required_padded