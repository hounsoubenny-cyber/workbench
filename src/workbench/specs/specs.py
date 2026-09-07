#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 14:27:35 2026

@author: hounsousamuel
"""

from pathlib import Path
from typing import Callable, Generic, TypeVar

from pydantic import BaseModel, ConfigDict
from workbench.core.subprocess.wb_subprocess_types import Arg
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
InputT = TypeVar("InputT", bound=BaseModel)


class ActionSpec(BaseModel, Generic[InputT]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str                    # "convert_video"
    label: str                 # "Convertir une vidéo"
    tool: str                  # "ffmpeg"
    build_args: Callable[[InputT], list[Arg]]  # user_input typé -> list[Arg]
    output_filename_template: str | Callable[[InputT], str]  # ex: "{basename}_converted.{format}"
    binary_config: BinVersionCheckerConfig
    min_version: tuple | None = None
    check_version: bool = True
    input_cls: type(BaseModel)
    capture_stdout: bool = False
    validate_arg: bool = False  # Valider un argument comme check si réellement fichier vidéo
    
    def full_args(self, user_input: InputT) -> list:
        return self.build_args(user_input)
    
    def validate_args(self, user_input: InputT, workdir: Path) -> None:
        """
        Hook de validation "métier" (au-delà du typage Pydantic de base),
        ex: vérifier que le fichier fourni est vraiment une vidéo.

        `workdir` est requis ici : `user_input.input_file` n'est qu'un nom
        relatif, il faut le résoudre dans le bon dossier avant toute
        inspection de contenu (sinon on checke le mauvais fichier, ou un
        fichier qui n'existe pas depuis le cwd du process).
        """
        pass