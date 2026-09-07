#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 14:23:02 2026

@author: hounsousamuel
"""

"""
Test du flux complet de MainEngine (ActionSpec & PipelineSpec).
"""

import asyncio
import tempfile
from pathlib import Path
from pydantic import BaseModel

# Imports de votre projet Workbench
from workbench.api.config import WbConfig
from workbench.core.orchestrator import MainEngine
from workbench.specs.specs import ActionSpec
from workbench.specs.pipeline_spec import PipelineSpec, PipelineStepSpec
from workbench.core.subprocess.wb_subprocess_types import (
    BoolArg, PathArg, PatternArg, Arg
)
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig


# =============================================================================
# 1. MODÈLES PYDANTIC POUR LES INPUTS UTILISATEUR
# =============================================================================

class LsInput(BaseModel):
    show_all: bool = True
    long_format: bool = True


class GrepInput(BaseModel):
    pattern: str
    input_file: str


class PipelineFilterInput(BaseModel):
    keyword: str


# =============================================================================
# 2. DÉFINITION DES SPECS (LS & GREP)
# =============================================================================

# Configuration de vérification des versions
ls_bin_config = BinVersionCheckerConfig(
    cmd="--version", 
    marker="coreutils", 
    tool_name="ls"
)

grep_bin_config = BinVersionCheckerConfig(
    cmd="--version", 
    marker="grep", 
    tool_name="grep"
)

# ActionSpec pour "ls"
ls_action_spec = ActionSpec[LsInput](
    id="list_directory",
    label="Lister les fichiers du dossier",
    tool="ls",
    binary_config=ls_bin_config,
    output_filename_template="ls_output.txt",
    build_args=lambda user_in: [
        BoolArg(flag="-a", value=user_in.show_all),
        BoolArg(flag="-l", value=user_in.long_format),
    ]
)

# ActionSpec pour "grep"
grep_action_spec = ActionSpec[GrepInput](
    id="filter_pattern",
    label="Filtrer un fichier texte",
    tool="grep",
    binary_config=grep_bin_config,
    output_filename_template="filtered_output.txt",
    build_args=lambda user_in: [
        PatternArg(flag="", value=user_in.pattern),
        PathArg(flag="", value=user_in.input_file, must_exist=True),
    ]
)

# PipelineSpec : ls -> grep
pipeline_spec = PipelineSpec[PipelineFilterInput](
    id="ls_then_grep_pipeline",
    label="Lister puis filtrer par mot-clé",
    steps=[
        # Étape 1 : ls (on capture son stdout dans ls_output.txt)
        PipelineStepSpec[PipelineFilterInput](
            id="step_ls",
            action=ls_action_spec,
            build_step_input=lambda pipe_in, outputs: LsInput(show_all=True, long_format=True),
            capture_stdout=True
        ),
        # Étape 2 : grep prend la sortie de l'étape 1 et cherche le mot-clé
        PipelineStepSpec[PipelineFilterInput](
            id="step_grep",
            action=grep_action_spec,
            build_step_input=lambda pipe_in, outputs: GrepInput(
                pattern=pipe_in.keyword,
                input_file=outputs["_previous"]
            ),
            capture_stdout=True
        )
    ]
)


# =============================================================================
# 3. FONCTIONS DE TEST
# =============================================================================

async def test_single_action_spec():
    """TEST 1 : Exécution d'un job simple (ActionSpec) avec logs en direct."""
    print("\n" + "=" * 70)
    print("🧪 TEST 1 : FLUX COMPLET ACTION SPEC (ls -la)")
    print("=" * 70)

    # 1. Préparation de l'environnement et du workdir
    with tempfile.TemporaryDirectory() as tmp_workdir:
        # Création de quelques fichiers de test dans le workdir
        (Path(tmp_workdir) / "test_video.mp4").touch()
        (Path(tmp_workdir) / "notes.txt").write_text("Hello World\nCybersecurity")
        (Path(tmp_workdir) / "script.py").touch()

        config = WbConfig(max_concurrent_job=5)
        orchestrator = MainEngine(config)
        # Sécurité si _tasks n'était pas initialisé dans le __init__
        if not hasattr(orchestrator, "_tasks") or orchestrator._tasks is None:
            orchestrator._tasks = {}

        orchestrator.start()

        # 2. Callbacks de test
        async def on_exec_log(payload: dict):
            stream = payload.get("stream", "info")
            text = payload.get("text", "").rstrip()
            print(f"  [STREAM {stream.upper()}] {text}")

        done_event = asyncio.Event()

        def on_done(task):
            print("  🏁 [DONE_CALLBACK] Le job d'action est terminé !")
            done_event.set()

        job_id = orchestrator.job_id()
        print(f"🚀 Démarrage du job Action : {job_id}")

        # 3. Création et lancement du job
        user_input = LsInput(show_all=True, long_format=True)
        job_info = orchestrator.create_job(
            spec=ls_action_spec,
            job_id=job_id,
            workdir=tmp_workdir,
            user_input=user_input,
            exec_callback=on_exec_log,
            done_callback=on_done,
            timeout=10
        )

        # 4. Attente de la fin du job
        await done_event.wait()
        await job_info["entry"].task

        print(f"✅ Code de retour final : {job_info['entry'].task.result()}")
        await orchestrator.stop()


