#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 08:19:58 2026

@author: hounsousamuel
"""

import sys
import inspect
from typing import Type
from workbench.specs.specs import ActionSpec
from workbench.specs.pipeline_spec import PipelineSpec

def collect_specs(module_name: str, spec_type: Type = ActionSpec) -> dict:
    """
    Construit le dict {id: spec} en scannant les ActionSpec définis dans le
    module `module_name` — pas besoin de maintenir une liste manuelle en
    plus. Volontairement limité à UN module (pas de scan de tout le
    package) : plus prévisible, et une erreur reste localisée à un seul
    fichier.
    """
    module = sys.modules[module_name]
    target_type = spec_type or (ActionSpec, PipelineSpec)
    
    specs = [
        obj for _, obj in inspect.getmembers(module) 
        if isinstance(obj, target_type)
    ]
 
    seen: dict[str, ActionSpec | PipelineSpec] = {}
    for spec in specs:
        if spec.id in seen:
            raise ValueError(
                f"Deux Spec partagent le même id '{spec.id}' dans {module_name} "
                f"— sans ce check, l'un écraserait l'autre silencieusement."
                f"({spec!r} et {seen[spec.id]!r})"
            )
        seen[spec.id] = spec
    return seen