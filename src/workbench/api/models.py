#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 00:07:23 2026

@author: hounsousamuel
"""

from pydantic import BaseModel, Field

class UpdateConfigData(BaseModel):
    max_concurrent_job: int | None = Field(
        default=None, description="Nombre max de jobs simultanés"
    )
    buffer_max_lines: int | None = Field(
        default=None, description="Nombre max de ligne dans les buffer job"
    )
    buffer_clear_delay: float | None = Field(
        default=None,
        description="Temps de suppression du buffer après deconnexion."
    )
    file_ttl: float | None = None

class CreateJobWithCatalogData(BaseModel):
    id: str
    user_input: dict
    timeout: float | None = None