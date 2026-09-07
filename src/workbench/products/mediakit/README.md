# 🎬 Mediakit

> Interface graphique pour FFmpeg, ImageMagick et SoX — construite sur [Workbench](../../../../README.md).

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Built on Workbench](https://img.shields.io/badge/built%20on-Workbench-009688.svg)](../../../../README.md)
[![Statut](https://img.shields.io/badge/statut-v1.0.0-brightgreen.svg)](#)

---

## 📖 Sommaire

1. [Ce que fait Mediakit](#-ce-que-fait-mediakit)
2. [Prérequis](#-prérequis)
3. [Lancer Mediakit](#-lancer-mediakit)
4. [Configuration (variables d'environnement)](#️-configuration-variables-denvironnement)
5. [Builder l'exécutable autonome (PyInstaller)](#-builder-lexécutable-autonome-pyinstaller)
6. [Outils requis sur la machine hôte](#️-outils-requis-sur-la-machine-hôte)
7. [Dépannage](#-dépannage)
8. [Licence](#-licence)

---

## 🎯 Ce que fait Mediakit

Mediakit transforme trois outils CLI puissants — mais peu accessibles sans habitude du terminal — en interface graphique guidée :

- **FFmpeg** : montage, conversion, compression, recadrage vidéo, sous-titrage, GIF...
- **ImageMagick** : retouche, redimensionnement, flou, conversion de format d'image...
- **SoX** : traitement et conversion audio.

Chaque action (couper une vidéo, flouter un visage, exporter un GIF...) est une `ActionSpec` déclarée côté serveur : formulaire typé côté frontend, validation Pydantic, exécution sandboxée — le tout hérité du socle générique de Workbench (voir le [README principal](../../../../README.md) pour le modèle de sécurité).

Mediakit ne réimplémente rien : c'est une couche de spécifications (`specs/ffmpeg`, `specs/imagemagick`, `specs/sox`, `specs/pipelines`) posée sur l'orchestrateur Workbench.

---

## ✅ Prérequis

| Élément | Détail |
| :--- | :--- |
| Python | 3.11+ (uniquement pour l'option A, lancement depuis les sources) |
| FFmpeg, ImageMagick, SoX | Installés sur la machine hôte et accessibles dans le `PATH` (voir [section dédiée](#️-outils-requis-sur-la-machine-hôte)) |
| Navigateur | N'importe lequel — l'interface s'y ouvre automatiquement |

---

## 🚀 Lancer Mediakit

### Option A — Depuis les sources (dev)

```bash
cd src/workbench/products/mediakit/api
python run_api.py
```

Le backend démarre, choisit un port libre automatiquement, et ouvre votre navigateur par défaut sur l'interface. Gardez le terminal ouvert tant que vous utilisez l'app ; fermez-le (ou `Ctrl+C`) pour arrêter le serveur.

### Option B — Exécutable autonome (utilisateur final, pas de Python requis)

1. Téléchargez le binaire correspondant à votre OS depuis la page **Releases** du dépôt.
2. Lancez-le :
   - **Windows / macOS** : double-clic sur le fichier.
   - **Linux** : rendez-le exécutable une première fois si besoin (`chmod +x mediakit-backend`), puis lancez-le depuis un terminal avec `./mediakit-backend`.
3. Votre navigateur s'ouvre automatiquement sur l'interface.
4. Pour fermer l'application, fermez la fenêtre de terminal qui s'est ouverte (ou `Ctrl+C`).

> 💡 FFmpeg, ImageMagick et SoX doivent être installés séparément sur la machine — l'exécutable autonome embarque le backend Python, pas ces binaires externes (voir plus bas).

---

## ⚙️ Configuration (variables d'environnement)

Le comportement du backend est piloté par ces variables d'environnement, définissables dans un fichier `.env` à la racine de `api/`, ou directement dans le shell :

| Variable | Rôle | Obligatoire | Défaut |
| :--- | :--- | :--- | :--- |
| `WB_MEDIAKIT_CONFIG_FILE` | Chemin vers le fichier de configuration Mediakit (`configs/config.toml`) | ✅ Oui | — |
| `WB_MEDIAKIT_AUTO_CHOOSE` | Si activé, le backend choisit lui-même un port libre au démarrage | Non | `1` (activé) |
| `WB_MEDIAKIT_PORT` | Port fixe à utiliser — ignoré si `WB_MEDIAKIT_AUTO_CHOOSE` est activé | Non, sauf si auto-choose désactivé | — |

**Exemple — port automatique** (recommandé pour l'usage courant) :

```env
WB_MEDIAKIT_CONFIG_FILE=/chemin/absolu/vers/configs/config.toml
WB_MEDIAKIT_AUTO_CHOOSE=1
```

**Exemple — port fixe** (utile en développement pour garder la même URL à chaque lancement) :

```env
WB_MEDIAKIT_CONFIG_FILE=/chemin/absolu/vers/configs/config.toml
WB_MEDIAKIT_AUTO_CHOOSE=0
WB_MEDIAKIT_PORT=8123
```

---

## 📦 Builder l'exécutable autonome (PyInstaller)

Nécessite Python 3.11+, les dépendances installées, et le frontend déjà buildé.

```bash
# 1. Build le frontend (le .spec l'embarque dans le binaire)
cd src/workbench/products/mediakit/frontend
npm install
npm run build

# 2. Installer les dépendances Python
pip install -r ../../../../requirements.txt
pip install -r ../requirements.txt
pip install pyinstaller

# 3. Compiler avec le .spec
cd ../api
pyinstaller mediakit.spec
```

Le binaire final se trouve dans `api/dist/mediakit-backend` (ou `mediakit-backend.exe` sous Windows). C'est ce fichier qu'on attache à une Release GitHub pour le distribuer — il ne doit jamais être commité dans le dépôt (voir `.gitignore`, section PyInstaller).

---

## 🖥️ Outils requis sur la machine hôte

Mediakit orchestre des binaires CLI externes qui doivent être installés séparément et accessibles dans le `PATH` :

- **FFmpeg**
- **ImageMagick**
- **SoX**

Vous pouvez vérifier rapidement leur présence et version dans un terminal :

```bash
ffmpeg -version
magick -version
sox --version
```

Une fois Mediakit lancé, l'interface signale aussi l'absence ou l'incompatibilité de version de chacun via l'endpoint `/api/binary/{tool}/check` hérité de Workbench.

---

## 🩹 Dépannage

| Symptôme | Piste |
| :--- | :--- |
| Le navigateur ne s'ouvre pas automatiquement | Vérifiez le terminal : l'URL (ex. `http://127.0.0.1:xxxx`) y est affichée, ouvrez-la manuellement |
| Erreur "binaire introuvable" pour ffmpeg/magick/sox | Vérifiez que le binaire est bien dans le `PATH` (`which ffmpeg`, `which magick`, `which sox`) |
| Port déjà utilisé (mode port fixe) | Changez `WB_MEDIAKIT_PORT` ou repassez en `WB_MEDIAKIT_AUTO_CHOOSE=1` |
| Rien ne se passe au lancement de l'exécutable (Linux) | Vérifiez les droits d'exécution : `chmod +x mediakit-backend` |

---

## 📜 Licence

Ce produit est distribué sous licence **propriétaire** — voir le fichier `LICENSE` de ce dossier. Le framework [Workbench](../../../../README.md) sous-jacent reste sous licence **Apache 2.0**.
