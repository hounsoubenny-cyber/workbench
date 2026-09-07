#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 00:04:11 2026

@author: hounsousamuel
"""


import uvicorn
import logging # noqa
from pydantic import BaseModel, Field, ConfigDict

class StartConfig(BaseModel):
    server: None | uvicorn.Server
    host: str = "0.0.0.0"
    port: int = 8000
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)
    access_log: bool = True
    log_level: int | None = None #logging.WARNING
    
class WbConfig(BaseModel):
    max_concurrent_job: int = Field(
        default=10, description="Nombre max de jobs simultanés"
    )
    buffer_max_lines: int | None = Field(
        default=5_000, description="Nombre max de ligne dans les buffer job"
    )
    buffer_clear_delay: float = Field(
        default=120,
        description="Temps de suppression du buffer après deconnexion."
    )
    file_ttl: float = 60 * 60
    
        