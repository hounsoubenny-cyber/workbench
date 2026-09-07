#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 13:04:09 2026

@author: hounsousamuel
"""

from typing import Any, List
from pydantic import BaseModel
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, PatternArg, MultiPathArg, MultiPathMode,
    BoolArg, IntArg, FloatArg, Arg, ArgType as ArgTypeEnum,
    EnumArg,
)
from workbench.specs.specs import ActionSpec
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
    
class RawArg(BaseModel):
    flag: str
    value: Any = None
    values: List[Any] = None
    min_value: int | None = None
    max_value: int | None = None
    must_exist: bool | None = None
    type: ArgTypeEnum
    mode: MultiPathMode = MultiPathMode.REPEAT_FLAG
    separator: str | None = None
    is_upload_file: bool = False
    enum_values: list[str] | None = None
    
    
class RawEntry(BaseModel):
    tool: str
    args: List[RawArg]
    timeout: float | None = None
    capture_stdout: bool = False
    output_filename: str 
    check_version: bool = True
    min_version: tuple | None = None

class EmptyBaseModel(BaseModel):
    pass

class CustomActionSpec(ActionSpec):
    id: str = "custom_spec"
    input_cls: BaseModel = EmptyBaseModel
    label: str = "custom spec"
    collected_upload_files: list[str] | None = None
    validate_arg: bool = False
    timeout: float | None = None
    
def raw_to_custom_spec(raw_entry: RawEntry, binary_config: BinVersionCheckerConfig) -> CustomActionSpec:
    binary_config = BinVersionCheckerConfig.model_validate(binary_config)
    raw_entry = RawEntry.model_validate(raw_entry)
    args = raw_entry.args
    resolved_args = []
    collected_upload_files = []
    if args:
        for arg in args:
            flag = arg.flag
            value = arg.value
            values = arg.values
            resoled_arg: Arg
            
            if arg.is_upload_file:
                if value and isinstance(value, str):
                    collected_upload_files.append(value)
                elif values:
                    collected_upload_files.extend([v for v in values if v and isinstance(v, str)])
                
            if arg.type == ArgTypeEnum.BOOL:
                resoled_arg = BoolArg(
                    flag=flag, value=value
                )
            elif arg.type == ArgTypeEnum.INT:
                resoled_arg = IntArg(
                    flag=flag, value=value,
                    min_value=arg.min_value,
                    max_value=arg.max_value
                )
            elif arg.type == ArgTypeEnum.FLOAT:
                resoled_arg = FloatArg(
                    flag=flag, value=value,
                    min_value=arg.min_value,
                    max_value=arg.max_value
                )
            elif arg.type == ArgTypeEnum.PATH:
                resoled_arg = PathArg(
                    value=value, flag=flag, 
                    must_exist=arg.must_exist
                )
            elif arg.type == ArgTypeEnum.PATTERN_ARG:
                resoled_arg = PatternArg(
                    flag=arg.flag,
                    value=arg.value
                )
            elif arg.type == ArgTypeEnum.MULTI_PATH:
                resoled_arg = MultiPathArg(
                    flag=flag, values=values,
                    mode=arg.mode,
                    must_exist=arg.must_exist
                )
            elif arg.type == ArgTypeEnum.ENUM:
                resoled_arg = EnumArg(
                    flag=flag, value=value,
                    enum_values=arg.enum_values,
                )
                
            resolved_args.append(
                resoled_arg
            )
            
    def build_args(*args, **kwargs):
        return resolved_args
    
    spec = CustomActionSpec(
        binary_config=binary_config,
        build_args=build_args,
        collected_upload_files=collected_upload_files or None,
        min_version=tuple(raw_entry.min_version) if raw_entry.min_version else None,
        output_filename_template=raw_entry.output_filename,
        capture_stdout=raw_entry.capture_stdout,
        check_version=raw_entry.check_version,
        tool=raw_entry.tool,
        timeout=raw_entry.timeout,
    )
    return spec

if __name__ == "__main__":
    from pprint import pprint

    print("="*60)
    print("🧪 TEST 1 : Spécification FFmpeg standard")
    print("="*60)
    
    # Configuration du vérificateur de version pour ffmpeg
    ffmpeg_bin_config = BinVersionCheckerConfig(
        cmd="-version", 
        marker="ffmpeg", 
        tool_name="ffmpeg"
    )

    # Dictionnaire brut (comme s'il venait d'une API HTTP ou d'un JSON en BDD)
    raw_ffmpeg = {
      "tool": "ffmpeg",
      "args": [
        {"type": "bool", "flag": "-y", "value": True},
        {"type": "path", "flag": "-i", "value": "clip.mp4", "must_exist": True, "is_upload_file": True},
        {"type": "pattern", "flag": "-vf", "value": "scale=128:-1"}
      ],
      "output_filename": "out.mp4",
      "timeout": 30,
      "check_version": False
    }

    # 1. Conversion en CustomActionSpec
    spec_ffmpeg = raw_to_custom_spec(raw_ffmpeg, ffmpeg_bin_config)
    
    print("✅ ActionSpec généré :", spec_ffmpeg.id)
    print("📦 Fichiers à uploader détectés :", spec_ffmpeg.collected_upload_files)
    
    # 2. Test du build_args
    args_ffmpeg = spec_ffmpeg.build_args()
    print("🛠️  Arguments construits :")
    for a in args_ffmpeg:
        print(f"   - {a}")


    print("\n" + "="*60)
    print("🧪 TEST 2 : Spécification avec MultiPathArg (ex: concaténation)")
    print("="*60)

    # Configuration pour cat (ou un autre outil acceptant plusieurs fichiers)
    cat_bin_config = BinVersionCheckerConfig(
        cmd="--version", 
        marker="coreutils", 
        tool_name="cat"
    )

    raw_cat = {
      "tool": "cat",
      "args": [
        {
            "type": "multi_path", 
            "flag": "", 
            "values": ["part1.txt", "part2.txt", "part3.txt"], 
            "mode": "positional", # Sans flag, juste l'un après l'autre
            "must_exist": True, 
            "is_upload_file": True
        }
      ],
      "output_filename": "merged.txt",
      "check_version": False
    }

    # 1. Conversion
    spec_cat = raw_to_custom_spec(raw_cat, cat_bin_config)
    
    print("✅ ActionSpec généré :", spec_cat.id)
    print("📦 Fichiers à uploader détectés :", spec_cat.collected_upload_files)
    
    # 2. Test du build_args
    args_cat = spec_cat.build_args()
    print("🛠️  Arguments construits :")
    for a in args_cat:
        print(f"   - {a}")