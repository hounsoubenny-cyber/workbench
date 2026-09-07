#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Workbench — Test interactif complet ("live") : lance le VRAI serveur
uvicorn en sous-processus, puis pilote un menu interactif (Rich) qui parle
au serveur en HTTP (httpx) et WebSocket (websockets) réels — aucun mock,
aucun TestClient in-process. Le catalogue est le vrai catalogue
(workbench/examples/demo_catalog.py) : ls, grep, ffmpeg x2, pipeline.

Lancer en mode interactif (comme prévu par Sam) :
    python3 -m workbench.api.test_live_client

Lancer en mode automatique (aucune saisie, pour CI / vérification rapide) :
    python3 -m workbench.api.test_live_client --auto
"""

import asyncio
import json
import sys
import time
import subprocess
import tempfile
import signal
from pathlib import Path
from typing import Optional, Dict, Callable, Any
from datetime import datetime

import httpx
import websockets
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from workbench.wb_utils.loop_utils import _run_async

# ─── Configuration ──────────────────────────────────────────────────────

SERVER_PORT = 8791
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
WS_URL_BASE = f"ws://127.0.0.1:{SERVER_PORT}"
APP_MODULE = "workbench.api.server_app:app"
PROJECT_ROOT = Path(__file__).resolve().parents[2]

console = Console()


# ─── Client Workbench ───────────────────────────────────────────────────

class WorkbenchClient:
    """Client pour Workbench — vrai HTTP + vrai WebSocket."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.http = httpx.Client(timeout=60.0, follow_redirects=True)
        self.jobs: Dict[str, Dict] = {}
        self.ws: Optional[Any] = None
        self.current_job_id: Optional[str] = None

    def close(self):
        self.http.close()

    # ─── HTTP ────────────────────────────────────────────────────────────

    def get_config(self) -> Dict:
        r = self.http.get(f"{self.base_url}/config")
        r.raise_for_status()
        return r.json()

    def update_config(self, **kwargs) -> bool:
        data = {k: v for k, v in kwargs.items() if v is not None}
        r = self.http.post(f"{self.base_url}/config", json=data)
        r.raise_for_status()
        return r.json().get("success", False)

    def get_catalog(self) -> Dict:
        r = self.http.get(f"{self.base_url}/catalog")
        r.raise_for_status()
        return r.json()
    
    def create_job(self, spec_id: str, user_input: Dict, timeout: float = 60,
                   upload_paths: Optional[list[str]] = None) -> Dict:
        """
        FIX (multipart) : /job/create est passe en multipart/form-data
        cote serveur pour supporter l'upload de fichiers vers le workdir
        (voir specs/uploads.py, UploadRef). Le champ "data" porte le meme
        JSON qu'avant ; "files" porte les fichiers uploades, DANS L'ORDRE
        attendu par les champs UploadRef du modele d'input de la spec.
        """
        payload = {"id": spec_id, "user_input": user_input, "timeout": timeout}
        files = []
        opened = []
        try:
            for p in (upload_paths or []):
                f = open(p, "rb")
                opened.append(f)
                files.append(("files", (Path(p).name, f, "application/octet-stream")))
            r = self.http.post(
                f"{self.base_url}/job/create",
                data={"data": json.dumps(payload)},
                files=files,  # meme vide, force l'encodage multipart/form-data
            )
        finally:
            for f in opened:
                f.close()
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code} : {r.text}")
        return r.json()
    

    def get_job_status(self, job_id: str) -> Dict:
        r = self.http.get(f"{self.base_url}/job/status", params={"job_id": job_id})
        r.raise_for_status()
        return r.json()

    def stop_job(self, job_id: str) -> bool:
        r = self.http.get(f"{self.base_url}/job/stop", params={"job_id": job_id})
        r.raise_for_status()
        return r.json().get("success", False)

    def download_file(self, workdir: str, path: str) -> bytes:
        r = self.http.get(f"{self.base_url}/download", params={"workdir": workdir, "path": path})
        r.raise_for_status()
        return r.content

    # ─── WebSocket ───────────────────────────────────────────────────────

    async def connect_ws(self, job_id: str):
        ws_url = f"{WS_URL_BASE}/job/ws/logs?job_id={job_id}"
        self.current_job_id = job_id
        self.ws = await websockets.connect(ws_url)
        console.print(f"[green]✅ Connecté aux logs du job {job_id}[/green]")
        return self.ws

    async def listen_logs(self, callback: Optional[Callable] = None, max_seconds: float | None = None):
        """Écoute les logs en temps réel et les affiche."""
        if not self.ws:
            return
        start = time.time()
        try:
            async for message in self.ws:
                data = json.loads(message)
                if callback:
                    await callback(data)
                else:
                    self.display_log(data)

                if data.get("type") == "job_end":
                    break
                if max_seconds is not None and time.time() - start > max_seconds:
                    console.print("[dim]⏹ Arrêt du suivi (timeout atteint)[/dim]")
                    break

        except websockets.exceptions.ConnectionClosed:
            console.print("[dim]— Connexion WebSocket fermée par le serveur —[/dim]")
        except Exception as e:
            console.print(f"[red]❌ Erreur WebSocket: {e!r}[/red]")
        finally:
            self.current_job_id = None

    def display_log(self, data: Dict):
        """Affiche un message de log. Les crochets du texte sont échappés
        pour ne pas être interprétés comme du markup Rich."""
        msg_type = data.get("type", "unknown")
        timestamp = data.get("timestamp", "")

        ts_str = ""
        if timestamp:
            try:
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                ts_str = ts.strftime("%H:%M:%S")
            except Exception:
                ts_str = timestamp[:8]

        if msg_type == "replay_start":
            console.print(f"[cyan]🔄 Replay de {data.get('count', 0)} message(s)...[/cyan]")

        elif msg_type == "replay_end":
            console.print("[cyan]✅ Replay terminé[/cyan]")

        elif msg_type == "run_log":
            stream = data.get("stream", "")
            text = data.get("text", "")

            if stream == "stdout":
                color, prefix = "white", "📤"
            elif stream == "stderr":
                color, prefix = "yellow", "📥"
            else:
                color, prefix = "dim", " "

            safe_text = text.replace("[", "\\[").replace("]", "\\]").rstrip("\n")

            prefix_str = f"[dim]{ts_str}[/dim] " if ts_str else ""
            console.print(f"{prefix_str}{prefix} [{color}]{safe_text}[/]")

        elif msg_type == "job_result":
            console.print("\n[green]✅ Résultat du job reçu[/green]")
            result = data.get("result", {})
            print(result)
            if self.current_job_id and self.current_job_id in self.jobs:
                job = self.jobs[self.current_job_id]
                known_ids = {f.get("id") for f in job.get("output_files", [])}
                if isinstance(result, dict) and "returncode" not in result:
                    for step_id, filename in result.items():
                        if step_id in known_ids and isinstance(filename, str):
                            for out in job.get("output_files", []):
                                if out.get("id") == step_id:
                                    out["file"] = filename
                                    break
                                
                elif all(c in result for c in ("returncode", "stderr", "stdout")):
                    filename = result["output_filename"]
                    for out in job.get("output_files", []):
                        out["file"] = filename
                        break
                    
            if isinstance(result, dict):
                if "returncode" in result:
                    table = Table(title="Résultat d'exécution", box=box.ROUNDED)
                    table.add_column("Champ", style="cyan")
                    table.add_column("Valeur", style="white")
                    for k, v in result.items():
                        if k in ("stdout", "stderr") and isinstance(v, str) and len(v) > 200:
                            v = v[:200] + "..."
                        table.add_row(k, str(v).replace("[", "\\[").replace("]", "\\]"))
                    console.print(table)
                else:
                    console.print_json(json.dumps(result, default=str, indent=2))
            else:
                console.print(str(result))

        elif msg_type == "job_end":
            console.print("[yellow]🏁 Fin du job[/yellow]")

        elif msg_type == "info":
            console.print(f"[cyan]ℹ️ {data.get('message', '')}[/cyan]")

        else:
            console.print(f"[dim]{json.dumps(data, default=str)}[/dim]")


