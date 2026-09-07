#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 14:40:50 2026

@author: hounsousamuel
"""

import os
import tomli
import tomli_w
from dotenv import load_dotenv
from workbench.api.config import WbConfig

load_dotenv()

def load_config(path: str, config_cls: type[WbConfig] = WbConfig):
    if os.path.exists(path):
        with open(path, "rb") as f:
            conf = dict(tomli.load(f))
            keys = list(dict(config_cls.model_fields).keys())
            return WbConfig(**{k:v for k, v in conf.items() if k in keys})

def save_config(config: WbConfig, path: str):
    conf = dict(config.model_dump())
    to_save = {k : v for k, v in conf.items() if v is not None}
    with open(path, "wb") as f:
        tomli_w.dump(to_save, f)
    
    return True