async def test_pipeline_spec():
    """TEST 2 : Exécution d'un PipelineSpec chaîné (ls -> grep)."""
    print("\n" + "=" * 70)
    print("🧪 TEST 2 : FLUX COMPLET PIPELINE SPEC (ls -> grep 'video')")
    print("=" * 70)

    with tempfile.TemporaryDirectory() as tmp_workdir:
        # Fichiers de test
        (Path(tmp_workdir) / "video_sample1.mp4").touch()
        (Path(tmp_workdir) / "video_sample2.mkv").touch()
        (Path(tmp_workdir) / "document.pdf").touch()
        (Path(tmp_workdir) / "archive.zip").touch()

        config = WbConfig(max_concurrent_job=5)
        orchestrator = MainEngine(config)
        if not hasattr(orchestrator, "_tasks") or orchestrator._tasks is None:
            orchestrator._tasks = {}

        orchestrator.start()

        # Callback pour observer le chaînage des étapes
        async def on_pipeline_log(payload: dict):
            step = payload.get("step", "unknown_step")
            stream = payload.get("stream", "info")
            text = payload.get("text", "").rstrip()
            print(f"  [{step} | {stream.upper()}] {text}")

        done_event = asyncio.Event()

        def on_done(task):
            print("  🏁 [DONE_CALLBACK] Le Pipeline complet est terminé !")
            done_event.set()

        job_id = orchestrator.job_id()
        print(f"🚀 Démarrage du Pipeline : {job_id}")

        # Input global du pipeline : chercher "video"
        pipeline_input = PipelineFilterInput(keyword="video")

        job_info = orchestrator.create_job(
            spec=pipeline_spec,
            job_id=job_id,
            workdir=tmp_workdir,
            user_input=pipeline_input,
            exec_callback=on_pipeline_log,
            done_callback=on_done,
            timeout=15
        )

        await done_event.wait()
        await job_info["entry"].task

        # Vérification du fichier final généré dans le workdir
        output_file = Path(tmp_workdir) / "filtered_output.txt"
        if output_file.exists():
            print(f"\n📄 Contenu produit par l'étape finale ({output_file.name}) :")
            print("--------------------------------------------------")
            print(output_file.read_text().rstrip())
            print("--------------------------------------------------")

        await orchestrator.stop()


# =============================================================================
# 4. POINT D'ENTRÉE PRINCIPAL
# =============================================================================

async def main():
    await test_single_action_spec()
    await test_pipeline_spec()

if __name__ == "__main__":
    asyncio.run(main())