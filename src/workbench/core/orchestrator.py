#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep  2 00:08:16 2026

@author: hounsousamuel
"""

import asyncio
from pathlib import Path
from secrets import token_urlsafe
from dataclasses import dataclass
from pydantic import ValidationError, BaseModel
from typing import Dict, Union, Callable, List
from fastapi import WebSocket, WebSocketDisconnect, status, WebSocketException
from workbench.api.config import WbConfig
from workbench.core.subprocess.pipeline import Pipeline
from workbench.specs.pipeline_spec import PipelineSpec
from workbench.specs.specs import ActionSpec
from workbench.core.subprocess.wb_subprocess_types import Arg
from workbench.core.subprocess.engine import CommandEngine, ExecResult
from workbench.wb_utils.tasks_utils import stop_task
from workbench.wb_utils.funcs_utils import exec_func
from workbench.wb_utils.job_buffer_manager import JobBufferManager, JobStatus
from workbench.wb_utils.job_file_cleaner import AsyncJobFileCleaner
Spec = Union[PipelineSpec, ActionSpec]

@dataclass
class _TaskEntry:
    spec: Spec
    task: asyncio.Task
    workdir: str
    job_id: str
    job_buffer_manager: JobBufferManager
    user_input: BaseModel
    is_action_spec: bool
    output_files: list[dict]
    exec_result: ExecResult | Dict = None
    engine: CommandEngine = None
    pipeline: Pipeline = None
    args: List[Arg] | None = None # None pour pipeline
    _done: bool = False
    
def _is_action_spec(spec: Spec):
    return isinstance(spec, ActionSpec)

def _is_pipeline_spec(spec: Spec):
    return isinstance(spec, PipelineSpec)

class InvalidSpecError(Exception):
    pass

class TooManyJobs(Exception):
    pass

class JobAlreadyExists(Exception):
    pass

class ValidateArgError(Exception):
    def __init__(self, base_exception: Exception, *args):
        self.base_exception = base_exception
        super().__init__(*args)
        
class MainEngine:
    def __init__(self, config: WbConfig):
        self.config = config
        self._tasks: Dict[str, _TaskEntry] = {}
        self._cleanup_task = None
    
    def start(self):
        self._cleanup_task = asyncio.create_task(self.cleanup_task())
    
    async def stop(self, stop_tasks: bool = False):
        if self._cleanup_task and not self._cleanup_task.done():
            await stop_task(self._cleanup_task, 120)
        
        if stop_tasks:
            async def stop(job_id: str):
                await self.stop_job(job_id)
                self.remove_job(job_id)
                
            if self._tasks:
                tasks_copy = list(self._tasks.items())
                to_remove = [k for k, _ in tasks_copy]
                        
                if to_remove:
                    await asyncio.gather(
                        *[stop(k) for k in to_remove],
                        return_exceptions=True
                    )
                
    def set_config(self, config: WbConfig | Dict):
        try:
            self.config = WbConfig.model_validate(config)
            for entry in self._tasks.values():
                if entry.job_buffer_manager.config:
                    entry.job_buffer_manager.config = config.model_copy()
        except ValidationError:
            return False
        
        return True
    
    @staticmethod
    def job_id():
        return "wb-job_" + token_urlsafe(32)
    
    @staticmethod
    def validate_job_id(job_id: str):
        return len(job_id) == len(MainEngine.job_id()) and job_id.startswith("wb-job_")
    
    async def cleanup_task(self):
        """
        Loop de cleanup, au cas ou les done callback echouent
        """
        async def stop(job_id: str):
            await self.stop_job(job_id)
            self.remove_job(job_id)
            
        while True:
            if self._tasks:
                tasks_copy = list(self._tasks.items())
                to_remove = []
                for k, entry in tasks_copy:
                    if entry.task and entry.task.done():
                        to_remove.append(k)
                        
                if to_remove:
                    await asyncio.gather(
                        *[stop(k) for k in to_remove],
                        return_exceptions=True
                    )
            
            await asyncio.sleep(60)
    
    def get_job(self, job_id: str):
        return self._tasks.get(job_id, None)
    
    def create_job(
        self, 
        spec: Spec,
        job_id: str,
        workdir: str,
        user_input: BaseModel,
        done_callback: Callable | None = None,
        exec_callback: Callable | None = None,
        timeout: float | None = 300,
        job_file_cleaner: AsyncJobFileCleaner | None = None
    ):
        if not any(f(spec) for f in (_is_action_spec, _is_pipeline_spec)):
            raise InvalidSpecError
        
        max_jobs = self.config.max_concurrent_job
        n_active_jobs = sum(not entry._done for entry in self._tasks.values())
        if n_active_jobs >= max_jobs:
            raise TooManyJobs
        
        if job_id in self._tasks:
            raise JobAlreadyExists
            
        if _is_action_spec(spec):
            entry = self.create_action_spec_entry(
                job_id=job_id, 
                spec=spec, 
                workdir=workdir, 
                user_input=user_input, 
            )
        else:
            entry = self.create_pipeline_spec_entry(
                job_id=job_id, 
                spec=spec, 
                workdir=workdir, 
                user_input=user_input, 
                timeout=timeout
            )
        
        task = asyncio.create_task(
            self.execute_entry(
                entry=entry,
                timeout=timeout,
                exec_callback=exec_callback,
            )
        )
        
        def on_done(t):
            try:
                entry._done = True
                if done_callback and callable(done_callback):
                    done_callback(t)
                
                if job_file_cleaner:
                    for f in entry.output_files:
                        file = f["file"]
                        if not file:
                            continue
                        path = Path(Path(workdir) / Path(file)).resolve()
                        job_file_cleaner.register(str(path), path.is_dir(), self.config.file_ttl)
                
                    wtimeout = timeout or 3600
                    wtimeout += (job_file_cleaner.default_ttl or 15 * 60)
                    job_file_cleaner.register(workdir, is_dir=True) # ttl=wtimeout
                
                async def _delayed_remove(job_id: str):
                    try:
                        await asyncio.sleep(self.config.buffer_clear_delay)
                    except asyncio.CancelledError:
                        pass
                    self.remove_job(job_id)
    
                asyncio.create_task(_delayed_remove(job_id))
            
            except Exception as e:
                # Log l'erreur
                print(f"⚠️ Callback error: {e!r}")
        
        task.add_done_callback(on_done)
        entry.task = task
        self._tasks[job_id] = entry
        return {
            "job_id": job_id,
            "workdir": workdir,
            "entry": entry,
        }
    
    def create_action_spec_entry(
        self,
        job_id: str,
        spec: ActionSpec,
        workdir: str,
        user_input: BaseModel,
    ):
        if spec.validate_arg and callable(getattr(spec, "validate_args", None)):
            try:
                spec.validate_args(user_input, Path(workdir))
            except Exception as e:
                raise ValidateArgError(base_exception=e)
            
        args = spec.full_args(user_input)
        engine = CommandEngine(
            workdir=workdir,
            binary=spec.tool,
            min_version=spec.min_version,
            binary_config=spec.binary_config,
            check_version=spec.check_version
        )
        job_buffer_manager = JobBufferManager(self.config)
        file = spec.output_filename_template
        if callable(file):
            file = file(user_input)
            
        return _TaskEntry(
            task=None,
            spec=spec,
            workdir=workdir,
            job_id=job_id,
            engine=engine,
            job_buffer_manager=job_buffer_manager,
            args=args,
            is_action_spec=True,
            user_input=user_input,
            output_files=[
                {"id": spec.id, "last": True, "file": file, "pos": 0}
            ]
        )
    
    def create_pipeline_spec_entry(
        self,
        job_id: str,
        spec: PipelineSpec,
        workdir: str,
        user_input: BaseModel,
        timeout: float | None = 300,
    ):
        engines = {}
        output_files = []
        for i, step in enumerate(spec.steps):
            action_spec = step.action
            engine = CommandEngine(
                workdir=workdir,
                binary=action_spec.tool,
                min_version=action_spec.min_version,
                binary_config=action_spec.binary_config,
                check_version=action_spec.check_version
            )
            engines[action_spec.tool] = engine
            template = action_spec.output_filename_template
            if callable(template):
                try:
                    step_input = step.build_step_input(user_input, {})
                    file = template(step_input)
                except Exception:
                    file = None
            else:
                file = template
            output_files.append({
                "id": step.id,
                "file": file,
                "pos": i,
                "last": i == len(spec.steps) - 1
            })
                
        job_buffer_manager = JobBufferManager(self.config)
        pipeline = spec.to_pipeline(
            engines_by_tool=engines,
            timeout=timeout,
            pipeline_input=user_input,
        )
        return _TaskEntry(
            task=None,
            spec=spec,
            workdir=workdir,
            job_id=job_id,
            job_buffer_manager=job_buffer_manager,
            args=None,
            is_action_spec=False,
            pipeline=pipeline,
            user_input=user_input,
            output_files=output_files
        )
    
    async def execute_entry(
        self,
        entry: _TaskEntry,
        timeout: float | None = 300,
        exec_callback: Callable | None = None,
    ):
        job_buffer_manager = entry.job_buffer_manager
        
        async def on_output(*args, **kwargs):
            if exec_callback and callable(exec_callback):
                await exec_func(exec_callback, *args, **kwargs)
            
            await exec_func(job_buffer_manager.callback, *args, **kwargs)
            
        if entry.is_action_spec:            
            outputs = entry.output_files
            if not outputs or not outputs[0]["file"]:
                file = entry.spec.output_filename_template
                if callable(file):
                    file = file(entry.user_input)
            else:
                file = outputs[0]["file"]
            
            
            exec_result: ExecResult = await entry.engine.execute_async(
                args=entry.args if entry.args else entry.spec.full_args(entry.user_input),
                timeout=timeout,
                on_output=on_output,
                output_filename=file,
                capture_stdout=entry.spec.capture_stdout
            )
            await job_buffer_manager.send(
                message={"type": "job_result", "result": exec_result.to_dict()}
            )
            
        else: # Pipeline
            exec_result: Dict = await entry.pipeline.run(
                initial_inputs=dict(entry.user_input),
                on_output=on_output,
            )
            for f in entry.output_files:
                real_file = exec_result.get(f["id"])
                if real_file is not None:
                    f["file"] = real_file

            await job_buffer_manager.send(
                message={"type": "job_result", "result": exec_result}
            )
        
        entry.job_buffer_manager.status = JobStatus.FINISHED.value
        entry.exec_result = exec_result
        
        await job_buffer_manager.send(
            message={"type": "job_end"}
        )
        return entry
        
    async def stop_job(self, job_id: str) -> bool:
        if job_id not in self._tasks:
            return False
        
        if job_id in self._tasks:
            entry = self._tasks[job_id]
            await stop_task(entry.task)
            await entry.job_buffer_manager.send(
                message={"type": "info", "message": "job_stop"}
            )
            entry.job_buffer_manager.status = JobStatus.STOP.value
        
        self.remove_job(job_id)
        return True
        
    def remove_job(self, job_id: str):
        return self._tasks.pop(job_id, None)
        
    async def on_ws(
        self,
        ws: WebSocket,
        job_id: str
    ):
        entry = self._tasks.get(job_id, None)
        if not entry:
            await ws.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Job Introuvable"
            )
            return
        
        if not await entry.job_buffer_manager.connect(ws):
            await entry.job_buffer_manager.disconnect()
            return
        
        if entry.job_buffer_manager.status != JobStatus.RUNNING:
            r = entry.exec_result
            if hasattr(r, "to_dict"):
                r = r.to_dict()
                
            await entry.job_buffer_manager.send(
                message={"type": "job_result", "result": r}
            )
            await entry.job_buffer_manager.send(
                message={"type": "job_end"}
            )
            return
    
        try:
            while True:
                try:
                    await asyncio.wait_for(
                        entry.job_buffer_manager.receive(),
                        120
                    )
                except asyncio.TimeoutError:
                    continue
                
                except Exception:
                    break
                
        except (WebSocketDisconnect, WebSocketException):
            await entry.job_buffer_manager.schedule_cleanup()
            
        
        finally:
            await entry.job_buffer_manager.disconnect()

if __name__ == "__main__":
    pass
    