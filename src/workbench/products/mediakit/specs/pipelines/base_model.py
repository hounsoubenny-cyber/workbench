#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Sep  5 11:31:51 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Modèles Pydantic pour les entrées globales de tous les Pipelines.

Chaque modèle représente le formulaire que l'utilisateur remplit dans l'interface
graphique pour lancer un workflow complet à plusieurs étapes. Les fichiers d'entrée
sont strictement annotés avec UploadRef pour assurer leur transfert automatique.
"""

from typing import Literal
from pydantic import BaseModel, Field
from workbench.specs.uploads import UploadRef


# =============================================================================
# A. PIPELINES 100% VIDÉO (FFMPEG)
# =============================================================================

class SocialRepurposerInput(BaseModel):
    input_file: str = UploadRef(description="Vidéo source paysage (16:9)")
    watermark_logo: str = UploadRef(description="Logo PNG transparent")
    start_seconds: float = Field(default=0.0, ge=0.0, description="Point de départ de l'extrait")
    duration_seconds: float = Field(default=30.0, ge=3.0, le=90.0, description="Durée du Short / Reel")
    vertical_mode: Literal["blur_background", "crop_center"] = "blur_background"
    logo_position: Literal["top_left", "top_right", "bottom_left", "bottom_right"] = "top_right"


class WebOptimizerInput(BaseModel):
    input_file: str = UploadRef(description="Vidéo haute résolution à optimiser pour le web")
    resolution: Literal["1280x720", "854x480", "640x360"] = "1280x720"
    crf_quality: int = Field(default=28, ge=20, le=35, description="Qualité CRF (28 = excellent ratio poids/qualité)")


class ProGifMakerInput(BaseModel):
    input_file: str = UploadRef(description="Vidéo source")
    start_seconds: float = Field(default=0.0, ge=0.0)
    duration_seconds: float = Field(default=4.0, ge=0.5, le=15.0)
    fps: int = Field(default=15, ge=5, le=25)
    width: int = Field(default=480, ge=200, le=800)


class HardsubSocialInput(BaseModel):
    input_file: str = UploadRef(description="Vidéo source")
    subtitles_file: str = UploadRef(description="Fichier de sous-titres (.srt)")
    vertical_mode: Literal["blur_background", "crop_center"] = "crop_center"


class SpeedupMuteInput(BaseModel):
    input_file: str = UploadRef(description="Vidéo source")
    speed_factor: Literal["1.25", "1.5", "2.0"] = "2.0"


# =============================================================================
# B. PIPELINES 100% IMAGE (IMAGEMAGICK)
# =============================================================================

class EcommerceProductInput(BaseModel):
    input_file: str = UploadRef(description="Photo brute de produit")
    dimension: Literal["512", "800", "1024"] = "800"
    quality: int = Field(default=82, ge=50, le=95, description="Qualité de compression WebP")


class VintageCardInput(BaseModel):
    input_file: str = UploadRef(description="Photo source")
    sepia_intensity: int = Field(default=80, ge=40, le=95)
    border_color: Literal["black", "white", "gold", "gray"] = "white"
    border_thickness: int = Field(default=20, ge=5, le=80)


class FaviconGeneratorInput(BaseModel):
    input_file: str = UploadRef(description="Logo ou icône carrée haute résolution (PNG)")


class PrivacyBlurInput(BaseModel):
    input_file: str = UploadRef(description="Photo avec visages ou données privées")
    blur_intensity: int = Field(default=12, ge=4, le=40)


# =============================================================================
# C. PIPELINES 100% AUDIO (SOX)
# =============================================================================

class PodcastMasteringInput(BaseModel):
    input_file: str = UploadRef(description="Enregistrement vocal brut d'interview / podcast")
    highpass_cutoff_hz: int = Field(default=80, ge=40, le=160, description="Fréquence de coupure anti-rumble")
    target_peak_db: float = Field(default=-1.0, ge=-6.0, le=0.0, description="Plafond de crête (dB)")
    output_format: Literal["mp3", "wav", "flac"] = "mp3"


class SpeechToTextPrepInput(BaseModel):
    input_file: str = UploadRef(description="Fichier audio à transcrire avec Whisper / IA")


class DjStingerInput(BaseModel):
    input_file: str = UploadRef(description="Jingle ou piste musicale")
    start_seconds: float = Field(default=0.0, ge=0.0)
    duration_seconds: float = Field(default=15.0, ge=2.0, le=60.0)
    tempo_factor: float = Field(default=1.15, ge=0.8, le=2.0)
    fade_out_seconds: float = Field(default=3.0, ge=0.5, le=10.0)


class LofiRetroInput(BaseModel):
    input_file: str = UploadRef(description="Musique moderne à transformer en Lo-Fi")
    overdrive_gain_db: int = Field(default=12, ge=2, le=30)


# =============================================================================
# D. SUPER-PIPELINES CROISÉS (SOX + MAGICK + FFMPEG)
# =============================================================================

class YoutubePodcastCardInput(BaseModel):
    audio_file: str = UploadRef(description="Piste audio du podcast")
    cover_image: str = UploadRef(description="Illustration de couverture carrée ou libre")
    background_color: Literal["black", "white", "gray"] = "black"


class VideoAudioRemasterInput(BaseModel):
    video_file: str = UploadRef(description="Vidéo dont la bande-son doit être remasterisée")
    normalize_peak_db: float = Field(default=-1.0, ge=-6.0, le=0.0)
    bass_boost_db: float = Field(default=2.5, ge=-10.0, le=10.0)


class VideoTeaserCardInput(BaseModel):
    video_file: str = UploadRef(description="Vidéo source")
    snapshot_timestamp_s: float = Field(default=10.0, ge=0.0)
    teaser_text: str = Field(default="NOUVEL ÉPISODE", max_length=40)
    text_color: Literal["white", "gold", "yellow", "red"] = "gold"


class VideoToOptimizedWebpInput(BaseModel):
    video_file: str = UploadRef(description="Extrait vidéo source")
    start_seconds: float = Field(default=0.0, ge=0.0)
    duration_seconds: float = Field(default=4.0, ge=1.0, le=15.0)
    width: int = Field(default=480, ge=240, le=720)