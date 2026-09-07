#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 18:14:25 2026

@author: hounsousamuel
"""

"""Workbench Mediakit — SoxSpec, la base de toutes les actions SoX."""

from pathlib import Path

from workbench.specs.specs import ActionSpec, InputT
from workbench.core.subprocess.engine import resolve_sandboxed_path
from workbench.products.mediakit.specs.sox.base_model import BaseSoxActionInput
from workbench.products.mediakit.mk_utils.utils import is_audio_file
from workbench.core.subprocess.version_checker import (
    Config as BinVersionCheckerConfig,
)
SOX_CONFIG = BinVersionCheckerConfig(**{'cmd': '--version', 'marker': 'sox', 'tool_name': 'sox'})

class IsNotAudioFile(Exception):
    pass


class SoxSpec(ActionSpec[InputT]):
    tool: str = "sox"
    binary_config: BinVersionCheckerConfig = SOX_CONFIG
    # Contrairement à ffmpeg/magick, SoX ne va jamais chercher de ressource
    # distante ni interpréter de préfixe genre "protocole:" dans un nom de
    # fichier — pas d'équivalent de protocol_whitelist nécessaire ici. Le
    # garde-fou générique contre les ":" (déjà dans resolve_sandboxed_path)
    # suffit comme défense en profondeur commune aux 3 outils.

    def full_args(self, user_input: InputT) -> list:
        return self.build_args(user_input)

    def validate_args(self, user_input: BaseSoxActionInput, workdir: Path) -> None:
        if not isinstance(user_input, BaseSoxActionInput):
            raise ValueError("Input should be a valid BaseSoxActionInput !")

        if self.validate_arg:
            resolved = resolve_sandboxed_path(user_input.input_file, workdir)
            if not is_audio_file(str(resolved)):
                raise IsNotAudioFile(
                    f"{user_input.input_file} ne semble pas être un fichier audio"
                )