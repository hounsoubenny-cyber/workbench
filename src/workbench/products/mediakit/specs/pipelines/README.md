---

```markdown
# 🧩 Workbench Mediakit — Spécifications & Catalogue des Pipelines

> Moteur d'orchestration multi-étapes et inter-outils (FFmpeg, ImageMagick, SoX) sans aucun pipe Unix (`|`), sécurisé par passage de fichiers en environnement confiné.

---

## 1. Philosophie & Architecture des Pipelines

Contrairement aux scripts bash traditionnels qui enchaînent des outils via des tubes Unix (`outil1 | outil2`), le moteur de `Workbench` repose sur le paradigme **File-Passing Sandbox** :

```text
┌───────────────────────────────────────────────────────────────────────────┐
│                     ESPACE DE TRAVAIL ISOLÉ (WORKDIR)                     │
│                                                                           │
│  [Fichier Source]                                                         │
│         │                                                                 │
│         ▼                                                                 │
│  ┌──────────────┐      ┌─────────────────────────┐                        │
│  │ ÉTAPE 1      ├─────►│ Fichier Intermédiaire 1 │                        │
│  │ (ex: SoX)    │      └────────────┬────────────┘                        │
│  └──────────────┘                   │                                     │
│                                     ▼                                     │
│                        ┌─────────────────────────┐      ┌──────────────┐  │
│                        │ ÉTAPE 2 (ex: Magick)    ├─────►│ Fichier 2    │  │
│                        └─────────────────────────┘      └──────┬───────┘  │
│                                                                │          │
│                                                                ▼          │
│                                                         ┌──────────────┐  │
│                                                         │ ÉTAPE 3      │  │
│                                                         │ (ex: FFmpeg) │  │
│                                                         └──────┬───────┘  │
│                                                                │          │
│                                                                ▼          │
│                                                         [LIVRABLE FINAL]  │
└───────────────────────────────────────────────────────────────────────────┘
```

### Les 4 Piliers Techniques :
1. **Zéro injection shell :** Aucun sous-shell `sh` ou `bash` n'est invoqué. Chaque étape est lancée via `asyncio.create_subprocess_exec` avec des listes d'arguments typés (`Arg`).
2. **Interopérabilité totale :** Un outil audio (`sox`) peut préparer un fichier pour un outil graphique (`magick`), qui prépare lui-même des assets pour un encodeur vidéo (`ffmpeg`).
3. **Traçabilité des logs en direct :** Chaque ligne de log émise sur le WebSocket porte l'identifiant de son étape (`step_id`), permettant à l'interface d'afficher la progression étape par étape.
4. **Récupération des états (`outputs["_previous"]`) :** L'étape $N$ consomme automatiquement la sortie de l'étape $N-1$ sans que l'utilisateur n'ait à manipuler de chemins de fichiers intermédiaires.

---

## 2. Organisation des Fichiers

```text
specs/pipelines/
├── base_model.py          # 17 Modèles Pydantic d'entrée (schémas formulaires UI)
├── pipelines_video.py     # 5 Pipelines 100% Vidéo (FFmpeg)
├── pipelines_image.py     # 4 Pipelines 100% Image (ImageMagick)
├── pipelines_audio.py     # 4 Pipelines 100% Audio (SoX)
├── pipelines_combo.py     # 4 Super-Pipelines croisés multi-outils
└── __init__.py            # PIPELINE_ACTIONS (plat) & PIPELINE_CATALOG (structuré)
```

---

## 3. Répertoire Exhaustif des 17 Pipelines

### A. Pipelines Vidéo Dédiés — 100% FFmpeg (`pipelines_video.py`)

| ID Pipeline | Description | Enchaînement des étapes | Paramètres UI clés |
| :--- | :--- | :--- | :--- |
| `pipeline_social_repurposer` | Recyclage 16:9 vers Short/Reel 9:16 avec logo | `trim_no_copy` $\to$ `social_vertical` $\to$ `watermark` | `start_seconds`, `duration_seconds`, `vertical_mode`, `watermark_logo` |
| `pipeline_web_optimizer` | Descente 720p, compression CRF et faststart | `resize_video` $\to$ `compress_crf` $\to$ `faststart_web` | `resolution`, `crf_quality` |
| `pipeline_pro_gif_maker` | Extrait vidéo converti en GIF fluide 256 couleurs | `trim_with_copy` $\to$ `video_to_gif` | `start_seconds`, `duration_seconds`, `fps`, `width` |
| `pipeline_hardsub_social` | Vidéo verticale avec sous-titres incrustés | `burn_subtitles` $\to$ `social_vertical` | `input_file`, `subtitles_file`, `vertical_mode` |
| `pipeline_speedup_mute` | Création d'un timelapse accéléré muet | `speed_video` $\to$ `mute_video` | `speed_factor` (1.25x à 2.0x) |

---

### B. Pipelines Image Dédiés — 100% ImageMagick (`pipelines_image.py`)

| ID Pipeline | Description | Enchaînement des étapes | Paramètres UI clés |
| :--- | :--- | :--- | :--- |
| `pipeline_ecommerce_product` | Photo produit e-commerce (orient, carré, strip, WebP) | `auto_orient` $\to$ `square_thumbnail` $\to$ `strip_metadata` $\to$ `compress_webp` | `dimension` (512, 800, 1024), `quality` |
| `pipeline_vintage_card` | Carte postale rétro avec virage sépia et cadre | `sepia` $\to$ `vignette` $\to$ `add_border` | `sepia_intensity`, `border_color`, `border_thickness` |
| `pipeline_favicon_generator` | Création de suite d'icônes Favicon ICO multi-tailles | `square_thumbnail` $\to$ `generate_favicon` | `input_file` (image carrée) |
| `pipeline_privacy_blur` | Anonymisation de visage/document + suppression GPS | `blur_gaussian` $\to$ `strip_metadata` | `blur_intensity` (4 à 40) |

---

### C. Pipelines Audio Dédiés — 100% SoX (`pipelines_audio.py`)

| ID Pipeline | Description | Enchaînement des étapes | Paramètres UI clés |
| :--- | :--- | :--- | :--- |
| `pipeline_podcast_mastering` | Mastering studio (silences, anti-rumble, compand, norm) | `strip_silence` $\to$ `highpass` $\to$ `compand` $\to$ `normalize_gain` | `highpass_cutoff_hz`, `target_peak_db`, `output_format` |
| `pipeline_speech_to_text_prep` | Conditionnement vocal optimal pour IA (Whisper) | `channels_remix` $\to$ `resample_16k` $\to$ `normalize_gain` | `input_file` |
| `pipeline_dj_stinger` | Jingle de transition radio avec accélération et réverb | `trim_audio` $\to$ `change_tempo` $\to$ `reverb` $\to$ `fade_audio` | `duration_seconds`, `tempo_factor`, `fade_out_seconds` |
| `pipeline_lofi_retro` | Effet vintage Lo-Fi (filtre étouffé, basses, saturation) | `lowpass` $\to$ `bass_treble` $\to$ `overdrive` | `overdrive_gain_db` |

---

### D. Super-Pipelines Croisés Multi-Outils (`pipelines_combo.py`)

Ces workflows exploitent la synergie des 3 outils réunis pour réaliser des opérations complexes impossibles avec un seul binaire :

#### 1. `pipeline_youtube_podcast_card` (SoX + ImageMagick $\to$ FFmpeg)
* **Objectif :** Transformer un enregistrement audio brut en vidéo YouTube professionnelle avec pochette d'illustration 1080p.
* **Étapes :**
  1. **[SoX]** Normalisation dynamique du volume vocal à -1.0 dB.
  2. **[ImageMagick]** Adaptation de l'image de couverture au format 1920x1080 avec bandes de fond.
  3. **[FFmpeg]** Multiplexage de l'image fixe et de l'audio masterisé en vidéo MP4 H.264/AAC.
* **Livrable :** Vidéo `podcast_video.mp4` prête à publier.

#### 2. `pipeline_video_audio_remaster` (FFmpeg $\to$ SoX $\to$ FFmpeg)
* **Objectif :** Restaurer la bande-son d'une vidéo sans toucher à l'image.
* **Étapes :**
  1. **[FFmpeg]** Extraction du flux audio vers un fichier WAV 192k sans perte.
  2. **[SoX]** Traitement dynamique studio (compresseur multi-bandes vocal + égalisation de présence).
  3. **[FFmpeg]** Réinjection de l'audio nettoyé dans le flux vidéo d'origine sans ré-encodage vidéo (`-c:v copy`).
* **Livrable :** Vidéo `audio_replaced.mp4` avec son de studio.

#### 3. `pipeline_video_teaser_card` (FFmpeg $\to$ ImageMagick)
* **Objectif :** Générer une affiche promotionnelle pour réseaux sociaux depuis un rush vidéo.
* **Étapes :**
  1. **[FFmpeg]** Extraction d'une image fixe haute définition à un timestamp précis.
  2. **[ImageMagick]** Incrustation d'un badge textuel promotionnel (ex: *"NOUVEL ÉPISODE"*).
  3. **[ImageMagick]** Encadrement de l'image avec une bordure stylisée.
* **Livrable :** Image promotionnelle `bordered.jpg`.

#### 4. `pipeline_video_to_optimized_webp` (FFmpeg $\to$ ImageMagick)
* **Objectif :** Créer une animation WebP ultra-légère (alternative moderne aux GIFs lourds).
* **Étapes :**
  1. **[FFmpeg]** Découpe du segment vidéo court.
  2. **[FFmpeg]** Conversion du flux vidéo en animation brute.
  3. **[ImageMagick]** Compression destructive WebP optimisée pour le web.
* **Livrable :** Fichier `compressed.webp`.

---

## 4. Exemple d'Appel API / Client

Exemple de requête multipart pour lancer le **Super-Pipeline Podcast YouTube** :

```bash
curl -X POST http://localhost:8000/job/create \
  -F 'data={
    "id": "pipeline_youtube_podcast_card",
    "user_input": {
      "audio_file": "interview.wav",
      "cover_image": "cover.png",
      "background_color": "black"
    },
    "timeout": 300
  }' \
  -F 'files=@/chemin/vers/interview.wav' \
  -F 'files=@/chemin/vers/cover.png'
