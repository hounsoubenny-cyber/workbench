#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 14:48:58 2026

@author: hounsousamuel
"""

from workbench.products.mediakit.api.env import CONFIG_PATH, PORT
from workbench.api.config_manager import save_config as _save_config, load_config as _load_config
from workbench.api.config import WbConfig

class WbMediakitConfig(WbConfig):
    pass

def load_config() -> WbMediakitConfig:
    return _load_config(CONFIG_PATH, WbMediakitConfig)

def save_config(config: WbMediakitConfig):
    return _save_config(config,CONFIG_PATH)
    
