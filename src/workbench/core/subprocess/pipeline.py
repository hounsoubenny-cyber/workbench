#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Aug 31 22:18:08 2026

@author: hounsousamuel

Workbench — Pipeline : enchaîne plusieurs CommandEngine (ffmpeg,
magick, sox...) sans jamais utiliser de vrai pipe Unix. Chaque étape écrit
son résultat dans un fichier du workdir, que l'étape suivante peut ensuite
référencer.
"""

import asyncio
from dataclasses import dataclass
from typing import Callable, Awaitable, Union
from pathlib import Path
from workbench.core.subprocess.engine import (
    CommandEngine, ExecResult, resolve_sandboxed_path,
)
from workbench.core.subprocess.wb_subprocess_types import Arg
from workbench.wb_utils.loop_utils import _run_async
LogCallback = Union[Callable[[dict], None], Callable[[dict], Awaitable[None]]]

# Reçoit le dict des sorties déjà produites (outputs) et renvoie la liste
# d'arguments typés pour CETTE étape.
ArgsBuilder = Callable[[dict], list[Arg]]


class PipelineError(Exception):
    """Levée quand une étape du pipeline échoue — porte l'id de l'étape fautive."""

    def __init__(self, step_id: str, original: Exception):
        self.step_id = step_id
        self.original = original
        super().__init__(f"Étape '{step_id}' a échoué : {original}")


@dataclass
class PipelineStep:
    id: str
    engine: CommandEngine
    build_args: ArgsBuilder
    # `output_filename` peut être une valeur fixe OU une fonction du dict
    # `outputs` — utile quand le nom dépend de l'input de l'étape (ex: le
    # format choisi), pour rester garanti cohérent avec ce que build_args a
    # réellement produit (même source de vérité, jamais deux noms différents
    # qui peuvent diverger silencieusement).
    output_filename: Union[str, Callable[[dict], str]]
    timeout: float = 300
    capture_stdout: bool = False


class Pipeline:
    def __init__(self, steps: list[PipelineStep]):
        self.steps = steps

    async def run(
        self,
        initial_inputs: dict | None = None,
        on_output: LogCallback | None = None,
    ) -> dict:
        """
        initial_inputs : fichiers de départ fournis par l'utilisateur,
        ex: {"input": "video_source.mp4"} — traités comme une donnée présente
        dans le workdir, pas comme une sortie d'étape.

        Retourne le dict `outputs` complet : {step_id: chemin, ..., "_previous": chemin}
        """
        outputs: dict = dict(initial_inputs or {})

        for step in self.steps:
            args = step.build_args(outputs)

            async def _forward(payload: dict, _step_id: str = step.id) -> None:
                if on_output is None:
                    return
                enriched = {"step": _step_id, **payload}
                maybe_coro = on_output(enriched)
                if asyncio.iscoroutine(maybe_coro):
                    await maybe_coro

            try:
                result: ExecResult = await step.engine.execute_async(
                    args, timeout=step.timeout, on_output=_forward
                )
            except Exception as exc:
                raise PipelineError(step.id, exc) from exc

            if not result.ok:
                raise PipelineError(
                    step.id,
                    RuntimeError(
                        f"code retour {result.returncode} — {result.stderr[-500:]}"
                    ),
                )

            resolved_filename = (
                step.output_filename(outputs) if callable(step.output_filename) else step.output_filename
            )
            output_path = resolve_sandboxed_path(resolved_filename, step.engine.workdir)

            if step.capture_stdout:
                # L'outil n'a rien écrit lui-même : on matérialise nous-mêmes
                # sa sortie stdout dans le fichier attendu par l'étape suivante.
                Path(output_path).write_text(result.stdout)

            # On stocke le nom RELATIF (pas le chemin absolu résolu) : les
            # PathArg suivants recoivent une valeur relative au
            # workdir
            outputs[step.id] = resolved_filename
            outputs["_previous"] = resolved_filename

        return outputs
    
    def run_sync(
        self,
        initial_inputs: dict | None = None,
        on_output: LogCallback | None = None,
    ):
        return _run_async(self.run, initial_inputs, on_output)
    
if __name__ == "__main__":
    from workbench.core.subprocess.wb_subprocess_types import EnumArg, PathArg
    workdir = "/tmp"
    ls_config = {'cmd': '--version', 'marker': 'coreutils', 'tool_name': 'ls'}
    grep_config = {'cmd': '--version', 'marker': 'grep', 'tool_name': 'grep'}
    ls_engine = CommandEngine('ls', ls_config, workdir)
    grep_engine = CommandEngine('grep', grep_config, workdir)
    
    pipeline = Pipeline([
        PipelineStep(
            id='list_files',
            engine=ls_engine, 
            build_args=lambda o: [], 
            output_filename='ls_output.txt', 
            capture_stdout=True
        ),
        PipelineStep(id='filter_video', engine=grep_engine,
            build_args=lambda o: [EnumArg(value='video', enum_values=['video','audio']), PathArg(value=o['_previous'], must_exist=True)],
            output_filename='grep_output.txt', capture_stdout=True),
    ])
    
    r = pipeline.run_sync(on_output=None)
    
    
