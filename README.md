# 🛠️ Workbench

> Framework Python pour exposer des outils en ligne de commande via une API typée, sandboxée et pilotable depuis une interface graphique (web ou desktop).

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063.svg)](https://docs.pydantic.dev/)

---

## 📖 Sommaire

1. [Le problème](#-le-problème)
2. [Ce que fait Workbench](#-ce-que-fait-workbench)
3. [Ce que Workbench n'est pas](#-ce-que-workbench-nest-pas)
4. [Architecture](#-architecture)
5. [Modèle de sécurité](#-modèle-de-sécurité)
6. [Structure du dépôt (monorepo)](#-structure-du-dépôt-monorepo)
7. [Installation](#-installation)
8. [Guide de démarrage rapide](#-guide-de-démarrage-rapide)
9. [API REST & WebSocket](#-api-rest--websocket)
10. [Introspection UI](#-introspection-ui)
11. [Mode manuel (`RawEntry`)](#-mode-manuel-rawentry)
12. [Produits construits sur Workbench](#-produits-construits-sur-workbench)
13. [Distribution Desktop (Tauri)](#-distribution-desktop-tauri)
14. [Licence](#-licence)

---

## 🎯 Le problème

Beaucoup d'outils en ligne de commande sont solides, éprouvés, et font très bien leur travail. Le problème n'est pas l'outil — c'est ce qui se passe **quand on veut le rendre accessible via une interface graphique ou une API web** :

- Leur syntaxe (flags, options combinables, ordre des arguments) est souvent intimidante pour qui n'a pas l'habitude du terminal — un outil puissant reste inutilisé s'il fait peur avant même d'être essayé.
- Construire une commande à partir d'une entrée utilisateur, à la main, ouvre la porte à l'injection d'arguments si on n'y prête pas une attention constante.
- Chaque nouvel outil qu'on veut exposer redemande de refaire tout ce travail de validation, de sandboxing, et de gestion des fichiers temporaires.
- Streamer la sortie d'un process en direct vers un frontend, gérer son annulation, et nettoyer proprement après coup, c'est de la plomberie qu'on réécrit à chaque fois.

## ⚙️ Ce que fait Workbench

Workbench part du principe que la puissance d'un outil CLI ne devrait pas être réservée à qui maîtrise déjà sa syntaxe. Il transforme les actions de ces outils en **interfaces graphiques conviviales** — formulaires clairs, options guidées, logs lisibles en direct — pour les rendre accessibles à des utilisateurs qui n'ont jamais ouvert un terminal.

Techniquement, c'est une **couche d'orchestration générique**, indépendante de tout outil en particulier. Elle fournit :

- Un système d'arguments typés (`PathArg`, `IntArg`, `FloatArg`, `BoolArg`, `EnumArg`, `PatternArg`, `MultiPathArg`) — pas de string libre concaténée dans une commande.
- Un moteur d'exécution qui lance les process directement (`shell=False`), dans un dossier de travail isolé par job.
- Un système de pipeline pour chaîner plusieurs outils sans passer par des pipes Unix, avec des sorties intermédiaires référencées explicitement.
- Un streaming WebSocket des logs, découplé du cycle de vie du job (une déconnexion réseau n'interrompt pas l'exécution en cours).
- Une introspection automatique des schémas Pydantic vers des formulaires exploitables côté frontend.

Chaque produit construit sur Workbench (le premier étant Mediakit) déclare ses propres outils et actions ; le socle (validation, sandboxing, exécution, streaming, nettoyage) est partagé et ne se réécrit pas à chaque fois.

## 🚫 Ce que Workbench n'est pas

- Ce n'est **pas** une critique des outils qu'il expose. Les binaires wrappés sont choisis précisément parce qu'ils sont robustes et éprouvés — Workbench ne cherche pas à les remplacer ni à corriger de prétendus défauts.
- Ce n'est **pas** un wrapper universel magique : chaque outil exposé nécessite de déclarer explicitement ses actions (`ActionSpec`) et leurs arguments valides. La sécurité vient de cette liste blanche explicite, pas d'une détection automatique.

---

## 🏗️ Architecture

```text
+-------------------------------------------------------------------------+
|                  INTERFACE (Web / Desktop)                              |
+-------------------------------------------------------------------------+
                                    │  ▲
              HTTP (Multipart/JSON) │  │  WebSocket (stdout / stderr)
                                    ▼  │
+-------------------------------------------------------------------------+
|                  SERVEUR D'APPLICATION (FastAPI)                        |
+-------------------------------------------------------------------------+
                                    │
                                    ▼
+-------------------------------------------------------------------------+
|                  ORCHESTRATEUR CENTRAL (MainEngine)                     |
|    Concurrence · Timeouts/Annulation · Buffer+Replay · Nettoyage        |
+-------------------------------------------------------------------------+
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
             ActionSpec (unitaire)          PipelineSpec (chaîné)
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
+-------------------------------------------------------------------------+
|                  MOTEUR D'EXÉCUTION (CommandEngine)                     |
|    Validation binaire/version · Sandboxing chemins · Args typés         |
+-------------------------------------------------------------------------+
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              [ Binaire A ]    [ Binaire B ]    [ Binaire C ]
```

---

## 🔒 Modèle de sécurité

| Risque | Protection |
| :--- | :--- |
| Injection de commande shell | Exécution directe (`shell=False`), aucune concaténation de chaîne |
| Injection d'argument | Aucun positionnel ne peut commencer par `-` ; chaque type est borné et validé par Pydantic |
| Path traversal | Résolution stricte des chemins à l'intérieur du `workdir` du job |
| Protocoles CLI détournés | Caractère `:` interdit dans les chemins |
| Binaire inattendu ou corrompu | Vérification de version + marqueur textuel avant exécution |
| Texte libre non contraint | `PatternArg` : longueur maximale, caractères de contrôle interdits |
| Ressources infinies | Timeouts et quota de jobs concurrents |

La responsabilité de composer des `ActionSpec` sûres reste à qui les déclare : Workbench fournit les briques de validation, pas une garantie automatique sur n'importe quelle commande imaginable.

---

## 📁 Structure du dépôt (monorepo)

```text
workbench/                      ← racine du repo git
├── src/
│   └── workbench/
│       ├── api/                 ← routeur FastAPI générique, réutilisé par tous les produits
│       ├── core/                ← orchestrateur + moteur d'exécution
│       ├── specs/                ← ActionSpec, PipelineSpec, registry, raw engine
│       ├── wb_utils/            ← utilitaires partagés (buffers, cleanup, config...)
│       └── products/
│           └── mediakit/         ← premier produit construit sur Workbench
│               ├── api/
│               ├── specs/
│               └── frontend/     ← React + Vite, buildé et servi par FastAPI
├── .github/workflows/
├── .gitignore
├── pyproject.toml
└── README.md
```

Chaque produit importe directement les modules génériques de `src/workbench/{api,core,wb_utils}` : ce couplage par import direct est la raison du choix du monorepo plutôt que des dépôts séparés par produit.

---

## 📦 Installation

```bash
git clone https://github.com/<votre-compte>/workbench.git
cd workbench
pip install -e .
```

**Dépendances principales :** Python 3.11+, `pydantic >= 2.0`, `fastapi >= 0.100`, `uvicorn[standard]`, `python-magic`.

---

## 🚀 Guide de démarrage rapide

### 1. Déclarer des arguments typés

```python
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, IntArg, EnumArg, PatternArg, MultiPathArg, MultiPathMode
)

input_file = PathArg(flag="-i", value="source.ext", must_exist=True)
level = IntArg(flag="-l", value=5, min_value=0, max_value=10)
mode = EnumArg(flag="-m", value="fast", enum_values=["fast", "balanced", "quality"])

# Plusieurs entrées, flag répété une fois par fichier
multi_inputs = MultiPathArg(flag="-i", values=["a.ext", "b.ext"], mode=MultiPathMode.REPEAT_FLAG)

# Motif contrôlé (ex: pour un outil type grep/jq)
pattern = PatternArg(flag="-e", value="ERROR|WARN")
```

### 2. Créer une `ActionSpec`

```python
from pydantic import BaseModel, Field
from workbench.specs.specs import ActionSpec
from workbench.core.subprocess.version_checker import Config as BinVersionConfig

class MyActionInput(BaseModel):
    input_file: str
    level: int = Field(default=5, ge=0, le=10)

binary_config = BinVersionConfig(cmd="--version", marker="mytool", tool_name="mytool")

my_action_spec = ActionSpec[MyActionInput](
    id="my_action",
    label="Mon action",
    tool="mytool",
    binary_config=binary_config,
    input_cls=MyActionInput,
    min_version=(1, 0),
    output_filename_template="output.ext",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        IntArg(flag="-l", value=u.level, min_value=0, max_value=10),
        PathArg(value="output.ext"),
    ],
)
```

### 3. Exécuter avec `MainEngine`

```python
import asyncio
from workbench.api.config import WbConfig
from workbench.core.orchestrator import MainEngine

async def main():
    config = WbConfig(max_concurrent_job=5, file_ttl=3600)
    engine = MainEngine(config)
    engine.start()

    async def log_handler(payload):
        print(f"[{payload.get('stream', 'stdout')}] {payload.get('text', '').rstrip()}")

    job = engine.create_job(
        spec=my_action_spec,
        job_id=engine.job_id(),
        workdir="/tmp/mon_job_1",
        user_input=MyActionInput(input_file="source.ext", level=7),
        exec_callback=log_handler,
    )

    await job["entry"].task
    print("Résultat :", job["entry"].exec_result)
    await engine.stop()

asyncio.run(main())
```

---

## 🌐 API REST & WebSocket

| Endpoint | Méthode | Description |
| :--- | :--- | :--- |
| `/api/catalog` | GET | Arbre complet des specs et pipelines déclarés |
| `/api/spec/{spec_id}/info` | GET | Schéma d'entrée pour l'UI |
| `/api/job/create` | POST (multipart) | Lance un job (`data` JSON + `files`) |
| `/api/job/advanced/create` | POST (multipart) | Lance un job manuel (`RawEntry`) |
| `/api/job/status?job_id=...` | GET | Statut courant du job |
| `/api/job/stop?job_id=...` | GET | Interrompt un job actif |
| `/api/download?workdir=...&path=...` | GET | Téléchargement sécurisé d'un fichier généré |
| `/api/binary/{tool}/check` | GET | Vérifie présence et version d'un binaire |
| `/api/job/ws/logs?job_id=...` | WebSocket | Stream bidirectionnel des logs |

### Protocole WebSocket

```json
{ "type": "run_log", "stream": "stdout", "text": "..." }
{ "type": "replay_start", "count": 140 }
{ "type": "replay_end" }
{ "type": "job_result", "result": { "returncode": 0, "ok": true } }
{ "type": "job_end" }
```

---

## 🎨 Introspection UI

```python
from workbench.wb_utils.model_parser import model_to_dict

schema = model_to_dict(MyActionInput)
```

Traduit un modèle Pydantic en schéma exploitable directement par un formulaire frontend (type, contraintes, valeur par défaut, description).

---

## 🛠️ Mode manuel (`RawEntry`)

Pour les cas non couverts par une `ActionSpec` déclarée, une commande peut être construite dynamiquement côté frontend et validée côté serveur :

```json
{
  "tool": "mytool",
  "output_filename": "output.ext",
  "timeout": 120,
  "args": [
    { "type": "path", "flag": "-i", "value": "input.ext", "must_exist": true },
    { "type": "pattern", "flag": "-p", "value": "some-pattern" },
    { "type": "enum", "flag": "-m", "value": "fast", "enum_values": ["fast", "quality"] }
  ]
}
```

Le champ `tool` est fixé côté serveur/frontend, jamais laissé libre à l'utilisateur final — la sélection du binaire n'est donc pas un vecteur d'attaque ouvert.

---

## 📦 Produits construits sur Workbench

| Produit | Statut |
| :--- | :--- |
| **Mediakit** | ✅ v1.0.0 — frontend buildé, servi par FastAPI |

---

## 🖥️ Distribution Desktop (Tauri)

Les produits Workbench peuvent être distribués comme applications desktop natives (Windows/macOS/Linux) via Tauri :

1. Le backend Python (packagé en exécutable autonome) est lancé en arrière-plan au démarrage de l'app.
2. La fenêtre Tauri pointe sur l'instance locale du backend.
3. Le build cross-plateforme est automatisé via GitHub Actions (`.github/workflows/`), sans dépendance à une chaîne Rust installée localement pour la distribution.

---

## 📜 Licence

Ce dépôt applique **deux régimes de licence distincts** :

- Le **core Workbench** (`src/workbench/api`, `core`, `specs`, `wb_utils`) est sous licence **[Apache 2.0](LICENSE)** — libre d'utilisation, modification et redistribution, y compris commerciale.
- Les **produits** (`src/workbench/products/*`, dont Mediakit) sont **propriétaires** — voir le fichier `LICENSE` présent dans chaque dossier de produit. Cloner ce dépôt ne donne pas de droit d'utilisation sur ces produits en dehors du core.
