#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 14:51:30 2026

@author: hounsousamuel
"""

import os
import socket
from dotenv import load_dotenv
from workbench.products.mediakit.api.errors import StartAppError

load_dotenv()

CONFIG_FILE_KEY = "WB_MEDIAKIT_CONFIG_FILE"
PORT_KEY = "WB_MEDIAKIT_PORT"
AUTO_CHOOSE_KEY = "WB_MEDIAKIT_AUTO_CHOOSE"

CONFIG_PATH = os.environ.get(CONFIG_FILE_KEY)
PORT = os.environ.get(PORT_KEY)
AUTO_CHOOSE = os.environ.get(AUTO_CHOOSE_KEY, "1").strip().lower() in ("1", "true", "True")

def check_path(path: str):
    if not path or not os.path.exists(path):
        raise StartAppError("Config Path is missing")

def check_port(port: int, check_is_open: bool = False):
    if not port:
        raise StartAppError(f"Port absent, variable {PORT_KEY!r} absente ou {AUTO_CHOOSE_KEY!r} mis à 0")
    
    try:
        port = int(port)
    except ValueError:
        raise StartAppError("Port invalide !")
    
    sock = socket.socket()
    r = sock.connect_ex(("127.0.0.1", port))
    sock.close()
    if r == 0:
        raise StartAppError("Port occupé !")
     
    return port

def find_open_port():
    import socket
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]
    
check_path(CONFIG_PATH)
if AUTO_CHOOSE:
    PORT = find_open_port()
else:
    PORT = check_port(PORT, check_is_open=True)