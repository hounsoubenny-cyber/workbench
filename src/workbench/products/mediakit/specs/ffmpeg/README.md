# 🎬 Workbench Mediakit — Spécifications & Catalogue FFmpeg

> Module d'orchestration vidéo haute performance, sécurisé par typage strict Pydantic et exécution asynchrone sans shell.

---

## 1. Vue d'ensemble & Philosophie de Sécurité

Le sous-système FFmpeg de Workbench permet d'automatiser et de piloter des opérations multimédias lourdes (transcodage, découpe, normalisation sonore, incrustations) depuis une interface graphique ou une API web, avec des garanties de sécurité strictes :

- **Isolation des protocoles (`-protocol_whitelist file`) :** Aucun flux réseau externe, injection `http://` ou playlist `concat:` malveillante ne peut être déclenchée.
- **Zéro injection shell :** Les commandes sont construites sous forme de vecteurs d'arguments typés (`PathArg`, `EnumArg`, `PatternArg`) et exécutées via `asyncio.create_subprocess_exec`.
- **Validation `UploadRef` :** Détection automatique des fichiers à téléverser avant le démarrage du sous-processus.

---

## 2. Organisation Modulaire du Catalogue

Le catalogue est scindé en modules thématiques dans `specs/ffmpeg/actions/` :

```text
specs/ffmpeg/
├── base_model.py          # Modèles Pydantic typés & contraintes
├── base_spec.py           # FfmpegSpec (garde-fous globaux)
├── __init__.py            # FFMPEG_ACTIONS (plat) & FFMPEG_CATALOG (structuré)
└── actions/
    ├── actions_convert.py   # Transcodage, compression & GIF
    ├── actions_extract.py   # Démultiplexage audio, frames & sous-titres
    ├── actions_timing.py    # Découpe, vitesse, reverse & FPS
    ├── actions_geometry.py  # Dimensions, crop, formats réseaux sociaux (9:16)
    ├── actions_audio.py     # Traitement sonore au sein du flux vidéo
    ├── actions_effects.py   # Incrustations, sous-titres en dur & filtres
    └── actions_multi.py     # Concaténation multi-fichiers & podcasts
```

---

## 3. Répertoire Exhaustif des Actions

### A. Transcodage, Formats & Compression (`actions_convert.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `ffmpeg_convert_format` | Transcode vers MP4, WebM, MKV, AVI, MOV | `output_format`, `codec` | Rendre un fichier lisible sur navigateur ou TV |
| `ffmpeg_compress_crf` | Compression constante haute fidélité | `crf` (18 à 35), `preset` | Réduire le poids de 60% sans perte visuelle |
| `ffmpeg_compress_target_size` | Calcul de débit pour respecter un poids fixe | `target_size_mb`, `duration_seconds` | Respecter la limite de 10 Mo Discord ou 25 Mo Mail |
| `ffmpeg_video_to_gif` | Génération de GIF fluide 256 couleurs | `fps`, `width`, `duration_s` | Création d'animations pour bannières ou tutoriels |
| `ffmpeg_faststart_web` | Réorganisation du `moov atom` en tête de fichier | `input_file` | Streaming vidéo instantané sans attendre le téléchargement total |

### B. Extractions de Flux (`actions_extract.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `ffmpeg_extract_audio_lossless` | Extraction brute sans ré-encodage (`-c:a copy`) | `input_file` | Sauvegarde rapide de la piste audio originale |
| `ffmpeg_extract_audio_convert` | Extraction avec conversion de format | `output_format`, `bitrate` | Extraire un MP3 192k ou WAV d'une vidéo YouTube |
| `ffmpeg_extract_frame_single` | Capture d'une image fixe précise | `timestamp_seconds`, `output_format` | Créer une miniature officielle ou vérifier une frame |
| `ffmpeg_extract_frames_series` | Planche de miniatures régulières | `every_n_seconds`, `output_format` | Générer un storyboard visuel complet |
| `ffmpeg_extract_subtitles` | Démultiplexage des sous-titres intégrés | `output_format` (srt, vtt) | Récupérer les sous-titres pour traduction |

