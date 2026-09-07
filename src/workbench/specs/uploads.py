#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 12:15:25 2026

@author: hounsousamuel
"""

"""
Marqueur générique pour signaler, sur un modèle Pydantic d'input (LsInput,
ConvertToGifInput, ConcatVideosInput...), qu'un champ str (ou list[str])
attend un NOM DE FICHIER correspondant à un fichier réellement uploadé en
multipart lors de POST /job/create — voir api/create_routes.py, fonction
`collect_upload_filenames`.

Le champ contient toujours le nom (relatif au workdir) que le client
souhaite donner au fichier une fois enregistré — c'est ce même nom qui sera
ensuite référencé normalement dans `build_args` (PathArg/MultiPathArg),
exactement comme n'importe quel autre champ str. Le marqueur ne change rien
à la validation Pydantic elle-même : il sert uniquement à ce que le serveur
sache, de façon générique (sans aucun code par-spec), quels champs doivent
être appariés à des fichiers uploadés, ET dans quel ordre (ordre de
déclaration du modèle, ordre de la liste pour un champ list[str]).

Usage :
    class ConvertToGifInput(BaseModel):
        input_file: str = UploadRef(description="Vidéo à convertir")
        width: int = 64

    class ConcatVideosInput(BaseModel):
        inputs: list[str] = UploadRef(description="Vidéos à concaténer, dans l'ordre")
"""

from typing import Any

from pydantic import Field, BaseModel
from pydantic.fields import FieldInfo


_MARKER_KEY = "workbench_upload"


def UploadRef(*, default: Any = ..., **kwargs) -> FieldInfo:
    """Field() Pydantic classique, avec le marqueur d'upload en plus."""
    extra = kwargs.pop("json_schema_extra", None) or {}
    extra = {**extra, _MARKER_KEY: True}
    return Field(default=default, json_schema_extra=extra, **kwargs)


def is_upload_field(field_info: FieldInfo) -> bool:
    extra = field_info.json_schema_extra
    return isinstance(extra, dict) and extra.get(_MARKER_KEY) is True


def collect_upload_filenames(model_instance) -> list[str]:
    """
    Parcourt les champs du modèle (dans leur ordre de déclaration —
    garanti par Pydantic v2) et retourne, à plat, la liste ordonnée des
    noms de fichiers attendus comme uploads : un nom pour un champ str
    marqué, N noms (dans l'ordre de la liste) pour un champ list[str]
    marqué.
    """
    names: list[str] = []
    for field_name, field_info in type(model_instance).model_fields.items():
        if not is_upload_field(field_info):
            continue
        value = getattr(model_instance, field_name)
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            names.extend(v for v in value if v)
        elif value:
            names.append(value)
    return names

if __name__ == "__main__":
    class GrepInput(BaseModel):
        pattern: str
        input_file: str = UploadRef(description='Fichier texte')
    
    field_info = GrepInput.model_fields['input_file']
    # 1. Ce que UploadRef() a REELLEMENT pose sur le champ (rien de plus qu'un Field() normal + un dict)
    print('Type de field_info:', type(field_info))
    print('field_info.json_schema_extra =', field_info.json_schema_extra)
    print()
    
    field_info_pattern = GrepInput.model_fields['pattern']
    print('Pour le champ NON marque (pattern):')
    print('field_info.json_schema_extra =', field_info_pattern.json_schema_extra)
    print()
    
    # 2. is_upload_field() : juste un test sur ce dict
    print('is_upload_field(input_file) ->', is_upload_field(field_info))
    print('is_upload_field(pattern)    ->', is_upload_field(field_info_pattern))
    print()
    
    # 3. Tous les champs du modele, dans l'ordre
    print('model_fields.items() (ordre de declaration) ->', list(GrepInput.model_fields.keys()))
    print()
    
    # 4. collect_upload_filenames sur une INSTANCE reelle
    instance = GrepInput(pattern='foo', input_file='notes.txt')
    print('collect_upload_filenames(instance) ->', collect_upload_filenames(instance))
