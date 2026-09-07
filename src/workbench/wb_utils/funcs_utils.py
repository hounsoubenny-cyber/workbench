#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 18:05:58 2026

@author: hounsousamuel
"""

import asyncio

async def exec_func(f, *args, **kwargs):
    r = f(*args, **kwargs)
    if asyncio.iscoroutine(r):
        r = await r
    
    return r