### C. Découpe & Gestion Temporelle (`actions_timing.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `ffmpeg_trim_with_copy` | Coupe instantanée sans ré-encodage | `start_seconds`, `duration_seconds` | Découpe ultra-rapide calée sur les keyframes |
| `ffmpeg_trim_no_copy` | Coupe chirurgicale à la milliseconde | `start_seconds`, `duration_seconds` | Découpage au millième de seconde près |
| `ffmpeg_speed_video` | Accéléré / Ralenti audio et vidéo synchrones | `speed_factor` (0.25 à 2.0) | Timelapses, vidéos accélérées ou ralenti dramatique |
| `ffmpeg_reverse_video` | Inversion du sens de lecture vidéo et audio | `input_file` | Effet rembobinage créatif |
| `ffmpeg_change_fps` | Conversion de cadence d'images | `fps` (15, 24, 25, 30, 60) | Convertir du 60 FPS en 24 FPS cinéma ou 30 FPS web |

### D. Géométrie, Cadrage & Réseaux Sociaux (`actions_geometry.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `ffmpeg_resize_video` | Redimensionnement aux résolutions standard | `resolution` (1080p, 720p, etc.) | Adapter une vidéo 4K pour un affichage 720p |
| `ffmpeg_crop_video` | Rognage manuel par coordonnées | `width`, `height`, `x`, `y` | Supprimer des bordures ou isoler un sujet |
| `ffmpeg_social_vertical` | Adaptation automatique 9:16 vertical | `mode` (crop_center, blur_background) | Préparer une vidéo 16:9 pour TikTok, Reels et Shorts |
| `ffmpeg_rotate_video` | Rotation géométrique fixe | `rotation` (90° CW, 90° CCW, 180°) | Corriger une vidéo filmée à l'envers sur smartphone |
| `ffmpeg_flip_video` | Effet miroir horizontal ou vertical | `direction` (horizontal, vertical) | Inverser l'angle de vue d'une webcam |
| `ffmpeg_pad_letterbox` | Ajout de bandes pour forcer un ratio | `target_aspect`, `color` | Adapter un film en 16:9 avec bandes noires |

### E. Traitement Audio Intégré (`actions_audio.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `ffmpeg_mute_video` | Suppression totale de la piste sonore | `input_file` | Nettoyer les bruits d'une vidéo muette |
| `ffmpeg_boost_volume` | Amplification ou réduction de volume | `volume_multiplier` | Corriger une prise de son trop faible |
| `ffmpeg_normalize_loudness` | Normalisation broadcast EBU R128 | `target_lufs` (-16.0 standard) | Éviter que YouTube baisse automatiquement le son |
| `ffmpeg_audio_fade` | Fondu progressif en entrée et sortie | `fade_in_s`, `fade_out_s` | Éviter les coupures audio brutales |
| `ffmpeg_fix_audio_delay` | Décalage temporel son/image | `delay_ms` | Réparer les voix désynchronisées des lèvres |
| `ffmpeg_replace_audio` | Remplacement intégral de la bande-son | `new_audio_file` | Ajouter un doublage ou une musique sur une vidéo |
| `ffmpeg_add_background_music` | Mixage d'une musique sous la voix | `music_file`, `music_volume` | Musique d'ambiance pour vlogs et interviews |

### F. Effets Visuels & Incrustations (`actions_effects.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `ffmpeg_add_watermark_image` | Incrustation de logo transparent | `watermark_image`, `position`, `margin_px` | Protection de copyright et branding de chaîne |
| `ffmpeg_burn_subtitles` | Incrustation en dur des sous-titres (hardsub) | `subtitles_file` | Rendre les sous-titres visibles sans lecteur dédié |
| `ffmpeg_adjust_color_eq` | Étalonnage contraste/luminosité/saturation | `brightness`, `contrast`, `saturation` | Rehausser les couleurs d'une vidéo terne |
| `ffmpeg_blur_video` | Floutage global de l'image | `intensity` | Anonymisation complète ou arrière-plans |

### G. Assemblage Multi-fichiers (`actions_multi.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `ffmpeg_concat_videos` | Assemblage de plusieurs clips vidéo bout à bout | `inputs` (liste de vidéos) | Créer un montage final à partir de rushs |
| `ffmpeg_image_plus_audio` | Création d'une vidéo depuis une pochette et un son | `image_file`, `audio_file` | Publier des podcasts ou albums sur YouTube |

---

## 4. Exemple d'Appel API / Frontend

Pour lancer une compression CRF via l'endpoint `/job/create` :

```json
{
  "id": "ffmpeg_compress_crf",
  "user_input": {
    "input_file": "camera_raw.mov",
    "crf": 22,
    "preset": "slow"
  },
  "timeout": 600
}
```