# ─── Interface Interactive ─────────────────────────────────────────────

class InteractiveTester:
    def __init__(self):
        self.client = WorkbenchClient()
        self.server_process: Optional[subprocess.Popen] = None
        self.running = True

    def print_header(self):
        header = Panel(
            "[bold blue]🛠️  Workbench — Test interactif (live)[/bold blue]\n"
            "[dim]Vrai serveur uvicorn, vrai catalogue, vrais binaires (ls, grep, ffmpeg)[/dim]\n\n"
            f"[dim]📡 Serveur: {BASE_URL}[/dim]",
            border_style="blue",
            title="Workbench",
        )
        console.print(header)

    def print_menu(self):
        table = Table(title="Menu Principal", box=box.ROUNDED)
        table.add_column("Option", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_row("1", "📋 Voir le catalogue des specs")
        table.add_row("2", "🚀 Créer un job (ActionSpec ou Pipeline)")
        table.add_row("3", "📊 Voir le statut des jobs")
        table.add_row("4", "📡 Suivre les logs d'un job (WebSocket)")
        table.add_row("5", "⏹️  Arrêter un job")
        table.add_row("6", "📥 Télécharger un fichier")
        table.add_row("7", "⚙️  Configuration")
        table.add_row("8", "🔬 Tester un CommandEngine directement")
        table.add_row("9", "🔀 Tester un Pipeline directement")
        table.add_row("10", "🔄 Lancer un test complet (job + WS + download)")
        table.add_row("11", "🧹 Nettoyer les jobs (en mémoire client)")
        table.add_row("0", "❌ Quitter")
        console.print(table)

    def show_catalog(self):
        console.print("\n[bold]📋 Catalogue des specs[/bold]\n")
        try:
            catalog = self.client.get_catalog()
            table = Table(box=box.ROUNDED)
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Label", style="white")
            table.add_column("Type", style="green")
            table.add_column("Détails", style="dim")
            for spec_id, spec in catalog.items():
                if spec.get("type") == "pipeline":
                    tools = ", ".join(s.get("tool", "?") for s in spec.get("steps", []))
                    details = f"steps: {tools}"
                else:
                    details = f"tool: {spec.get('tool', 'unknown')}"
                table.add_row(spec_id, spec.get("label", spec_id), spec.get("type", "unknown"), details)
            console.print(table)
        except Exception as e:
            console.print(f"[red]❌ Erreur: {e!r}[/red]")

    def _prompt_user_input(self, spec_id: str) -> Dict:
        user_input = {}
        if spec_id == "list_directory":
            console.print("\n[dim]Paramètres pour ls:[/dim]")
            user_input["show_all"] = Confirm.ask("Afficher les fichiers cachés (-a) ?", default=True)
            user_input["long_format"] = Confirm.ask("Format long (-l) ?", default=True)
        elif spec_id == "filter_pattern":
            console.print("\n[dim]Paramètres pour grep:[/dim]")
            user_input["pattern"] = Prompt.ask("Motif à chercher", default="total")
            user_input["input_file"] = Prompt.ask("Fichier d'entrée (relatif au workdir du job)", default="")
        elif spec_id == "generate_test_video":
            console.print("\n[dim]Paramètres pour ffmpeg (génération):[/dim]")
            user_input["duration_s"] = float(Prompt.ask("Durée (secondes)", default="1.0"))
            user_input["size"] = Prompt.ask("Taille (ex: 64x64)", default="64x64")
        elif spec_id == "convert_to_gif":
            console.print("\n[dim]Paramètres pour ffmpeg (conversion en GIF):[/dim]")
            user_input["input_file"] = Prompt.ask("Fichier vidéo d'entrée (relatif au workdir)", default="generated.mp4")
            user_input["width"] = int(Prompt.ask("Largeur", default="64"))
            user_input["duration_s"] = float(Prompt.ask("Durée", default="1.0"))
        elif spec_id == "ls_then_grep_pipeline":
            console.print("\n[dim]Paramètres pour le pipeline ls -> grep:[/dim]")
            user_input["keyword"] = Prompt.ask("Mot-clé à rechercher dans le listing", default="total")
        else:
            input_str = Prompt.ask("Paramètres (JSON)", default="{}")
            try:
                user_input = json.loads(input_str)
            except Exception:
                console.print("[yellow]⚠️ JSON invalide, utilisation de {}[/yellow]")
        return user_input

    async def follow_logs(self, job_id: str, max_seconds: float | None = None):
        console.print(f"\n[bold]📡 Suivi des logs du job {job_id}[/bold]")
        console.print("[dim]Le suivi s'arrête automatiquement à la fin du job[/dim]\n")
        try:
            await self.client.connect_ws(job_id)
            await self.client.listen_logs(max_seconds=max_seconds)
        except Exception as e:
            console.print(f"[red]❌ Erreur: {e!r}[/red]")

    def show_job_status(self):
        if not self.client.jobs:
            console.print("[yellow]Aucun job en mémoire[/yellow]")
            return
        console.print("\n[bold]📊 Jobs[/bold]\n")
        table = Table(box=box.ROUNDED)
        table.add_column("Job ID", style="cyan")
        table.add_column("Spec", style="white")
        table.add_column("Workdir", style="dim")
        table.add_column("Statut", style="green")
        for job_id, job in list(self.client.jobs.items())[-10:]:
            try:
                status = self.client.get_job_status(job_id)
                status_str = status.get("status", "unknown")
                color = {"finished": "green", "running": "yellow"}.get(status_str, "red")
                spec = job.get("spec", {})
                spec_id = spec.get("id", "unknown") if isinstance(spec, dict) else str(spec)
                table.add_row(
                    job_id[:24] + "…" if len(job_id) > 24 else job_id,
                    spec_id,
                    (job.get("workdir", "") or "")[:30] + "…",
                    f"[{color}]{status_str}[/{color}]",
                )
            except Exception:
                pass
        console.print(table)

        job_id = Prompt.ask("\nEntrez un Job ID pour voir les détails (ou Enter)", default="")
        if job_id and job_id in self.client.jobs:
            console.print_json(json.dumps(self.client.jobs[job_id], default=str, indent=2))

    def download_file_interactive(self):
        if not self.client.jobs:
            console.print("[yellow]Aucun job en mémoire[/yellow]")
            return
        console.print("\n[bold]📥 Téléchargement d'un fichier[/bold]\n")

        table = Table(title="Fichiers disponibles", box=box.ROUNDED)
        table.add_column("Job ID", style="cyan")
        table.add_column("Fichiers", style="white")
        candidates = []
        for job_id, job in list(self.client.jobs.items())[-10:]:
            files = [f.get("file") for f in job.get("output_files", []) if f.get("file")]
            if files:
                candidates.append(job_id)
                table.add_row(job_id[:24] + "…" if len(job_id) > 24 else job_id, "\n".join(files))
        console.print(table)

        if not candidates:
            console.print("[yellow]Aucun fichier de sortie connu pour l'instant[/yellow]")
            return

        job_id = Prompt.ask("Job ID")
        if job_id not in self.client.jobs:
            console.print("[red]Job non trouvé[/red]")
            return
        job = self.client.jobs[job_id]
        files = [f.get("file") for f in job.get("output_files", []) if f.get("file")]
        if not files:
            console.print("[yellow]Aucun fichier disponible[/yellow]")
            return

        for i, file in enumerate(files, 1):
            console.print(f"  {i}. {file}")
        choice = Prompt.ask("Choisissez un fichier", choices=[str(i) for i in range(1, len(files) + 1)])
        file_path = files[int(choice) - 1]

        try:
            content = self.client.download_file(job["workdir"], file_path)
            if not content:
                console.print("[red]❌ Fichier vide ou inexistant[/red]")
                return
            console.print(f"[green]✅ Téléchargé: {len(content)} octets[/green]")
            if Confirm.ask("Afficher un aperçu ?", default=False):
                if file_path.endswith((".txt", ".log", ".json", ".csv")):
                    try:
                        text = content.decode("utf-8")
                        lines = text.split("\n")
                        preview_text = "\n".join(lines[:20]).replace("[", "\\[").replace("]", "\\]")
                        if len(lines) > 20:
                            preview_text += f"\n[dim]... et {len(lines) - 20} lignes de plus[/dim]"
                        console.print(Panel(preview_text, title=f"Aperçu de {file_path}", border_style="green"))
                    except UnicodeDecodeError:
                        console.print("[dim]Fichier binaire (pas d'aperçu texte)[/dim]")
                else:
                    hex_preview = content[:64].hex()
                    console.print(Panel(
                        f"[dim]{hex_preview}{'…' if len(content) > 64 else ''}[/dim]",
                        title=f"Aperçu hex de {file_path}", border_style="green"
                    ))
        except Exception as e:
            console.print(f"[red]❌ Erreur: {e!r}[/red]")

    def test_command_engine(self):
        console.print("\n[bold]🔬 Test CommandEngine (direct, hors serveur)[/bold]\n")
        try:
            from workbench.core.subprocess.engine import CommandEngine
            from workbench.core.subprocess.version_checker import Config as BinConfig
            from workbench.core.subprocess.wb_subprocess_types import (
                BoolArg, PathArg, IntArg, FloatArg, EnumArg, PatternArg,
            )

            binary = Prompt.ask("Binaire", default="ls")
            cmd = Prompt.ask("Commande de version", default="--version")
            marker = Prompt.ask("Marqueur attendu dans la sortie", default="coreutils" if binary == "ls" else binary)
            config = BinConfig(cmd=cmd, marker=marker, tool_name=binary)
            workdir = tempfile.mkdtemp()
            console.print(f"[dim]Workdir: {workdir}[/dim]")

            engine = CommandEngine(binary=binary, binary_config=config, workdir=workdir, min_version=None, check_version=True)
            console.print(f"[green]✅ Engine créé: {engine.binary_path}[/green]")
            console.print(f"Version détectée: {engine.version}")

            console.print("\n[dim]Construction des arguments (tapez 'done' pour arrêter):[/dim]")
            args = []
            while True:
                arg_type = Prompt.ask(
                    "Type d'argument", choices=["bool", "path", "int", "float", "enum", "pattern", "done"], default="done"
                )
                if arg_type == "done":
                    break
                flag = Prompt.ask("Flag (ex: -a, ou vide si positionnel)", default="")
                if arg_type == "bool":
                    args.append(BoolArg(flag=flag, value=Confirm.ask("Valeur", default=True)))
                elif arg_type == "path":
                    value = Prompt.ask("Chemin (relatif au workdir)")
                    must_exist = Confirm.ask("Doit exister ?", default=False)
                    args.append(PathArg(flag=flag, value=value, must_exist=must_exist))
                elif arg_type == "int":
                    args.append(IntArg(flag=flag, value=int(Prompt.ask("Valeur"))))
                elif arg_type == "float":
                    args.append(FloatArg(flag=flag, value=float(Prompt.ask("Valeur"))))
                elif arg_type == "enum":
                    value = Prompt.ask("Valeur")
                    enum_values = [v.strip() for v in Prompt.ask("Valeurs autorisées (séparées par ,)").split(",")]
                    args.append(EnumArg(flag=flag, value=value.strip(), enum_values=enum_values))
                elif arg_type == "pattern":
                    args.append(PatternArg(flag=flag, value=Prompt.ask("Motif")))

            cmd_str = engine.build_command(args)
            console.print("\n[dim]Commande construite:[/dim]")
            console.print(f"  [cyan]{' '.join(cmd_str)}[/cyan]")

            if Confirm.ask("Exécuter ?", default=True):
                console.print("\n[dim]Exécution en cours...[/dim]")

                async def run():
                    return await engine.execute_async(
                        args=args, timeout=30,
                        on_output=lambda x: console.print(f"[dim]{x['stream']}: {x['text'].rstrip()}[/dim]"),
                    )

                result = _run_async(run)
                console.print("\n[bold]Résultat:[/bold]")
                console.print(f"  Returncode: {result.returncode}")
                console.print(f"  OK (0 ou 1): {result.ok}   Success (0): {result.success}")
                if result.stdout:
                    console.print(f"  Stdout: {result.stdout[:200]!r}")
                if result.stderr:
                    console.print(f"  Stderr: {result.stderr[:200]!r}")
        except Exception as e:
            console.print(f"[red]❌ Erreur: {e!r}[/red]")
            import traceback
            traceback.print_exc()

    def test_pipeline(self):
        console.print("\n[bold]🔀 Test Pipeline (direct, hors serveur) — ls -> grep[/bold]\n")
        try:
            from workbench.core.subprocess.engine import CommandEngine
            from workbench.core.subprocess.pipeline import Pipeline, PipelineStep
            from workbench.core.subprocess.version_checker import Config as BinConfig
            from workbench.core.subprocess.wb_subprocess_types import PathArg, BoolArg, PatternArg as PatternArgLike

            workdir = tempfile.mkdtemp()
            console.print(f"[dim]Workdir: {workdir}[/dim]")

            ls_engine = CommandEngine("ls", BinConfig(cmd="--version", marker="coreutils", tool_name="ls"), workdir)
            console.print(f"  [green]✅ ls: {ls_engine.binary_path}[/green]")
            grep_engine = CommandEngine("grep", BinConfig(cmd="--version", marker="grep", tool_name="grep"), workdir)
            console.print(f"  [green]✅ grep: {grep_engine.binary_path}[/green]")

            keyword = Prompt.ask("Mot-clé à chercher avec grep", default="total")

            pipeline = Pipeline([
                PipelineStep(
                    id="list_files", engine=ls_engine,
                    build_args=lambda outputs: [BoolArg(flag="-a", value=True), BoolArg(flag="-l", value=True)],
                    output_filename="ls_output.txt", capture_stdout=True,
                ),
                PipelineStep(
                    id="filter_output", engine=grep_engine,
                    build_args=lambda outputs: [
                        PatternArgLike(value=keyword),
                        PathArg(value=outputs["_previous"], must_exist=True),
                    ],
                    output_filename="filtered_output.txt", capture_stdout=True,
                ),
            ])
            console.print("[green]✅ Pipeline construit[/green]")
            for step in pipeline.steps:
                console.print(f"  - {step.id}: {step.engine.binary_path}")

            if Confirm.ask("Exécuter le pipeline ?", default=True):
                console.print("\n[dim]Exécution en cours...[/dim]")

                async def run():
                    return await pipeline.run(
                        initial_inputs={},
                        on_output=lambda x: console.print(f"[dim][{x.get('step', '?')}] {x.get('text', '').rstrip()}[/dim]"),
                    )

                result = _run_async(run)
                console.print("\n[bold]Résultat (dict outputs):[/bold]")
                console.print_json(json.dumps(result, default=str, indent=2))
                for step_id, filename in result.items():
                    if filename and step_id != "_previous" and isinstance(filename, str):
                        filepath = Path(workdir) / filename
                        if filepath.exists():
                            content = filepath.read_text().replace("[", "\\[").replace("]", "\\]")
                            console.print(Panel(
                                content[:500] + ("…" if len(content) > 500 else ""),
                                title=f"Contenu de {filename}", border_style="green",
                            ))
        except Exception as e:
            console.print(f"[red]❌ Erreur: {e!r}[/red]")
            import traceback
            traceback.print_exc()

    async def run_full_test(self, auto_spec_id: str | None = None, auto_user_input: dict | None = None):
        console.print("\n[bold]🔄 Test complet (création + suivi WS + téléchargement)[/bold]\n")
        try:
            self.client.get_config()
            console.print("[green]✅ Serveur accessible[/green]")
        except Exception:
            console.print("[red]❌ Serveur inaccessible[/red]")
            return

        catalog = self.client.get_catalog()
        spec_ids = list(catalog.keys())

        if auto_spec_id:
            spec_id = auto_spec_id
            user_input = auto_user_input or {}
        else:
            console.print("[bold]1. Choisir une spec[/bold]")
            for i, s in enumerate(spec_ids, 1):
                console.print(f"  {i}. {s}")
            choice = Prompt.ask("Votre choix", choices=[str(i) for i in range(1, len(spec_ids) + 1)])
            spec_id = spec_ids[int(choice) - 1]
            user_input = self._prompt_user_input(spec_id)

        console.print(f"\n[bold]2. Création du job « {spec_id} »[/bold]")
        try:
            result = self.client.create_job(spec_id, user_input, 60)
        except Exception as e:
            console.print(f"[red]❌ Erreur: {e!r}[/red]")
            return
        job_id, workdir = result["job_id"], result["workdir"]
        self.client.jobs[job_id] = result
        console.print(f"[green]✅ Job créé: {job_id}[/green]  (workdir: {workdir})")

        console.print("\n[bold]3. Suivi des logs en direct (WebSocket, max 15s)[/bold]")
        await self.follow_logs(job_id, max_seconds=15)

        console.print("\n[bold]4. Téléchargement des fichiers produits[/bold]")
        files = [f.get("file") for f in self.client.jobs[job_id].get("output_files", []) if f.get("file")]
        for file_path in files:
            try:
                content = self.client.download_file(workdir, file_path)
                console.print(f"[green]✅ {file_path}: {len(content)} octets[/green]")
                out_dir = Path.cwd() / "downloads"
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / file_path).write_bytes(content)
                console.print(f"  [dim]Sauvegardé → {out_dir / file_path}[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠️ {file_path}: {e!r}[/yellow]")

        console.print("\n[bold green]✅ Test complet terminé ![/bold green]")

    def show_config(self):
        try:
            config = self.client.get_config()
            console.print("\n[bold]⚙️ Configuration actuelle[/bold]\n")
            table = Table(box=box.ROUNDED)
            table.add_column("Clé", style="cyan")
            table.add_column("Valeur", style="white")
            for key, value in config.items():
                table.add_row(key, str(value))
            console.print(table)
            if Confirm.ask("Modifier la configuration ?", default=False):
                console.print("[dim]Laissez vide pour ne pas modifier ce champ[/dim]")
                updates = {}
                for key, current in config.items():
                    val = Prompt.ask(key, default="")
                    if val:
                        updates[key] = float(val) if "." in val else int(val)
                if updates:
                    self.client.update_config(**updates)
                    console.print("[green]✅ Configuration mise à jour[/green]")
                    console.print(self.client.get_config())
        except Exception as e:
            console.print(f"[red]❌ Erreur: {e!r}[/red]")

    # ─── Gestion du serveur (vrai sous-processus uvicorn) ────────────────

    def start_server(self) -> bool:
        if self.server_process:
            console.print("[yellow]Serveur déjà en cours d'exécution[/yellow]")
            return True
        console.print("[bold]🚀 Démarrage du serveur (uvicorn, sous-processus réel)...[/bold]")

        self.server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", APP_MODULE, "--host", "127.0.0.1", "--port", str(SERVER_PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),  
            text=True,
        )
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
            task = progress.add_task("Attente du serveur...", total=None)
            for _ in range(40):
                time.sleep(0.25)
                if self.server_process.poll() is not None:
                    progress.update(task, completed=True)
                    out = self.server_process.stdout.read() if self.server_process.stdout else ""
                    console.print("[red]❌ Le serveur s'est arrêté immédiatement :[/red]")
                    console.print(out)
                    self.server_process = None
                    return False
                try:
                    self.client.get_config()
                    progress.update(task, completed=True)
                    console.print(f"[green]✅ Serveur démarré (pid {self.server_process.pid}, port {SERVER_PORT})[/green]")
                    return True
                except Exception:
                    pass
            progress.update(task, completed=True)
        console.print("[red]❌ Le serveur ne répond pas après 10s[/red]")
        self.stop_server()
        return False

    def stop_server(self):
        if not self.server_process:
            return
        self.server_process.send_signal(signal.SIGINT)
        try:
            self.server_process.wait(timeout=5)
            console.print("[green]✅ Serveur arrêté proprement[/green]")
        except subprocess.TimeoutExpired:
            self.server_process.kill()
            console.print("[yellow]⚠️ Serveur tué (force)[/yellow]")
        self.server_process = None

    # ─── Boucles principales ──────────────────────────────────────────────

    async def run(self):
        self.print_header()
        if not self.start_server():
            return

        while self.running:
            try:
                self.print_menu()
                choice = Prompt.ask(
                    "Votre choix",
                    choices=[str(i) for i in range(12)],
                )

                if choice == "0":
                    self.running = False
                    console.print("[bold red]👋 Au revoir ![/bold red]")
                elif choice == "1":
                    self.show_catalog()
                elif choice == "2":
                    job_id = self._create_job_and_get_id()
                    if job_id and Confirm.ask("\nSuivre les logs en temps réel ?", default=True):
                        await self.follow_logs(job_id)
                elif choice == "3":
                    self.show_job_status()
                elif choice == "4":
                    job_id = Prompt.ask("Job ID")
                    if job_id:
                        await self.follow_logs(job_id)
                elif choice == "5":
                    job_id = Prompt.ask("Job ID")
                    if job_id:
                        ok = self.client.stop_job(job_id)
                        console.print("[green]✅ Job arrêté[/green]" if ok else "[red]❌ Échec de l'arrêt[/red]")
                elif choice == "6":
                    self.download_file_interactive()
                elif choice == "7":
                    self.show_config()
                elif choice == "8":
                    self.test_command_engine()
                elif choice == "9":
                    self.test_pipeline()
                elif choice == "10":
                    await self.run_full_test()
                elif choice == "11":
                    self.client.jobs.clear()
                    console.print("[green]✅ Jobs nettoyés (côté client)[/green]")

            except KeyboardInterrupt:
                self.running = False
                console.print("\n[bold red]👋 Arrêt demandé[/bold red]")
            except Exception as e:
                console.print(f"[red]❌ Erreur: {e!r}[/red]")

        self.stop_server()
        self.client.close()

    def _create_job_and_get_id(self) -> str | None:
        """Variante synchrone de create_job_interactive qui renvoie le job_id créé."""
        console.print("\n[bold]🚀 Création d'un job[/bold]\n")
        try:
            catalog = self.client.get_catalog()
            spec_ids = list(catalog.keys())
            console.print("Specs disponibles:")
            for i, spec_id in enumerate(spec_ids, 1):
                console.print(f"  {i}. [cyan]{spec_id}[/cyan] ([dim]{catalog[spec_id].get('label', '')}[/dim])")
            choice = Prompt.ask("Choisissez une spec", choices=[str(i) for i in range(1, len(spec_ids) + 1)])
            spec_id = spec_ids[int(choice) - 1]
            user_input = self._prompt_user_input(spec_id)
            timeout = float(Prompt.ask("Timeout (secondes)", default="30.0"))
            result = self.client.create_job(spec_id, user_input, timeout)
            job_id = result["job_id"]
            self.client.jobs[job_id] = result
            console.print(f"\n[green]✅ Job créé: {job_id}[/green]")
            for f in result.get("output_files", []):
                console.print(f"    - {f.get('file', '?')} (id: {f.get('id', '?')})")
            return job_id
        except Exception as e:
            console.print(f"[red]❌ Erreur: {e!r}[/red]")
            return None

    async def run_auto(self):
        """Mode non-interactif : démarre le serveur, exercice le catalogue
        complet (ls, ffmpeg génération, ffmpeg conversion, pipeline), sans
        aucune saisie utilisateur. Utile en CI ou pour une vérification
        rapide de bout en bout."""
        self.print_header()
        if not self.start_server():
            raise SystemExit(1)

        scenarios = [
            ("list_directory", {"show_all": True, "long_format": True}),
            ("generate_test_video", {"duration_s": 1.0, "size": "64x64"}),
            ("ls_then_grep_pipeline", {"keyword": "total"}),
        ]
        try:
            self.show_catalog()
            for spec_id, user_input in scenarios:
                await self.run_full_test(auto_spec_id=spec_id, auto_user_input=user_input)
            self.show_job_status()
            console.print("\n[bold green]🎉 Mode automatique terminé sans erreur.[/bold green]")
        finally:
            self.stop_server()
            self.client.close()


# ─── Entry Point ──────────────────────────────────────────────────────

def main():
    tester = InteractiveTester()

    def _sigint(sig, frame):
        console.print("\n[yellow]⚠️ Interruption, arrêt du serveur...[/yellow]")
        tester.stop_server()
        sys.exit(0)

    signal.signal(signal.SIGINT, _sigint)

    auto = "--auto" in sys.argv
    try:
        if auto:
            asyncio.run(tester.run_auto())
        else:
            asyncio.run(tester.run())
    except KeyboardInterrupt:
        console.print("\n[bold red]👋 Au revoir ![/bold red]")
        tester.stop_server()


if __name__ == "__main__":
    main()