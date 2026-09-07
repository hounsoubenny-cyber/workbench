#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 08:20:34 2026

@author: hounsousamuel
"""

"""
Workbench — PipelineSpec : décrit un enchaînement prédéfini de plusieurs
ActionSpec (potentiellement d'outils différents), et sait le transformer en
un vrai `Pipeline` exécutable (core/subprocess/pipeline.py).
"""

from typing import Callable, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from workbench.specs.specs import ActionSpec
from workbench.core.subprocess.pipeline import Pipeline, PipelineStep
from workbench.core.subprocess.engine import CommandEngine

InputT = TypeVar("InputT", bound=BaseModel)


class PipelineStepSpec(BaseModel, Generic[InputT]):
    """
    Une étape du pipeline = un ActionSpec existant + comment construire SON
    input typé à partir de l'input global du pipeline et des sorties déjà
    produites par les étapes précédentes (le dict `outputs` du Pipeline).

    Pas de champ `output_filename` ici volontairement : le nom réel du
    fichier produit est TOUJOURS dérivé de `action.output_filename_template`
    (la même fonction utilisée quand l'action tourne seule, hors pipeline).
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str
    action: ActionSpec
    build_step_input: Callable[[InputT, dict], BaseModel]
    capture_stdout: bool = False


class PipelineSpec(BaseModel, Generic[InputT]):
    id: str
    label: str
    steps: list[PipelineStepSpec]

    model_config = ConfigDict(arbitrary_types_allowed=True)
    input_cls: type(BaseModel)
    
    def to_pipeline(
        self, 
        engines_by_tool: dict[str, CommandEngine], 
        pipeline_input: InputT,
        timeout: float = 300,
    ) -> Pipeline:
        """
        engines_by_tool : {"ffmpeg": <CommandEngine du job>, "sox": <...>}
        — un engine déjà construit par outil, tous partageant le même
        workdir (celui du job en cours).
        """
        steps = []
        for step_spec in self.steps:
            engine = engines_by_tool[step_spec.action.tool]

            def build_args(outputs: dict, _step_spec=step_spec, _engine=engine) -> list:
                step_input = _step_spec.build_step_input(pipeline_input, outputs)
                _step_spec.action.validate_args(step_input, workdir=_engine.workdir)
                return _step_spec.action.full_args(step_input)

            def output_filename(outputs: dict, _step_spec=step_spec) -> str:
                step_input = _step_spec.build_step_input(pipeline_input, outputs)
                template = _step_spec.action.output_filename_template
                return template(step_input) if callable(template) else template

            steps.append(
                PipelineStep(
                    id=step_spec.id,
                    engine=engine,
                    build_args=build_args,
                    output_filename=output_filename,
                    capture_stdout=step_spec.capture_stdout,
                    timeout=timeout
                )
            )
        return Pipeline(steps)