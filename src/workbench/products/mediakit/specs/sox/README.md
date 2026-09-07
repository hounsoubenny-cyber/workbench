# 🎵 Workbench Mediakit — Spécifications & Catalogue SoX

> Traitement audionumérique de précision studio (DSP) : conversion, normalisation, dynamique et effets acoustiques.

---

## 1. Vue d'ensemble & Architecture DSP

SoX (*Sound eXchange*) est réputé pour son moteur de traitement de signal audio mathématiquement transparent. Contrairement à FFmpeg qui traite des conteneurs multimédias complexes, SoX est spécialisé dans le traitement direct des échantillons sonores (*samples*) :

- **Traitement positionnel rigoureux :** L'entrée et la sortie sont positionnées avant l'enchaînement des effets DSP.
- **Résolution sans artefact :** Rééchantillonnage de haute fidélité avec calcul anti-repliement (*anti-aliasing*).
- **Zéro surcharge :** Exécution ultra-légère idéale pour l'embarqué ou les serveurs à forte concurrence.

---

## 2. Organisation Modulaire du Catalogue

Le catalogue est scindé en modules thématiques dans `specs/sox/actions/` :

```text
specs/sox/
├── base_model.py          # Modèles Pydantic typés & contraintes
├── base_spec.py           # SoxSpec (socle d'exécution)
├── __init__.py            # SOX_ACTIONS (plat) & SOX_CATALOG (structuré)
└── actions/
    ├── actions_convert.py   # Formats, échantillonnage, quantification, canaux
    ├── actions_dynamics.py  # Normalisation, gain, compression compand, silences
    ├── actions_timing.py    # Découpe (trim), fondus (fade), silences (pad), tempo, pitch
    ├── actions_eq.py        # Égaliseurs bass/treble, filtres passe-bas/haut, paramétrique
    └── actions_effects.py   # Réverbération, écho, chorus spatialisé, overdrive
```

---

## 3. Répertoire Exhaustif des Actions

### A. Transcodage & Fréquences (`actions_convert.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `sox_convert_format` | Transcodage entre MP3, WAV, FLAC et OGG | `output_format` | Rendre un audio compatible avec un lecteur cible |
| `sox_resample_rate` | Modification de la fréquence d'échantillonnage | `sample_rate` (8kHz à 48kHz) | Préparer un fichier pour Whisper/IA (16kHz) ou CD (44.1kHz) |
| `sox_channels_remix` | Conversion de canaux (Stéréo $\leftrightarrow$ Mono) | `channels` (1 ou 2) | Réduire de 50% la taille d'une voix enregistrée |
| `sox_extract_channel` | Isolation d'un seul canal (Gauche ou Droit) | `channel` (left, right) | Isoler la piste d'un micro défectueux |
| `sox_change_bit_depth` | Modification de la quantification binaire | `bit_depth` (16, 24, 32 bits) | Préparer un master audio pour la distribution |

### B. Dynamique, Volume & Nettoyage (`actions_dynamics.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `sox_normalize_gain` | Normalisation de crête (`norm`) sans saturation | `target_db` (-24.0 à 0.0 dB) | Maximiser le volume d'une piste sans écrêtage |
| `sox_adjust_gain` | Ajustement direct du gain sonore en dB | `gain_db` (-30.0 à +30.0 dB) | Rehausser un enregistrement audio trop faible |
| `sox_compand_dynamics` | Compresseur multi-bandes professionnel | `profile` (podcast_voice, loudness) | Lisser les écarts de voix pour un son percutant type radio |
| `sox_strip_silence` | Détection et coupe automatique des blancs | `threshold_percent`, `min_silence_duration` | Supprimer les silences inutiles au début/fin d'un podcast |

### C. Découpe, Vitesse & Hauteur de Ton (`actions_timing.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `sox_trim_audio` | Découpe d'un segment temporel précis | `start_seconds`, `duration_seconds` | Extraire un échantillon ou un refrain |
| `sox_fade_audio` | Fondus sonores d'ouverture et de fermeture | `fade_in_s`, `fade_out_s`, `curve` | Éviter les clics et coupures sonores brusques |
| `sox_pad_silence` | Insertion de silences au début ou à la fin | `pad_start_s`, `pad_end_s` | Laisser un temps de pause avant le jingle |
| `sox_change_tempo` | Accéléré/Ralenti sans altérer la voix | `factor` (0.5 à 2.5) | Écouter un cours audio plus rapidement en restant intelligible |
| `sox_change_pitch` | Décalage de tonalité sans changer le tempo | `cents` (-1200 à +1200) | Ajuster la tonalité pour correspondre à un instrument |
| `sox_reverse_audio` | Lecture de la piste audio à l'envers | `output_format` | Création d'effets sonores inversés de transition |

### D. Égalisation & Filtrage Fréquentiel (`actions_eq.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `sox_bass_treble` | Réglage direct des basses et des aigus | `bass_db`, `treble_db` | Donner de la rondeur ou de la clarté à une piste |
| `sox_lowpass_filter` | Filtre passe-bas (coupe les aigus agressifs) | `cutoff_hz` (200 à 20000 Hz) | Adoucir un son strident ou simuler un son étouffé |
| `sox_highpass_filter` | Filtre passe-haut anti-rumble | `cutoff_hz` (20 à 5000 Hz) | Supprimer les vibrations de micro et bruits de manipulation |
| `sox_parametric_equalizer` | Égaliseur paramétrique chirurgical | `frequency_hz`, `bandwidth_hz`, `gain_db` | Éliminer un sifflement parasite précis (larsen) |

### E. Effets Acoustiques & Spatialisation (`actions_effects.py`)

| ID Action | Description | Paramètres clés | Cas d'usage typiques |
| :--- | :--- | :--- | :--- |
| `sox_reverb_audio` | Réverbération acoustique de pièce | `reverberance`, `damping` | Ajouter de la profondeur et de l'espace à une voix sèche |
| `sox_echo_audio` | Écho et délai rythmique spatialisé | `delay_ms`, `decay` | Effets de répétition spatiale |
| `sox_chorus_audio` | Épaississement multi-voix (Chorus) | `intensity` (subtle, medium, heavy) | Donner du corps à une voix ou une guitare acoustique |
| `sox_overdrive_audio` | Saturation harmonique analogique chaude | `gain_db`, `colour` | Effet grain vintage ou voix saturée |

---

## 4. Exemple d'Appel API / Frontend

Pour normaliser un enregistrement de voix et couper les silences parasites :

```json
{
  "id": "sox_strip_silence",
  "user_input": {
    "input_file": "interview_brute.wav",
    "threshold_percent": 1.0,
    "min_silence_duration": 0.4,
    "output_format": "wav"
  },
  "timeout": 60
}
```
