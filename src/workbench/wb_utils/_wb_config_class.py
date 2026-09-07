#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 23:44:19 2026

@author: hounsousamuel
"""

class WbWsConfig:
    def __init__(
        self,
        buffer_max_lines: int | None = 5_000,
        buffer_clear_delay: float = 120,
    ):
        self.buffer_clear_delay = buffer_clear_delay
        self.buffer_max_lines = buffer_max_lines
        