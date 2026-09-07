#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 16:54:17 2026

@author: hounsousamuel
"""

import asyncio

def my_callback(task):
    """Callback exécuté quand la tâche se termine"""
    print(f"✅ Tâche terminée !")
    print(f"  - Done: {task.done()}")
    print(f"  - Cancelled: {task.cancelled()}")
    
    if task.cancelled():
        print(f"  - Statut: Annulée")
    elif task.exception():
        print(f"  - Statut: Erreur - {task.exception()}")
    else:
        print(f"  - Statut: Succès - Résultat: {task.result()}")

async def main():
    # La tâche peut se terminer de 3 façons
    
    # 1. Succès
    task1 = asyncio.create_task(success())
    task1.add_done_callback(my_callback)
    
    # 2. Erreur
    task2 = asyncio.create_task(fail())
    task2.add_done_callback(my_callback)
    
    # 3. Annulation
    task3 = asyncio.create_task(async_sleep())
    task3.add_done_callback(my_callback)
    task3.cancel()
    
    # Attendre que tout se termine
    await asyncio.sleep(0.2)

async def success():
    return "OK"

async def fail():
    raise ValueError("Erreur")

async def async_sleep():
    await asyncio.sleep(10)

asyncio.run(main())