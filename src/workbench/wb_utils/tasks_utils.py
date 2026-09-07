#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 18:07:08 2026

@author: hounsousamuel
"""

import asyncio

async def stop_task(t: asyncio.Task, timeout: float | None = None):
    if not t.done():
        t.cancel()

    try:
        if timeout is None:
            await t
        else:
            await asyncio.wait_for(asyncio.shield(t), timeout)
    except asyncio.CancelledError:
        pass
    except asyncio.TimeoutError:
        pass