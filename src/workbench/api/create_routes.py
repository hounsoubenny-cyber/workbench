#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 23:58:58 2026

@author: hounsousamuel
"""

import sys
import json
import shutil
import uvicorn
import tempfile
import threading
from pathlib import Path
from typing import Callable
from pydantic import ValidationError
from fastapi import (
    HTTPException, status, APIRouter, Request, WebSocket,
    UploadFile, File, Form,
)
from fastapi.responses import StreamingResponse
from workbench.core.orchestrator import (
    MainEngine, TooManyJobs, InvalidSpecError, JobAlreadyExists,
    Spec, _is_action_spec
)
from workbench.specs.raw_engine import (
    RawEntry, raw_to_custom_spec, CustomActionSpec,
    EmptyBaseModel
)
from workbench.core.subprocess.engine import resolve_sandboxed_path, PathTraversalError
from workbench.specs.uploads import collect_upload_filenames
from workbench.wb_utils.job_file_cleaner import AsyncJobFileCleaner
from workbench.api.models import (
    UpdateConfigData, CreateJobWithCatalogData
)
from workbench.wb_utils.error_mapper import map_orchestrator_error
from workbench.wb_utils.job_buffer_manager import JobStatus
from workbench.core.subprocess.version_checker import Config as BinVersionCheckerConfig
from workbench.wb_utils.model_parser import model_to_dict
from workbench.api.config import StartConfig

def iterfile(path, chunk_size: int = 1024 * 1024):
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk


def create_workdir(job_id: str) -> str:
    path = tempfile.mkdtemp(prefix=job_id)
    return path

def validate_workdir(path: str):
    if not Path(path).is_absolute():
        return False
    
    if not str(path).startswith(tempfile.gettempdir()):
        return False
    
    jid = MainEngine.job_id()
    basename = Path(path).name
    if len(basename) < len(jid):
        return False
 
    job_id = basename[:len(jid)]
    return MainEngine.validate_job_id(job_id)

def resolve_user_input(spec: Spec, raw: dict):
    model_cls = spec.input_cls
    return model_cls.model_validate(raw)
 
 
def summarize_spec(spec: Spec) -> dict:
    from workbench.specs.pipeline_spec import PipelineSpec as _PipelineSpec
    if isinstance(spec, _PipelineSpec):
        return {
            "id": spec.id,
            "label": spec.label,
            "type": "pipeline",
            "steps": [
                {"id": s.id, "tool": s.action.tool, "action_id": s.action.id, "label": s.action.label}
                for s in spec.steps
            ],
        }
    return {
        "id": spec.id,
        "label": spec.label,
        "type": "action",
        "tool": spec.tool,
        "min_version": spec.min_version,
    }

def save_uploaded_files(user_input, workdir: str, files: list[UploadFile], expected: list | None = None) -> None:
    """
    Enregistre les fichiers uploadés dans le workdir du job, RENOMMÉS selon
    les noms que `user_input` a lui-même demandés (champs marqués
    `UploadRef`, voir specs/uploads.py) — dans l'ordre de déclaration du
    modèle (et l'ordre de la liste pour un champ list[str]).
 
    Générique par construction : ne connaît RIEN de la spec en cours, juste
    du modèle Pydantic déjà validé. Fonctionne pareil pour 0, 1 ou N
    fichiers (ex: ffmpeg -i multiple, concat, etc).
    """
    if not expected:
        expected = collect_upload_filenames(user_input)
 
    if len(expected) != len(files):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "UPLOAD_COUNT_MISMATCH",
                "message": (
                    f"{len(expected)} fichier(s) attendu(s) {expected}, "
                    f"{len(files)} reçu(s)."
                ),
            },
        )
 
    if len(set(expected)) != len(expected):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error_code": "DUPLICATE_UPLOAD_NAME",
                "message": f"Noms de fichiers en double dans user_input: {expected}",
            },
        )
 
    for filename, upload in zip(expected, files):
        try:
            dest = resolve_sandboxed_path(filename, Path(workdir))
        except PathTraversalError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"error_code": "INVALID_UPLOAD_NAME", "message": str(e)},
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            shutil.copyfileobj(upload.file, f)
 


def _server_error(e: Exception) -> HTTPException:
    """
    Formate une exception en HTTPException 500.

    Args:
        e (Exception): L'exception à formater.

    Returns:
        HTTPException: Une exception HTTP 500 avec les détails.
    """
    print(e)
    import traceback
    traceback.print_exc()
    err = map_orchestrator_error(e)
    return HTTPException(
        status_code=err["status_code"],
        detail={"error": str(e), "type": type(e).__name__, **err},
    )

def get_loop():
    return "uvloop" if sys.platform != "win32" else "asyncio"


    
def start(app, start_config: StartConfig):
    """Démarre le serveur dans un thread séparé."""
    host, port = start_config.host, start_config.port
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        loop=get_loop(),
        workers=1,
        log_level=start_config.log_level,
        access_log=start_config.access_log
    )
    server = uvicorn.Server(config=config)
    start_config.server = server
    th = threading.Thread(target=server.run, daemon=True)
    return th, server


def stop(th: threading.Thread, timeout: int = 5):
    """Arrête proprement le thread serveur."""
    print("Arrêt du serveur...")
    th.join(timeout)
    print("Serveur arrêté.")
    
def create_router(
    orchestrator: MainEngine,
    show_specs_func: Callable,
    get_spec_func: Callable,
    get_binary_config: Callable,
    job_file_cleaner: AsyncJobFileCleaner,
    save_config_func: Callable | None = None
):
    router = APIRouter()
    
    @router.get("/download")
    async def download(request: Request, workdir: str, path: str):
        if not validate_workdir(workdir):
            raise HTTPException(
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
                detail="INVALID_WORKDIR"
            ) 
            
        base_dir = Path(workdir).resolve()
        target_path = (base_dir / path).resolve()
        
        if not target_path.is_relative_to(base_dir):
            raise HTTPException(status_code=403, detail="FORBIDDEN_PATH")
            
        if target_path.exists() and target_path.is_file():
            return StreamingResponse(
                iterfile(str(target_path)), 
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={target_path.name}"}
            )
        
        raise HTTPException(status_code=404, detail="Fichier introuvable.")
    
    @router.get("/spec/{spec_id}/info")
    async def spec_info(request: Request, spec_id: str):
        try:
            spec: Spec = get_spec_func(spec_id)
            if not spec:
                return {"success": False,}
            return {
                "input": model_to_dict(spec.input_cls),
                "summary": summarize_spec(spec),
                "success": True,
                "is_action_spec": _is_action_spec(spec)
            }
        except HTTPException:
            raise
        
        except Exception as e:
            raise _server_error(e)
            
    @router.get("/config")
    async def get_config(request: Request):
        try:
            return orchestrator.config.model_dump(mode="json")
        except HTTPException:
            raise
        
        except Exception as e:
            raise _server_error(e)
    
    @router.post("/config")
    async def set_config(request: Request, data: UpdateConfigData):
        try:
            data = dict(data.model_dump())
            data = {k: v for k, v in data.items() if v is not None}
            new_config = orchestrator.config.model_copy(update=data)
            try:
                if callable(save_config_func):
                    save_config_func(new_config)
            except Exception:
                pass
            
            return {"success": orchestrator.set_config(new_config)}

        
        except HTTPException:
            raise
        
        except Exception as e:
            raise _server_error(e)
    
    @router.get("/catalog")
    async def catalog(request: Request):
        try:
            return show_specs_func()
        
        except HTTPException:
            raise
        
        except Exception as e:
            raise _server_error(e)
    
    @router.post("/job/create")
    async def create_job(
        request: Request,
        data: str = Form(...),
        files: list[UploadFile] = File(default_factory=list),
    ):
        try:
            try:
                raw = json.loads(data)
                create_data = CreateJobWithCatalogData.model_validate(raw)
            except (json.JSONDecodeError, ValidationError) as e:
                if isinstance(e, ValidationError):
                    raise _server_error(e)
                    
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error_code": "INVALID_DATA_FIELD", "message": str(e)},
                )


            spec: Spec = get_spec_func(create_data.id)
            if not spec:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Spec '{create_data.id}' introuvable."
                )
            
            job_id = orchestrator.job_id()
            workdir = create_workdir(job_id)
            
            try:
                user_input = resolve_user_input(spec, create_data.user_input)
            except ValidationError as e:
                shutil.rmtree(workdir, ignore_errors=True)
                err = map_orchestrator_error(e)
                raise HTTPException(status_code=err["status_code"], detail=err)

            try:
                save_uploaded_files(user_input, workdir, files)
            except HTTPException:
                shutil.rmtree(workdir, ignore_errors=True)
                raise


            try:
                entry = orchestrator.create_job(
                    spec=spec,
                    job_id=job_id,
                    workdir=workdir,
                    user_input=user_input,
                    timeout=create_data.timeout,
                    job_file_cleaner=job_file_cleaner
                )
            except (JobAlreadyExists, TooManyJobs, InvalidSpecError) as e:
                shutil.rmtree(workdir, ignore_errors=True)
                return map_orchestrator_error(e)

            
            except Exception as e:
                shutil.rmtree(workdir, ignore_errors=True)
                raise e
             
            entry = entry["entry"]
            return {
                "workdir": workdir,
                "job_id": job_id,
                "spec": summarize_spec(entry.spec), 
                "is_action_spec": entry.is_action_spec,
                "output_files": entry.output_files,
                "is_custom_spec": False,
            }
        
        except HTTPException:
            raise
        
        except Exception as e:
            raise _server_error(e)
    
    @router.get("/job/stop")
    async def stop_job(request: Request, job_id: str):
        try:
            r = await orchestrator.stop_job(job_id)
            return {"success": r}
        
        except HTTPException:
            raise
        
        except Exception as e:
            raise _server_error(e)
    
    @router.get("/job/status")
    async def job_status(request: Request, job_id: str):
        try:
            job = orchestrator.get_job(job_id)
            if not job:
                return {"status": JobStatus.FINISHED.value}
            
            if job.job_buffer_manager:
                return {"status": job.job_buffer_manager.status}
            
            return {"status": "uknown"}
        
        except HTTPException:
            raise
        
        except Exception as e:
            raise _server_error(e)
            
    @router.websocket("/job/ws/logs")
    async def job_logs(ws: WebSocket, job_id: str):
        return await orchestrator.on_ws(ws, job_id)
        
    # ensuite job/advanced viendra pour des specs custum
    
    @router.post("/job/advanced/create")
    async def create_advanced_job(
        request: Request,
        data: str = Form(...),
        files: list[UploadFile] = File(default_factory=list),
    ):
        try:
            try:
                raw = json.loads(data)
                create_data: RawEntry = RawEntry.model_validate(raw)
            except (json.JSONDecodeError, ValidationError) as e:
                if isinstance(e, ValidationError):
                    raise _server_error(e)
                    
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"error_code": "INVALID_DATA_FIELD", "message": str(e)},
                )
            
            binary_config: dict | BinVersionCheckerConfig = get_binary_config(create_data.tool)
            
            spec: CustomActionSpec = raw_to_custom_spec(create_data, binary_config)
            user_input = EmptyBaseModel()
            job_id = orchestrator.job_id()
            workdir = create_workdir(job_id)
            
            try:
                save_uploaded_files(
                    user_input=user_input,
                    workdir=workdir,
                    files=files,
                    expected=spec.collected_upload_files
                )
            except HTTPException:
                shutil.rmtree(workdir, ignore_errors=True)
                raise


            try:
                entry = orchestrator.create_job(
                    spec=spec,
                    job_id=job_id,
                    workdir=workdir,
                    user_input=user_input,
                    timeout=spec.timeout,
                    job_file_cleaner=job_file_cleaner
                )
            except (JobAlreadyExists, TooManyJobs, InvalidSpecError) as e:
                shutil.rmtree(workdir, ignore_errors=True)
                return map_orchestrator_error(e)

            
            except Exception as e:
                shutil.rmtree(workdir, ignore_errors=True)
                raise e
             
            entry = entry["entry"]
            return {
                "workdir": workdir,
                "job_id": job_id,
                "spec": summarize_spec(entry.spec), 
                "is_action_spec": entry.is_action_spec,
                "is_custom_spec": True,
                "output_files": entry.output_files
            }
        
        except HTTPException:
            raise
        
        except Exception as e:
            raise _server_error(e)
            
    return router