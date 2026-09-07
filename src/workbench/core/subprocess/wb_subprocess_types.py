#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 21:55:31 2026

@author: hounsousamuel
"""


"""
Workbench Mediakit — Types d'arguments pour l'Engine CLI.

Ce module définit les types d'arguments autorisés pour construire les
commandes CLI (ffmpeg, ImageMagick, SoX) de manière sûre.

Volontairement, il n'existe AUCUN type "string" libre : chaque argument doit
être Path, Int, Float, Bool ou Enum. Ce choix élimine par construction toute
surface d'injection liée à du texte non contraint — un argument invalide est
rejeté par Pydantic avant même d'atteindre l'engine d'exécution.

⚠️ Ce module ne connaît PAS le workdir courant. Pour ArgType.PATH :
  - on valide seulement que la valeur n'est pas vide (aucun accès disque ici)
  - la résolution/sandboxing dans le workdir, et la vérification optionnelle
    d'existence (`must_exist`), sont faites par l'engine (engine.py), qui lui
    seul connaît le workdir du job en cours.
"""

import re
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class ArgType(str, Enum):
    """Types de valeurs autorisés pour un argument de commande CLI."""

    PATH = "path"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    ENUM = "enum"
    PATTERN_ARG = "pattern"
    MULTI_PATH = "multi_path"

class BaseArg(BaseModel):
    """Champs communs à tous les types d'arguments."""

    flag: str = Field(
        default="",
        description="Flag CLI associé, ex: '-b:v'. Laisser vide pour un argument positionnel.",
    )


class PathArg(BaseArg):
    """
    Un argument représentant un chemin de fichier, relatif au workdir du job.

    - `must_exist=True` pour un fichier d'ENTRÉE (l'engine vérifiera sa
      présence après résolution dans le workdir).
    - `must_exist=False` (défaut) pour un fichier de SORTIE, qui n'existe
      pas encore au moment où la commande est construite.
    """

    type: Literal[ArgType.PATH] = ArgType.PATH
    value: str
    must_exist: bool = False

    @field_validator("value")
    @classmethod
    def value_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("chemin vide")
        return v


class IntArg(BaseArg):
    """Un argument entier, avec bornes min/max optionnelles."""

    type: Literal[ArgType.INT] = ArgType.INT
    value: int
    min_value: int | None = None
    max_value: int | None = None

    @model_validator(mode="after")
    def check_range(self) -> "IntArg":
        _check_bounds(self.value, self.min_value, self.max_value, self.flag)
        return self


class FloatArg(BaseArg):
    """Un argument flottant, avec bornes min/max optionnelles."""

    type: Literal[ArgType.FLOAT] = ArgType.FLOAT
    value: float
    min_value: float | None = None
    max_value: float | None = None

    @model_validator(mode="after")
    def check_range(self) -> "FloatArg":
        _check_bounds(self.value, self.min_value, self.max_value, self.flag)
        return self


class BoolArg(BaseArg):
    """
    Un argument booléen — traduit en flag présent/absent dans la commande
    finale (voir engine.py), pas en '-flag true'/'-flag false'.
    """

    type: Literal[ArgType.BOOL] = ArgType.BOOL
    value: bool


class EnumArg(BaseArg):
    """
    Un argument dont la valeur doit appartenir à une liste fermée de choix.

    C'est le remplaçant du type "string" libre : toute valeur textuelle doit
    passer par un EnumArg avec ses valeurs autorisées explicitement listées.
    """

    type: Literal[ArgType.ENUM] = ArgType.ENUM
    value: str
    enum_values: list[str]

    @model_validator(mode="after")
    def check_value_in_enum(self) -> "EnumArg":
        if self.value not in self.enum_values:
            raise ValueError(f"{self.value!r} n'est pas parmi {self.enum_values}")
        return self


class PatternArg(BaseArg):
    """
    Un argument en string / regex pour les outils qui l'uilisent comme grep, jq.
    Une méthode de validation sera mis en place.
    """
    
    type: Literal[ArgType.PATTERN_ARG] = ArgType.PATTERN_ARG
    value: str
    
    # # Surchargeable par action si un cas précis a besoin de plus de caractères
    allowed_regex: str | None = None #r"^[A-Za-z0-9_\-.:=,/@ ]*$"
    max_length: int = 512

    @model_validator(mode="after")
    def validate_pattern(self) -> "PatternArg":
        if len(self.value) > self.max_length:
            raise ValueError(f"valeur trop longue ({len(self.value)} > {self.max_length})")
        if "\x00" in self.value or "\n" in self.value:
            raise ValueError("caractères de contrôle interdits")
        if self.allowed_regex:
            try:
                if not re.fullmatch(self.allowed_regex, self.value):
                    raise ValueError(f"{self.value!r} contient des caractères non autorisés")
            except re.error:
                pass
        if not self.flag and self.value.startswith("-"):
            raise ValueError("un motif positionnel ne peut pas commencer par '-' (injection d'argument)")
        return self
    
def _check_bounds(
    value: float, min_value: float | None, max_value: float | None, flag: str
) -> None:
    if min_value is not None and value < min_value:
        raise ValueError(f"Arg '{flag}': {value} < min autorisé {min_value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"Arg '{flag}': {value} > max autorisé {max_value}")

class MultiPathMode(str, Enum):
    """
    Comment plusieurs fichiers doivent apparaître dans la commande finale —
    ça dépend ENTIÈREMENT de l'outil, il n'y a pas de représentation
    universelle (`-i f1 -i f2` n'est PAS équivalent à `-i f1 f2` pour un
    parseur CLI classique) :
 
    - REPEAT_FLAG  : le flag est répété une fois par fichier.
                      ex ffmpeg : -i f1.mp4 -i f2.mp4 -i f3.mp4
    - POSITIONAL   : pas de flag (ou un seul flag suivi de TOUS les
                      fichiers), aucune répétition.
                      ex cat/tar : f1 f2 f3   (ou "tar -cf out.tar f1 f2 f3")
    - JOINED       : une seule valeur, fichiers joints par un séparateur.
                      ex (certains outils) : --files f1,f2,f3
    """
    REPEAT_FLAG = "repeat_flag"
    POSITIONAL = "positional"
    JOINED = "joined"
 
 
class MultiPathArg(BaseArg):
    """
    Plusieurs chemins de fichiers (typiquement plusieurs fichiers d'entrée),
    relatifs au workdir du job — voir MultiPathMode pour la sémantique de
    répétition, qui dépend de l'outil cible.
    """
 
    type: Literal[ArgType.MULTI_PATH] = ArgType.MULTI_PATH
    values: list[str]
    must_exist: bool = False
    mode: MultiPathMode = MultiPathMode.REPEAT_FLAG
    separator: str = ","  # utilisé seulement en mode JOINED
 
    @field_validator("values")
    @classmethod
    def values_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("au moins un fichier requis")
        for item in v:
            if not item.strip():
                raise ValueError("chemin vide dans la liste")
        return v


# Union discriminée : Pydantic choisit automatiquement le bon modèle
# (PathArg / IntArg / FloatArg / BoolArg / EnumArg) selon le champ "type".
TYPES = [PathArg, MultiPathArg, IntArg, FloatArg, BoolArg, EnumArg, PatternArg]
Arg = Annotated[
    Union[*TYPES],
    Field(discriminator="type"),
]
