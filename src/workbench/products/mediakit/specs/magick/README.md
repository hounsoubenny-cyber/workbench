# 🪄 Workbench Mediakit — Spécifications & Catalogue ImageMagick

> Moteur de retouche graphique, conversion et manipulation matricielle d'images de qualité studio.

---

## 1. Vue d'ensemble & Confinement Mémoire

ImageMagick est l'outil de référence pour le traitement d'images fixes. Pour contrer les risques de déni de service et d'exploitation par images piégées (bombes de décompression pixel), le socle `MagickSpec` impose des restrictions strictes à chaque commande :

- **Plafond mémoire dur (`-limit memory 512MiB`) :** Aucune allocation démesurée ne peut saturer la RAM de l'hôte.
- **Temps d'exécution maximal (`-limit time 60`) :** Annulation automatique des traitements récursifs anormaux.
- **Validation des extensions & chemins :** Exclusion formelle des préfixes de coders non sécurisés (`msl:`, `https:`, etc.).

---

## 2. Organisation Modulaire du Catalogue

Le catalogue est scindé en modules thématiques dans `specs/magick/actions/` :

```text
specs/magick/
├── base_model.py          # Modèles Pydantic typés & contraintes
├── base_spec.py           # MagickSpec (garde-fous globaux & limites)
├── __init__.py            # MAGICK_ACTIONS (plat) & MAGICK_CATALOG (structuré)
└── actions/
    ├── actions_convert.py   # Transcodage, compression, favicon & métadonnées
    ├── actions_geometry.py  # Dimensions, cadrage, rotation, avatars carrés
    ├── actions_color.py     # Étalonnage colorimétrique, N&B, sépia, auto-level
    ├── actions_effects.py   # Flou, netteté, pixellisation de censure, filtres artistiques
    └── actions_overlays.py  # Filigranes texte/image et bordures
```

---

## 3. Répertoire Exhaustif des Actions

### A. Transcodage & Optimisation Web (`actions_convert.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `magick_convert_format` | Transcodage vers WebP, AVIF, PNG, JPG, TIFF, BMP | `output_format` | Optimisation de compatibilité web moderne |
| `magick_compress_quality` | Réduction contrôlée de la qualité de compression | `quality` (1 à 100), `output_format` | Alléger les images d'un site e-commerce |
| `magick_strip_metadata` | Suppression définitive des métadonnées EXIF et GPS | `output_format` | Protection de la vie privée avant publication en ligne |
| `magick_generate_favicon` | Création d'une icône `.ico` multi-résolution | `input_file` | Générer le favicon d'un site web (16, 32, 48px) |

### B. Géométrie, Cadrage & Dimensions (`actions_geometry.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `magick_resize_image` | Redimensionnement proportionnel ou fixe | `size` (pourcentage ou WxH) | Réduire des photos HD pour l'affichage mobile |
| `magick_crop_image` | Découpe d'une zone rectangulaire (Crop) | `width`, `height`, `x`, `y` | Isoler un visage ou recadrer un sujet |
| `magick_square_thumbnail` | Miniature carrée centrée sans déformation | `dimension` (128 à 1024px) | Photos de profil d'utilisateurs et avatars |
| `magick_canvas_extent` | Extension de toile avec marges colorées | `target_dimension`, `background_color` | Adapter une photo au format carré pour Instagram |
| `magick_rotate_image` | Rotation géométrique précise | `degrees` (90°, 180°, 270°) | Redresser une photo scannée |
| `magick_flip_flop` | Effet miroir horizontal ou vertical | `direction` (horizontal, vertical) | Inverser la symétrie d'une illustration |
| `magick_auto_orient` | Redressement selon le capteur EXIF | `output_format` | Corriger automatiquement les photos prises de travers |

### C. Étalonnage & Couleurs (`actions_color.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `magick_grayscale` | Conversion en Noir & Blanc pur | `output_format` | Documents administratifs et photos artistiques |
| `magick_sepia` | Teinte sépia vintage chaleureuse | `threshold_percent` (30 à 95%) | Rendu photographique ancien |
| `magick_brightness_contrast` | Ajustement fin de luminosité et contraste | `brightness`, `contrast` (-50 à +50) | Rehausser une photo sous-exposée |
| `magick_auto_level` | Égalisation automatique d'histogramme | `output_format` | Améliorer le contraste des documents scannés |
| `magick_negate_colors` | Inversion totale des couleurs (Négatif) | `output_format` | Traitement d'art graphique ou radiographies |
| `magick_colorize_tint` | Filtre monochrome coloré unifié | `color`, `percent` | Bannières et identités visuelles stylisées |

### D. Filtres Artistiques & Anonymisation (`actions_effects.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `magick_blur_gaussian` | Flou gaussien paramétrable | `radius`, `sigma` | Floutage d'arrière-plans ou adoucissement |
| `magick_sharpen` | Accentuation de la netteté des détails | `radius`, `sigma` | Rendre les textes et contours plus nets |
| `magick_pixelate` | Mosaïque de censure / anonymisation | `pixel_size` (2%, 5%, 10%) | Masquer des visages, cartes d'identité ou plaques |
| `magick_vignette` | Assombrissement progressif des 4 coins | `radius`, `sigma` | Focaliser le regard sur le centre de l'image |
| `magick_oil_paint` | Rendu tableau / peinture à l'huile | `radius` (1 à 12) | Effet pictural artistique |
| `magick_charcoal` | Esquisse au fusain / dessin au crayon | `radius` (1 à 10) | Transformer une photo en croquis |

### E. Superpositions & Incrustations (`actions_overlays.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `magick_watermark_image` | Incrustation d'un logo PNG transparent | `watermark_file`, `position` | Filigrane pour protéger des photos de catalogue |
| `magick_watermark_text` | Mention textuelle de copyright | `text`, `position`, `pointsize`, `color` | Signature automatique de clichés |
| `magick_add_border` | Ajout d'une bordure / cadre solide | `thickness`, `color` | Encadrement décoratif de visuels |

---

## 4. Exemple d'Appel API / Frontend

Pour générer un avatar carré centré en WebP :

```json
{
  "id": "magick_square_thumbnail",
  "user_input": {
    "input_file": "portrait.jpg",
    "dimension": "512",
    "output_format": "webp"
  },
  "timeout": 30
}
```
