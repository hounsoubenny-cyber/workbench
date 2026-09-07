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
from workbench.core.subprocess.wb_subprocess_types import Arg, EnumArg, BoolArg, ArgType, PatternArg
from workbench.products.mediakit.specs.ffmpeg.base_model import BaseFfmpegActionInput
from workbench.products.mediakit.mk_utils.utils import is_video_file
from workbench.core.subprocess.version_checker import (
    Config as BinVersionCheckerConfig,
)

FFMPEG_CONFIG = BinVersionCheckerConfig(**{'cmd': '-version', 'marker': 'ffmpeg version', 'tool_name': 'ffmpeg'})
SAFE_WEB_VIDEO_FILTER = "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p"

class IsNotVideoFile(Exception):
    pass

    
class FfmpegSpec(ActionSpec[InputT]):
    tool: str = "ffmpeg"
    SECURITY_ARGS: ClassVar[list] = [
        EnumArg(flag="-protocol_whitelist", value="file", enum_values=["file"]),
        BoolArg(flag="-y", value=True), # Auto accet, evite de loquer stdin
    ]
    binary_config: BinVersionCheckerConfig = FFMPEG_CONFIG
    auto_even_dimensions: bool = False
    
    def full_args(self, user_input: InputT) -> list[Arg]:
        """
        ⚠️ Toujours utiliser full_args() pour construire la commande finale,
        jamais build_args() directement — sinon les args de sécurité
        (protocol_whitelist) ne sont pas inclus.
        """
        raw_args = self.build_args(user_input)

        if not self.auto_even_dimensions:
            return [*self.SECURITY_ARGS, *raw_args]

        modified_args = []
        has_vf = False
        has_filter_complex = False

        for arg in raw_args:
            flag = getattr(arg, "flag", "")
            if flag == "-vf" and hasattr(arg, "value"):
                has_vf = True
                val = str(arg.value)
                if "trunc(iw/2)*2" not in val:
                    val = f"{val},{SAFE_WEB_VIDEO_FILTER}"
                modified_args.append(arg.model_copy(update={"value": val}))
            else:
                if flag == "-filter_complex":
                    has_filter_complex = True
                modified_args.append(arg)

        # Si aucun -vf n'existait ET qu'il n'y a pas de -filter_complex, on injecte -vf en sécurité
        # (FFmpeg interdit de combiner -vf et -filter_complex sur un même flux de sortie)
        if not has_vf and not has_filter_complex:
            output_idx = len(modified_args)
            for i in range(len(modified_args) - 1, -1, -1):
                a = modified_args[i]
                if a.type == ArgType.PATH and not getattr(a, "must_exist", False) and not a.flag:
                    output_idx = i
                    break
            safe_vf_arg = PatternArg(flag="-vf", value=SAFE_WEB_VIDEO_FILTER)
            modified_args.insert(output_idx, safe_vf_arg)

        return [*self.SECURITY_ARGS, *modified_args]

    def validate_args(self, user_input: BaseFfmpegActionInput, workdir: Path) -> None:
        if not isinstance(user_input, BaseFfmpegActionInput):
            raise ValueError("Input should be a valid BaseFfmpegActionInput !")

        if self.validate_arg:
            resolved = resolve_sandboxed_path(user_input.input_file, workdir)
            if not is_video_file(str(resolved)):
                raise IsNotVideoFile(
                    f"{user_input.input_file} ne semble pas être un fichier vidéo"
                )