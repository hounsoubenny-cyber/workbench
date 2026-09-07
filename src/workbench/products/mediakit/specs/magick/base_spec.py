#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 18:14:25 2026

@author: hounsousamuel
"""

from pathlib import Path
from typing import ClassVar

from workbench.specs.specs import ActionSpec, InputT
from workbench.core.subprocess.engine import resolve_sandboxed_path
from workbench.core.subprocess.wb_subprocess_types import Arg, EnumArg
from workbench.products.mediakit.specs.magick.base_model import BaseMagickActionInput
from workbench.products.mediakit.mk_utils.utils import is_image_file
from workbench.core.subprocess.version_checker import (
    Config as BinVersionCheckerConfig,
)

MAGICK_CONFIG = BinVersionCheckerConfig(
    **{"cmd": "--version", "marker": "ImageMagick", "tool_name": "ImageMagick"}
)
class IsNotImageFile(Exception):
    pass


class MagickSpec(ActionSpec[InputT]):
    tool: str = "magick"
    binary_config: BinVersionCheckerConfig = MAGICK_CONFIG
    
    # Limites de ressources imposées à TOUTE commande magick — protège
    # contre les "bombes de décompression" (une petite image compressée qui,
    # une fois décompressée, consomme des dizaines de Go de RAM), et contre
    # un traitement qui tournerait indéfiniment sur un fichier piégé.
    # C'est l'équivalent, pour magick, de -protocol_whitelist pour ffmpeg.
    SECURITY_ARGS: ClassVar[list] = [
        EnumArg(flag="-limit", value="memory", enum_values=["memory"]),
        EnumArg(flag="", value="512MiB", enum_values=["512MiB"]),
        EnumArg(flag="-limit", value="time", enum_values=["time"]),
        EnumArg(flag="", value="60", enum_values=["60"]),
    ]

    def full_args(self, user_input: InputT) -> list[Arg]:
        """
        ⚠️ Toujours utiliser full_args() pour construire la commande finale,
        jamais build_args() directement — sinon les limites de ressources ne
        sont pas incluses.
        """
        return [*self.SECURITY_ARGS, *self.build_args(user_input)]

    def validate_args(self, user_input: BaseMagickActionInput, workdir: Path) -> None:
        if not isinstance(user_input, BaseMagickActionInput):
            raise ValueError("Input should be a valid BaseMagickActionInput !")

        if self.validate_arg:
            resolved = resolve_sandboxed_path(user_input.input_file, workdir)
            if not is_image_file(str(resolved)):
                raise IsNotImageFile(
                    f"{user_input.input_file} ne semble pas être un fichier image"
                )