```

### Réponse API immédiate :
```json
{
  "job_id": "wb-job_7xK9mP2qR4vT8wX1yZ3aB5cD7eF9gH1j",
  "workdir": "/tmp/wb-job_7xK9mP2qR4vT8wX1yZ3aB5cD7eF9gH1j_abc123",
  "spec_id": "pipeline_youtube_podcast_card",
  "is_action_spec": false,
  "output_files": [
    {"id": "step_sox_norm", "file": "normalized.wav", "pos": 0, "last": false},
    {"id": "step_magick_cover", "file": "canvas_padded.jpg", "pos": 1, "last": false},
    {"id": "step_ffmpeg_mux", "file": "podcast_video.mp4", "pos": 2, "last": true}
  ]
}
```

---

## 5. Intégration Frontend & Menus

Le fichier `specs/pipelines/__init__.py` expose :

- **`PIPELINE_ACTIONS` :** Dictionnaire plat pour résolution $O(1)$ directe par `job_id`.
- **`PIPELINE_CATALOG` :** Dictionnaire structuré par catégories (`video`, `image`, `audio`, `combo`), chacune fournissant :
  - `description` : Texte de présentation pour les en-têtes d'onglets UI.
  - `values` : Liste des spécifications prêtes pour l'affichage des cartes d'actions.
```

---