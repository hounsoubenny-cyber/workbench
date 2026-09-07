#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:25:48 2026

@author: hounsousamuel
"""

"""
Workbench — Traduction et introspection complète d'un modèle Pydantic
via model_fields pour l'auto-génération d'interfaces graphiques (GUI).
"""

import json
import types
from enum import Enum
from pydantic import BaseModel, Field
from pydantic_core import PydanticUndefined
from typing import (
    Any, Dict, List, Literal, Union, Optional, get_args, get_origin
)
from workbench.specs.uploads import _MARKER_KEY as _UPLOAD_MARKER, UploadRef


def _extract_type_and_choices(annotation: Any) -> tuple[str, list[Any] | None]:
    """
    Analyse l'annotation Python/Pydantic pour déterminer :
    - Le type UI simplifié (string, integer, float, boolean, enum, list, etc.)
    - Les choix possibles s'il s'agit d'un Literal ou d'un Enum.
    """
    origin = get_origin(annotation)
    args = get_args(annotation)

    # 1. Gestion des Optional[...] / Union[T, None]
    if origin is Union or isinstance(annotation, types.UnionType):
        # Exclut NoneType
        non_none_args = [a for a in args if a is not type(None)]
        if len(non_none_args) == 1:
            return _extract_type_and_choices(non_none_args[0])

    # 2. Gestion des Literal["a", "b", "c"]
    if origin is Literal:
        return "enum", list(args)

    # 3. Gestion des Enum Python
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return "enum", [e.value for e in annotation]

    # 4. Gestion des List[...] / list[str]
    if origin in (list, List):
        sub_type = "any"
        if args:
            sub_type, _ = _extract_type_and_choices(args[0])
        return f"list[{sub_type}]", None

    # 5. Types primitifs
    if annotation in (str, "str"):
        return "string", None
    if annotation in (int, "int"):
        return "integer", None
    if annotation in (float, "float"):
        return "float", None
    if annotation in (bool, "bool"):
        return "boolean", None

    return getattr(annotation, "__name__", str(annotation)), None


def _extract_constraints(field_info) -> Dict[str, Any]:
    """Extrait les contraintes Pydantic (ge, le, gt, lt, min_length, max_length)."""
    constraints = {}
    
    # Vérification directe des métadonnées de contrainte Pydantic v2
    for meta in getattr(field_info, "metadata", []):
        for attr in ("ge", "le", "gt", "lt", "min_length", "max_length"):
            val = getattr(meta, attr, None)
            if val is not None:
                constraints[attr] = val

    return constraints


def model_to_dict(model_or_class: BaseModel | type[BaseModel]) -> Dict[str, Any]:
    """
    Traduit un modèle Pydantic (classe ou instance) en un dictionnaire complet
    et structuré décrivant tous ses champs via `model_fields`.
    """
    is_instance = isinstance(model_or_class, BaseModel)
    model_cls = type(model_or_class) if is_instance else model_or_class

    if not (isinstance(model_cls, type) and issubclass(model_cls, BaseModel)):
        raise TypeError(f"Attendu un modèle ou une classe Pydantic, reçu : {type(model_or_class)}")

    schema_dict: Dict[str, Any] = {}

    for field_name, field_info in model_cls.model_fields.items():
        # Détection du type et des choix possibles (dropdowns)
        type_name, choices = _extract_type_and_choices(field_info.annotation)

        # Détection de la valeur par défaut
        default_val = None
        if field_info.default is not PydanticUndefined:
            default_val = field_info.default

        # Détection du flag UploadRef (upload de fichier requis)
        extra = field_info.json_schema_extra or {}
        is_upload = bool(isinstance(extra, dict) and extra.get(_UPLOAD_MARKER) is True)

        field_data: Dict[str, Any] = {
            "name": field_name,
            "type": type_name,
            "required": field_info.is_required(),
            "default": default_val,
            "description": field_info.description or "",
            "is_upload": is_upload,
            "choices": choices,
            "constraints": _extract_constraints(field_info),
        }

        # Si c'est une instance concrète, on ajoute la valeur actuelle
        if is_instance:
            field_data["value"] = getattr(model_or_class, field_name)

        schema_dict[field_name] = field_data

    return schema_dict

if __name__ == "__main__":

    print("=" * 70)
    print("🧪 TEST MODEL_TO_DICT AVEC UN MODÈLE COMPLEXE ET COMPLET")
    print("=" * 70)

    # 1. Un vrai Enum Python
    class ColorProfile(str, Enum):
        BT709 = "bt709"
        BT2020 = "bt2020"
        DCI_P3 = "dci_p3"

    # 2. Un modèle Pydantic très riche et complexe
    class AdvancedStudioMasterInput(BaseModel):
        # Fichier d'entrée unique (UploadRef)
        master_video: str = UploadRef(description="Fichier vidéo ProRes master 4K")
        
        # Liste de fichiers d'entrée multiples (UploadRef sur liste)
        audio_stems: List[str] = UploadRef(description="Pistes audio multi-canaux (Drums, Bass, Vocals)")
        
        # Enum Python (dropdown UI)
        color_space: ColorProfile = Field(default=ColorProfile.BT709, description="Espace colorimétrique")
        
        # Literal avec choix multiples (dropdown UI)
        export_preset: Literal["web_preview", "broadcast_tv", "cinema_dcp"] = "broadcast_tv"
        
        # Entier avec bornes min/max
        crf_quality: int = Field(default=18, ge=0, le=51, description="Facteur de compression CRF")
        
        # Flottant avec contraintes strictes
        audio_loudness_target: float = Field(default=-16.0, gt=-30.0, le=-10.0, description="Volume cible LUFS")
        
        # Champ optionnel (Union[int, None])
        max_gop_size: Optional[int] = Field(default=None, ge=1, le=600, description="Intervalle max entre keyframes")
        
        # Booléen (Switch / Checkbox UI)
        enable_hdr_metadata: bool = Field(default=True, description="Conserver les métadonnées HDR10")
        
        # Chaîne avec contraintes de longueur
        burn_in_label: str = Field(default="INTERNAL_REVIEW", min_length=3, max_length=25, description="Tag textuel")

    # ─── TEST A : Introspection de la CLASSE seule (Pour générer le formulaire frontend) ───
    print("\n📋 [TEST A] Introspection de la CLASSE (Schéma complet pour l'UI React/Tauri) :")
    schema_classe = model_to_dict(AdvancedStudioMasterInput)
    print(json.dumps(schema_classe, indent=2, ensure_ascii=False))

    # ─── TEST B : Introspection d'une INSTANCE concrète (Avec les valeurs actuelles) ───
    print("\n📋 [TEST B] Introspection d'une INSTANCE (Schéma + Valeurs réelles de l'utilisateur) :")
    instance_concrete = AdvancedStudioMasterInput(
        master_video="source_4k.mov",
        audio_stems=["stem_drums.wav", "stem_vocals.wav"],
        color_space=ColorProfile.BT2020,
        export_preset="cinema_dcp",
        crf_quality=12,
        audio_loudness_target=-14.5,
        max_gop_size=120,
        enable_hdr_metadata=False,
        burn_in_label="DIRECTORS_CUT"
    )
    schema_instance = model_to_dict(instance_concrete)
    print(json.dumps(schema_instance, indent=2, ensure_ascii=False))

    # ─── VÉRIFICATIONS RAPIDES ───
    assert schema_classe["master_video"]["is_upload"] is True
    assert schema_classe["audio_stems"]["type"] == "list[string]"
    assert schema_classe["color_space"]["choices"] == ["bt709", "bt2020", "dci_p3"]
    assert schema_classe["crf_quality"]["constraints"] == {"ge": 0, "le": 51}
    assert schema_instance["export_preset"]["value"] == "cinema_dcp"
    print("\n✅ TOUTES LES ASSERTIONS DU PARSER SONT VALIDÉES AVEC SUCCÈS !")