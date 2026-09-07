#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 16:08:01 2026

@author: hounsousamuel
"""

import asyncio
from pydantic import ValidationError
from typing import Dict, Any

from workbench.core.orchestrator import (
    TooManyJobs, InvalidSpecError, JobAlreadyExists, ValidateArgError
)
from workbench.core.subprocess.engine import PathTraversalError, MissingPathError
from workbench.core.subprocess.version_checker import (
    BinaryNotFoundError, SuspiciousBinaryError, VersionParseError
)
from workbench.core.subprocess.pipeline import PipelineError


def map_orchestrator_error(exc: Exception) -> Dict[str, Any]:
    """
    Traduit une exception technique de l'orchestrateur en message
    utilisateur clair avec un code d'erreur et un statut HTTP/WS adapté.
    """
    # 1. Gestion des erreurs de Pipeline (on déroule l'erreur de l'étape)
    if isinstance(exc, PipelineError):
        inner_error = map_orchestrator_error(exc.original)
        return {
            "error_code": "PIPELINE_STEP_FAILED",
            "message": f"Échec de l'étape '{exc.step_id}' : {inner_error['message']}",
            "status_code": inner_error["status_code"],
            "details": {"step_id": exc.step_id, "cause": inner_error}
        }

    # 2. Erreurs de capacité et cycle de vie
    if isinstance(exc, TooManyJobs):
        return {
            "error_code": "TOO_MANY_JOBS",
            "message": "Le système est saturé : trop de tâches tournent en même temps. Réessayez dans un instant.",
            "status_code": 429
        }

    if isinstance(exc, InvalidSpecError):
        return {
            "error_code": "INVALID_SPEC",
            "message": "L'action demandée est invalide ou non reconnue par le système.",
            "status_code": 400
        }

    if isinstance(exc, JobAlreadyExists):
        return {
            "error_code": "JOB_ALREADY_EXISTS",
            "message": "Un job avec cet identifiant existe déjà ou est déjà en cours d'exécution.",
            "status_code": 409
        }

    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)):
        return {
            "error_code": "JOB_TIMEOUT",
            "message": "Le temps limite d'exécution a été dépassé. Le processus a été interrompu.",
            "status_code": 504
        }

    if isinstance(exc, asyncio.CancelledError):
        return {
            "error_code": "JOB_CANCELLED",
            "message": "La tâche a été arrêtée par l'utilisateur.",
            "status_code": 499
        }

    # 3. Erreurs de Sécurité et Fichiers (Sandboxing)
    if isinstance(exc, PathTraversalError):
        return {
            "error_code": "FORBIDDEN_PATH",
            "message": "Accès refusé : tentative d'accès à un fichier hors de l'espace de travail ou nom interdit.",
            "status_code": 403
        }

    if isinstance(exc, MissingPathError):
        return {
            "error_code": "FILE_NOT_FOUND",
            "message": "Le fichier source requis est introuvable sur le disque.",
            "status_code": 404
        }

    # 4. Erreurs de binaires CLI (ffmpeg, sox, magick)
    if isinstance(exc, BinaryNotFoundError):
        return {
            "error_code": "TOOL_MISSING",
            "message": f"Outil introuvable sur le système : {str(exc)}.",
            "status_code": 503
        }

    if isinstance(exc, SuspiciousBinaryError):
        return {
            "error_code": "TOOL_UNVERIFIED",
            "message": "Alerte de sécurité : l'exécutable système ne correspond pas à l'outil officiel attendu.",
            "status_code": 500
        }

    if isinstance(exc, VersionParseError):
        return {
            "error_code": "TOOL_VERSION_INCOMPATIBLE",
            "message": "La version de l'outil système installé est trop ancienne ou incompatible.",
            "status_code": 503
        }

    # 5. Validation des entrées utilisateur (Pydantic / Valeurs invalides / Validations métier)
    if isinstance(exc, ValidateArgError):
        # On extrait le message de l'exception d'origine encapsulée
        base_msg = str(exc.base_exception)
        return {
            "error_code": "VALIDATION_BUSINESS_ERROR",
            "message": f"Échec de la validation : {base_msg}",
            "status_code": 422
        }

    if isinstance(exc, ValidationError):
        first_err = exc.errors()[0]
        field = " -> ".join(str(loc) for loc in first_err.get("loc", []))
        msg = first_err.get("msg", "valeur invalide")
        return {
            "error_code": "INVALID_INPUT_PARAMS",
            "message": f"Paramètre invalide ({field}) : {msg}.",
            "status_code": 422
        }

    if isinstance(exc, ValueError):
        return {
            "error_code": "INVALID_ARGUMENT",
            "message": f"Argument incorrect : {str(exc)}.",
            "status_code": 400
        }
    
    if "Output file does not contain any stream" in str(exc) or "does not contain any stream" in str(getattr(exc, "stderr", "")):
        return {
            "error_code": "NO_AUDIO_STREAM_FOUND",
            "message": "La vidéo source ne contient aucune piste audio à extraire.",
            "status_code": 422
        }
    
    # 6. Erreur générique imprévue
    return {
        "error_code": "INTERNAL_ENGINE_ERROR",
        "message": f"Une erreur inattendue est survenue : {str(exc)}",
        "status_code": 500
    }

if __name__ == "__main__":
    import json
    from pydantic import BaseModel, Field

    print("="*60)
    print("🧪 TEST DU MAPPING D'ERREURS ORCHESTRATEUR")
    print("="*60)

    # Fonction utilitaire pour un affichage propre
    def test_error(name: str, exc: Exception):
        print(f"\n🟢 Test : {name}")
        print(f"   Exception brute : {repr(exc)}")
        mapped = map_orchestrator_error(exc)
        print(f"   Résultat API    : {json.dumps(mapped, indent=2, ensure_ascii=False)}")

    # 1. Erreur simple
    test_error("Erreur de valeur basique", ValueError("Le paramètre 'bitrate' est incorrect"))

    # 2. Erreur d'orchestration
    test_error("Orchestrateur saturé", TooManyJobs())

    # 3. Notre nouvelle erreur ValidateArgError (avec une exception métier imbriquée)
    base_err = Exception("Le fichier 'video.txt' n'a pas un en-tête multimédia valide.")
    test_error("Erreur de validation métier (ValidateArgError)", ValidateArgError(base_exception=base_err))

    # 4. Erreur de Pipeline (qui encapsule une autre erreur)
    bin_err = BinaryNotFoundError("ffmpeg")
    test_error("Erreur de Pipeline (imbriquée)", PipelineError(step_id="step_convert_audio", original=bin_err))

    # 5. Vraie erreur Pydantic
    class DummyModel(BaseModel):
        volume: int = Field(ge=0, le=100)

    try:
        DummyModel(volume=-10)
    except ValidationError as ve:
        test_error("Erreur Pydantic (ValidationError)", ve)