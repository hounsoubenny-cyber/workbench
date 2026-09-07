#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep  5 11:47:38 2026

@author: hounsousamuel
"""

from typing import Dict
from workbench.specs.specs import ActionSpec
from workbench.specs.pipeline_spec import PipelineSpec

Spec = ActionSpec | PipelineSpec

def merge(*args: Dict[str, Spec]) -> Dict[str, Spec]:
    """
    Fusionne plusieurs dictionnaires de Specs en vérifiant l'unicité stricte des IDs.
    Lève un ValueError immédiat en cas de collision.
    """
    seen: Dict[str, Spec] = {}
    
    for arg in args:
        if not arg:
            continue
            
        for k, v in arg.items():
            # 1. Détection de collision
            if k in seen:
                raise ValueError(
                    f"💥 Collision d'identifiant détectée : deux Specs partagent l'ID '{k}'. "
                    f"Chaque action ou pipeline doit avoir un identifiant universellement unique."
                    f"({v!r} et {seen[k]!r})"
                )
            
            # 2. Vérification de cohérence clé == spec.id (optionnel mais ultra-utile)
            if hasattr(v, "id") and v.id != k:
                raise ValueError(
                    f"⚠️ Incohérence de nommage : la clé '{k}' ne correspond pas au champ 'id' de la spec '{v.id}'."
                )
                
            seen[k] = v
    
    return seen    