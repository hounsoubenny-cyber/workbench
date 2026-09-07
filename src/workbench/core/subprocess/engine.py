#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 22:18:07 2026

@author: hounsousamuel
"""

import os
import asyncio
import shutil
from pathlib import Path
from typing import Callable, Awaitable, Union

from workbench.core.subprocess.wb_subprocess_types import Arg, ArgType, MultiPathMode
from workbench.core.subprocess.version_checker import (
    BinaryNotFoundError, VersionParseError,
    get_binary_version, version_at_least,
    Config as BinVersionCheckerConfig,
)
from workbench.wb_utils.loop_utils import _run_async
from workbench.wb_utils.stop_process import kill_process_async


TRUSTED_DIRS = [
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
] # None

class PathTraversalError(Exception):
    pass


class MissingPathError(Exception):
    pass


# Le callback reçoit toujours un dict {"stream": "stdout"|"stderr", "text": str}.
# Il peut être une fonction normale OU une coroutine — les deux sont supportées.
LogCallback = Union[Callable[[dict], None], Callable[[dict], Awaitable[None]]]


def resolve_sandboxed_path(value: str, workdir: Path) -> Path:
    if not workdir:
        raise ValueError("workdir is needed !")
    
    # Défense en profondeur, en plus de -protocol_whitelist (ffmpeg) : un nom
    # contenant ":" peut être interprété comme un préfixe de protocole/coder
    # par ffmpeg (http:, concat:) OU ImageMagick (msl:, label:@, https:) —
    # jamais légitime pour un nom de fichier média normal.
    if ":" in value:
        raise PathTraversalError(f"Caractère ':' interdit dans un chemin: {value}")

    workdir = Path(workdir).resolve()
    
    candidate = Path(value)
    if candidate.is_absolute() and not candidate.is_relative_to(workdir):
        raise PathTraversalError(f"Chemin absolu interdit: {value}")

    resolved = (workdir / candidate).resolve()

    if not resolved.is_relative_to(workdir):
        raise PathTraversalError(f"Chemin hors du workdir: {value} → {resolved}")

    return resolved


class ExecResult:
    def __init__(self, returncode: int, stdout: str, stderr: str, output_filename: str = ""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.output_filename = output_filename

    @property
    def ok(self) -> bool:
        return self.returncode in (0, 1)
    
    @property
    def success(self) -> bool:
        return self.returncode == 0
    
    def to_dict(self):
        return {
            "returncode": self.returncode,
            "stderr": self.stderr,
            "stdout": self.stdout,
            "ok": self.ok,
            "success": self.success,
            "output_filename": self.output_filename
        }
    def __repr__(self) -> str:
        return f"ExecResult(returncode={self.returncode}, ok={self.ok})"


class CommandEngine:
    def __init__(
        self,
        binary: str,
        binary_config: BinVersionCheckerConfig,
        workdir: Path,
        min_version: tuple[int, ...] | None = None,
        check_version: bool = True,
    ):
        self.workdir = Path(workdir).resolve()
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.binary_config = binary_config
        self.version: tuple[int, ...] | None = None
        self.binary_path = self._resolve_and_check(
            binary.strip(), 
            binary_config,
            min_version, 
            check_version=check_version
        )

    def _resolve_and_check(
        self,
        binary: str,
        binary_config: BinVersionCheckerConfig,
        min_version: tuple[int, ...] | None,
        trusted_dirs: list | None = None,
        check_version: bool = True,
    ) -> str:
        trusted_dirs = trusted_dirs or TRUSTED_DIRS
        if trusted_dirs:
            trusted_dirs = os.pathsep.join(trusted_dirs)
        path = shutil.which(binary.strip(), path=trusted_dirs)
        if not path:
            raise BinaryNotFoundError(f"Binaire introuvable dans le PATH: {binary}")

        # version = _run_async(get_binary_version_async, path, binary_config, check_version)
        version = get_binary_version(path, binary_config, check_version=check_version)
        self.version = version
        
        if min_version is not None and check_version and not version_at_least(version, min_version):
            raise VersionParseError(
                f"{binary}: version {version} trop ancienne (minimum requis {min_version})"
            )

        return path

    def _validate(self, arg: Arg) -> Arg:
        """Valide/normalise un argument. Pour un PathArg : résolution + sandbox."""
        if arg.type == ArgType.PATH:
            resolved = resolve_sandboxed_path(arg.value, self.workdir)
            if arg.must_exist and not resolved.exists():
                raise MissingPathError(f"Fichier attendu introuvable: {resolved}")
            return arg.model_copy(update={"value": str(resolved)})
        if arg.type == ArgType.MULTI_PATH:
            resolved_values = []
            for v in arg.values:
                resolved = resolve_sandboxed_path(v, self.workdir)
                if arg.must_exist and not resolved.exists():
                    raise MissingPathError(f"Fichier attendu introuvable: {resolved}")
                resolved_values.append(str(resolved))
            return arg.model_copy(update={"values": resolved_values})
        return arg
 
    def build_command(self, args: list[Arg]) -> list[str]:
        cmd = [self.binary_path]
        for arg in args:
            arg = self._validate(arg)
            if arg.type == ArgType.BOOL:
                if arg.value:
                    if arg.flag:
                        cmd.append(arg.flag)
            elif arg.type == ArgType.MULTI_PATH:
                if arg.mode == MultiPathMode.REPEAT_FLAG:
                    for v in arg.values:
                        if arg.flag:
                            cmd.append(arg.flag)
                        cmd.append(v)
                elif arg.mode == MultiPathMode.POSITIONAL:
                    if arg.flag:
                        cmd.append(arg.flag)
                    cmd.extend(arg.values)
                elif arg.mode == MultiPathMode.JOINED:
                    if arg.flag:
                        cmd.append(arg.flag)
                    cmd.append(arg.separator.join(arg.values))
            else:
                if arg.flag:
                    cmd.append(arg.flag)
                cmd.append(str(arg.value))
        return cmd


    async def execute_async(
        self,
        args: list[Arg],
        timeout: float | None = 300,
        on_output: LogCallback | None = None,
        output_filename: str | None = None,
        capture_stdout: bool = False,
    ) -> ExecResult:
        cmd = self.build_command(args)

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.workdir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout_chunks: list[str] = []
        stderr_chunks: list[str] = []

        async def _emit(stream_name: str, text: str) -> None:
            if on_output is None:
                return
            payload = {"stream": stream_name, "text": text}
            maybe_coro = on_output(payload)
            if asyncio.iscoroutine(maybe_coro):
                await maybe_coro

        async def _pump(stream: asyncio.StreamReader, stream_name: str, sink: list[str]) -> None:
            # Lire ligne par ligne pendant que le process tourne, pour
            # streamer les logs en direct au lieu d'attendre la fin.
            while True:
                raw_line = await stream.readline()
                if not raw_line:
                    break
                line = raw_line.decode(errors="replace")
                sink.append(line)
                await _emit(stream_name, line)

        try:
            await asyncio.wait_for(
                asyncio.gather(
                    _pump(process.stdout, "stdout", stdout_chunks),
                    _pump(process.stderr, "stderr", stderr_chunks),
                ),
                timeout=timeout,
            )
            returncode = await asyncio.wait_for(process.wait(), 120)
        except asyncio.TimeoutError as e:
            await kill_process_async(process)
            raise TimeoutError(str(e))
        
        except asyncio.CancelledError as e:
            await kill_process_async(process)
            raise e
        
        stdout = "".join(stdout_chunks)
        if output_filename and capture_stdout:
            output_path = resolve_sandboxed_path(output_filename, workdir=self.workdir)
            Path(output_path).write_text(stdout)
            
        return ExecResult(
            returncode=returncode,
            stdout=stdout,
            stderr="".join(stderr_chunks),
            output_filename=output_filename
        )

    def execute_sync(
        self,
        args: list[Arg],
        timeout: float = 300,
        on_output: LogCallback | None = None,
    ) -> ExecResult:
        """Raccourci pratique — même logique que execute_async, juste attendu de façon synchrone."""
        return _run_async(self.execute_async, args, timeout, on_output)
    
if __name__ == "__main__":
    from workbench.core.subprocess.wb_subprocess_types import BoolArg
    binary = "/usr/bin/pwd"
    cmd = "--version"
    config = {'cmd': cmd, 'marker': '', 'tool_name': binary}
    workdir = "/tmp"
    ls_engine = CommandEngine(
        binary=binary, 
        binary_config=config, 
        workdir=workdir
    )
    ls_engine.execute_sync(
        args=[BoolArg(flag="-P", value=True)],
        on_output=lambda x: print(f"{x!r}")
    )