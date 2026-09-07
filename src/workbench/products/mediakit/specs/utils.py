#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:51:38 2026

@author: hounsousamuel
"""
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workbench Mediakit — Utilitaires du catalogue et résolution des specs.
"""

from workbench.products.mediakit.specs.ffmpeg.actions import FFMPEG_CATALOG
from workbench.products.mediakit.specs.ffmpeg.base_spec import FFMPEG_CONFIG
from workbench.products.mediakit.specs.sox.actions import SOX_CATALOG
from workbench.products.mediakit.specs.sox.base_spec import SOX_CONFIG
from workbench.products.mediakit.specs.magick.actions import MAGICK_CATALOG
from workbench.products.mediakit.specs.magick.base_spec import MAGICK_CONFIG
from workbench.products.mediakit.specs.pipelines import PIPELINE_CATALOG
from workbench.specs.pipeline_spec import PipelineSpec
from workbench.wb_utils.merger import merge

ACTION_ALL_CAT = merge(
    FFMPEG_CATALOG["all_cat"],
    SOX_CATALOG["all_cat"],
    MAGICK_CATALOG["all_cat"]
)

PIPELINE_ALL_CAT = merge(
    PIPELINE_CATALOG["all_cat"],
)

ALL_CAT = merge(
    ACTION_ALL_CAT,
    PIPELINE_ALL_CAT
)

def summarize_spec(spec) -> dict:
    """Convertit une Spec (ActionSpec ou PipelineSpec) en dict JSON-compatible."""
    if isinstance(spec, PipelineSpec):
        return {
            "id": spec.id,
            "label": spec.label,
            "type": "pipeline",
            "steps": [
                {"id": s.id, "tool": s.action.tool, "action_id": s.action.id, "label": s.action.label}
                for s in spec.steps
            ],
        }
    return {
        "id": spec.id,
        "label": spec.label,
        "type": "action",
        "tool": spec.tool,
        "min_version": spec.min_version,
    }

def _summarize_catalog_dict(catalog_dict: dict) -> dict:
    """Résume récursivement un catalogue d'outil (all_cat + categories)."""
    return {
        "all_cat": {k: summarize_spec(v) for k, v in catalog_dict.get("all_cat", {}).items()},
        "categories": {
            cat_name: {
                "description": cat_info.get("description", ""),
                "values": {k: summarize_spec(v) for k, v in cat_info.get("values", {}).items()}
            }
            for cat_name, cat_info in catalog_dict.get("categories", {}).items()
        }
    }

def get_catalog(*args, **kwargs) -> dict:
    """Retourne le catalogue complet 100% sérialisable en JSON pour GET /api/catalog."""
    return {
        "action_specs": {
            "ffmpeg": _summarize_catalog_dict(FFMPEG_CATALOG),
            "magick": _summarize_catalog_dict(MAGICK_CATALOG),
            "sox": _summarize_catalog_dict(SOX_CATALOG),
            "all_cat": {k: summarize_spec(v) for k, v in ACTION_ALL_CAT.items()}
        },
        "pipeline_specs": _summarize_catalog_dict(PIPELINE_CATALOG)
    }

def get_spec(spec_id: str):
    """Retourne l'objet Spec complet avec ses fonctions pour le CommandEngine."""
    return ALL_CAT.get(spec_id, None)

BINARY_CONFS = {
    "ffmpeg": FFMPEG_CONFIG,
    "sox": SOX_CONFIG,
    "magick": MAGICK_CONFIG
}

def get_binary_config(tool_name: str):
    return BINARY_CONFS[tool_name]