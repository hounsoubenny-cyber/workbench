#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 23:32:20 2026

@author: hounsousamuel
"""

"""
Catalogue de demo — VRAIES specs (ls, grep, ffmpeg) utilisees par les deux
fichiers de test (test_api_client_full.py et test_live_client.py).

Volontairement mis dans un module a part (workbench/examples/) : les deux
suites de test l'importent, pour etre certaines de tester exactement le
meme catalogue, construit exactement comme documente dans
core/test_orchestrator.py (le seul exemple "officiel" existant dans le
projet).
"""

from pydantic import BaseModel, Field

from workbench.specs.specs import ActionSpec
from workbench.specs.pipeline_spec import PipelineSpec, PipelineStepSpec
from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    BoolArg, PathArg, FloatArg, PatternArg, MultiPathMode, MultiPathArg
)
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
from workbench.specs.uploads import UploadRef

# =============================================================================
# 1. MODELES PYDANTIC POUR LES INPUTS UTILISATEUR (un par ActionSpec)
# =============================================================================

class LsInput(BaseModel):
    show_all: bool = True
    long_format: bool = True


class GrepInput(BaseModel):
    pattern: str
    # Marque UploadRef : quand `filter_pattern` est lancee SEULE (hors
    # pipeline), ce nom est celui d'un fichier a UPLOADER (voir
    # save_uploaded_files dans create_routes.py) — sans ca, le workdir est
    # toujours vide au demarrage d'un job standalone, donc grep n'aurait
    # jamais rien a lire. (Dans le pipeline ls_then_grep_pipeline,
    # GrepInput est construit en interne via build_step_input — jamais par
    # ce chemin d'upload, donc aucun conflit.)
    input_file: str = UploadRef(description="Fichier texte a uploader")
 



class GenerateVideoInput(BaseModel):
    duration_s: float = Field(default=1.0, ge=0.1, le=5.0)
    size: str = "64x64"  # ex: "64x64" — pas de ':' donc OK pour un futur PathArg,
                          # mais ici c'est un parametre lavfi -> PatternArg.


class ConvertToGifInput(BaseModel):
    # Meme raisonnement que GrepInput.input_file : chaque job a son PROPRE
    # workdir vide au depart, donc `convert_to_gif` standalone a besoin
    # d'un vrai upload pour avoir une video a convertir.
    input_file: str = UploadRef(description="Vidéo à uploader")
    width: int = Field(default=64, ge=8, le=640)
    duration_s: float = Field(default=1.0, ge=0.1, le=120.0)



class ConcatVideosInput(BaseModel):
    """
    Demo de MultiPathArg + UploadRef sur une liste : concatene N videos
    uploadees, DANS L'ORDRE d'upload — cas d'usage exact evoque : ffmpeg
    avec plusieurs `-i`, pas un seul flag qui prend une liste.
    """
    inputs: list[str] = UploadRef(description="Vidéos à concaténer, dans l'ordre")
 
 
class PipelineFilterInput(BaseModel):
    """Input du pipeline complet ls -> grep : juste le mot-cle a chercher."""
    keyword: str



# =============================================================================
# 2. CONFIGS DE VERSION (marker = ce qu'on doit retrouver dans `<bin> --version`)
# =============================================================================

ls_bin_config = BinVersionCheckerConfig(cmd="--version", marker="coreutils", tool_name="ls")
grep_bin_config = BinVersionCheckerConfig(cmd="--version", marker="grep", tool_name="grep")
ffmpeg_bin_config = BinVersionCheckerConfig(cmd="-version", marker="ffmpeg", tool_name="ffmpeg")


# =============================================================================
# 3. ACTION SPECS — les vrais binaires : ls, grep, ffmpeg (x2)
# =============================================================================

# --- ls -a -l ---------------------------------------------------------------
ls_action_spec = ActionSpec[LsInput](
    id="list_directory",
    label="Lister les fichiers du dossier",
    tool="ls",
    binary_config=ls_bin_config,
    output_filename_template="ls_output.txt",
    build_args=lambda u: [
        BoolArg(flag="-a", value=u.show_all),
        BoolArg(flag="-l", value=u.long_format),
    ],
    input_cls=LsInput,
    capture_stdout=True,
)

# --- grep <pattern> <fichier> ------------------------------------------------
grep_action_spec = ActionSpec[GrepInput](
    id="filter_pattern",
    label="Filtrer un fichier texte par motif",
    tool="grep",
    binary_config=grep_bin_config,
    output_filename_template="filtered_output.txt",
    build_args=lambda u: [
        PatternArg(value=u.pattern),
        PathArg(value=u.input_file, must_exist=True),
    ],
    input_cls=GrepInput,
    capture_stdout=True,
)

# --- ffmpeg : genere une mini video de test (source lavfi, aucun fichier
#     d'entree requis) -------------------------------------------------------
def _generate_video_filename(u: GenerateVideoInput) -> str:
    return "generated.mp4"


generate_video_spec = ActionSpec[GenerateVideoInput](
    id="generate_test_video",
    label="Générer une vidéo de test (source synthétique lavfi)",
    tool="ffmpeg",
    binary_config=ffmpeg_bin_config,
    min_version=(4, 0),
    output_filename_template=_generate_video_filename,
    build_args=lambda u: [
        BoolArg(flag="-y", value=True),
        # "-f lavfi" : le format d'entree. Une simple valeur fermee -> EnumArg
        # serait possible, mais ici on illustre PatternArg pour la source
        # elle-meme, qui contient volontairement des ':' (testsrc=duration=..:
        # size=..:rate=..) — un caractere INTERDIT pour un PathArg (protection
        # anti "protocole ffmpeg" dans engine.py). PatternArg est le bon choix
        # ici : ce n'est pas un chemin, c'est un descripteur de filtre lavfi.
        PatternArg(flag="-f", value="lavfi"),
        PatternArg(
            flag="-i",
            value=f"testsrc=duration={u.duration_s}:size={u.size}:rate=10",
        ),
        FloatArg(flag="-t", value=u.duration_s, min_value=0.1, max_value=5.0),
        PathArg(value=_generate_video_filename(u)),
    ],
    input_cls=GenerateVideoInput,
)

# --- ffmpeg : convertit une video (deja presente dans le workdir) en gif ----
def _convert_to_gif_filename(u: ConvertToGifInput) -> str:
    return "thumb.gif"


convert_to_gif_spec = ActionSpec[ConvertToGifInput](
    id="convert_to_gif",
    label="Convertir une vidéo en GIF animé",
    tool="ffmpeg",
    binary_config=ffmpeg_bin_config,
    min_version=(4, 0),
    output_filename_template=_convert_to_gif_filename,
    build_args=lambda u: [
        BoolArg(flag="-y", value=True),
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        FloatArg(flag="-t", value=u.duration_s, min_value=0.1, max_value=5.0),
        # "scale=64:-1" contient ':' -> PatternArg (comme pour le "-i" plus
        # haut), pas PathArg.
        PatternArg(flag="-vf", value=f"scale={u.width}:-1"),
        PathArg(value=_convert_to_gif_filename(u)),
    ],
    input_cls=ConvertToGifInput
)

# --- ffmpeg : concatene N videos uploadees (demo MultiPathArg + UploadRef
#     sur une liste) ------------------------------------------------------
def _concat_videos_filename(u: ConcatVideosInput) -> str:
    return "concatenated.mp4"
 
 
concat_videos_spec = ActionSpec[ConcatVideosInput](
    id="concat_videos",
    label="Concaténer plusieurs vidéos (upload multiple)",
    tool="ffmpeg",
    binary_config=ffmpeg_bin_config,
    min_version=(4, 0),
    output_filename_template=_concat_videos_filename,
    build_args=lambda u: [
        BoolArg(flag="-y", value=True),
        # Repond exactement a la question posee : "-i f1 -i f2" (repete),
        # PAS "-i f1 f2" — c'est le mode REPEAT_FLAG qui encode cette
        # semantique, propre a ffmpeg (voir wb_subprocess_types.py).
        MultiPathArg(
            flag="-i", values=u.inputs, must_exist=True,
            mode=MultiPathMode.REPEAT_FLAG,
        ),
        PatternArg(
            flag="-filter_complex",
            value="".join(f"[{i}:v:0]" for i in range(len(u.inputs)))
                  + f"concat=n={len(u.inputs)}:v=1:a=0[outv]",
        ),
        PatternArg(flag="-map", value="[outv]"),
        PathArg(value=_concat_videos_filename(u)),
    ],
    input_cls=ConcatVideosInput
)


# =============================================================================
# 4. PIPELINE SPEC — ls -> grep (2 outils differents chaines)
# =============================================================================

pipeline_spec = PipelineSpec[PipelineFilterInput](
    id="ls_then_grep_pipeline",
    label="Lister puis filtrer par mot-clé",
    steps=[
        PipelineStepSpec[PipelineFilterInput](
            id="step_ls",
            action=ls_action_spec,
            build_step_input=lambda pipe_in, outputs: LsInput(show_all=True, long_format=True),
            capture_stdout=True,
        ),
        PipelineStepSpec[PipelineFilterInput](
            id="step_grep",
            action=grep_action_spec,
            build_step_input=lambda pipe_in, outputs: GrepInput(
                pattern=pipe_in.keyword,
                input_file=outputs["_previous"],
            ),
            capture_stdout=True,
        ),
    ],
    input_cls=PipelineFilterInput
)


# =============================================================================
# 5. CATALOGUE (utilise `registry.collect_specs`, comme prevu par
#    specs/registry.py — limite aux ActionSpec definies dans CE module)
# =============================================================================

_ACTION_SPECS: dict = collect_specs(__name__)

# collect_specs() ne connait que les ActionSpec (voir specs/registry.py,
# isinstance(obj, ActionSpec)) — les PipelineSpec ne sont pas "collectees"
# automatiquement, on les ajoute nous-memes au dict complet.
FULL_CATALOG: dict = {**_ACTION_SPECS}


def get_spec(spec_id: str):
    return FULL_CATALOG.get(spec_id)


def show_catalog() -> dict:
    """
    Formate le catalogue pour la route GET /catalog. On ne renvoie pas les
    objets Spec bruts (non-JSON-serialisables tels quels a cause des
    `Callable`) mais un resume utile a un client/CLI.
    """
    out = {}
    for spec_id, spec in FULL_CATALOG.items():
        if isinstance(spec, PipelineSpec):
            out[spec_id] = {
                "id": spec.id,
                "label": spec.label,
                "type": "pipeline",
                "steps": [
                    {"id": s.id, "tool": s.action.tool, "action_id": s.action.id}
                    for s in spec.steps
                ],
            }
        else:
            out[spec_id] = {
                "id": spec.id,
                "label": spec.label,
                "type": "action",
                "tool": spec.tool,
            }
    return out