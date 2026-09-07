#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 18:24:36 2026

@author: hounsousamuel
"""

from typing import Literal, List
from pydantic import BaseModel, Field, model_validator
from workbench.specs.uploads import UploadRef

# =============================================================================
# SOCLE DE BASE
# =============================================================================

class BaseFfmpegActionInput(BaseModel):
    """Input commun pour toute action FFmpeg prenant au moins un fichier source."""
    input_file: str = UploadRef(description="Fichier vidéo ou audio source principal")


_RESOLUTIONS = ["1920x1080", "1280x720", "854x480", "640x360", "426x240"]

_VALID_VIDEO_CODECS_BY_FORMAT = {
    "mp4": ["libx264", "libx265"],
    "mkv": ["libx264", "libx265", "vp9"],
    "webm": ["vp9"],
    "avi": ["libx264"],
    "mov": ["libx264", "libx265"],
}

_AUDIO_CODEC_BY_FORMAT = {
    "mp4": "aac",
    "mkv": "aac",
    "webm": "libopus",
    "avi": "mp3",
    "mov": "aac",
}


# =============================================================================
# A. TRANSCODAGE & CONTENEURS
# =============================================================================

class ConvertVideoInput(BaseFfmpegActionInput):
    output_format: Literal["mp4", "webm", "mkv", "avi", "mov"] = "mp4"
    codec: Literal["libx264", "libx265", "vp9"] = "libx264"

    @model_validator(mode="after")
    def check_codec_compatible(self) -> "ConvertVideoInput":
        allowed = _VALID_VIDEO_CODECS_BY_FORMAT.get(self.output_format, [])
        if self.codec not in allowed:
            raise ValueError(f"Codec '{self.codec}' incompatible avec '{self.output_format}' (autorisés : {allowed})")
        return self


class VideoToGifInput(BaseFfmpegActionInput):
    fps: int = Field(default=12, ge=5, le=30, description="Cadence d'images (FPS) du GIF")
    width: int = Field(default=480, ge=160, le=1080, description="Largeur max en pixels")
    duration_s: float = Field(default=5.0, ge=0.5, le=30.0, description="Durée max du GIF en secondes")


class FaststartWebInput(BaseFfmpegActionInput):
    pass


# =============================================================================
# B. COMPRESSION & POIDS
# =============================================================================

class CompressCrfInput(BaseFfmpegActionInput):
    crf: int = Field(default=24, ge=18, le=35, description="Facteur CRF (18=quasi sans perte, 28=léger, 32=très compressé)")
    preset: Literal["ultrafast", "fast", "medium", "slow", "veryslow"] = "medium"


class CompressTargetSizeInput(BaseFfmpegActionInput):
    target_size_mb: float = Field(default=8.0, ge=1.0, le=500.0, description="Poids cible souhaité en mégaoctets")
    duration_seconds: float = Field(..., gt=0.0, description="Durée exacte de la vidéo en secondes pour calcul du bitrate")


# =============================================================================
# C. EXTRACTION
# =============================================================================

class ExtractAudioLosslessInput(BaseFfmpegActionInput):
    pass


class ExtractAudioConvertInput(BaseFfmpegActionInput):
    output_format: Literal["mp3", "wav", "aac", "flac", "ogg"] = "mp3"
    bitrate: Literal["128k", "192k", "256k", "320k"] = "192k"


class ExtractFrameInput(BaseFfmpegActionInput):
    timestamp_seconds: float = Field(default=1.0, ge=0.0, description="Moment de la capture en secondes")
    output_format: Literal["png", "jpg"] = "png"


class ExtractFramesSeriesInput(BaseFfmpegActionInput):
    every_n_seconds: int = Field(default=5, ge=1, le=120, description="Intervalle de capture en secondes")
    output_format: Literal["png", "jpg"] = "jpg"


class ExtractSubtitlesInput(BaseFfmpegActionInput):
    output_format: Literal["srt", "vtt"] = "srt"


# =============================================================================
# D. DÉCOUPE, VITESSE & TIMING
# =============================================================================

class TrimVideoInput(BaseFfmpegActionInput):
    start_seconds: float = Field(default=0.0, ge=0.0, description="Début du segment en secondes")
    duration_seconds: float = Field(default=10.0, gt=0.01, description="Durée du segment en secondes")


class SpeedVideoInput(BaseFfmpegActionInput):
    speed_factor: Literal["0.25", "0.5", "0.75", "1.25", "1.5", "2.0"] = "1.5"


class ReverseVideoInput(BaseFfmpegActionInput):
    pass


class ChangeFpsInput(BaseFfmpegActionInput):
    fps: Literal[15, 24, 25, 30, 60] = 30


# =============================================================================
# E. GÉOMÉTRIE, CADRAGE & RÉSEAUX SOCIAUX
# =============================================================================

class ResizeVideoInput(BaseFfmpegActionInput):
    resolution: Literal["1920x1080", "1280x720", "854x480", "640x360", "426x240"] = "1280x720"


class CropVideoInput(BaseFfmpegActionInput):
    width: int = Field(default=640, ge=50, description="Largeur du rectangle découpé")
    height: int = Field(default=360, ge=50, description="Hauteur du rectangle découpé")
    x: int = Field(default=0, ge=0, description="Position X du coin supérieur gauche")
    y: int = Field(default=0, ge=0, description="Position Y du coin supérieur gauche")


class SocialVerticalInput(BaseFfmpegActionInput):
    mode: Literal["crop_center", "blur_background"] = "blur_background"


class RotateVideoInput(BaseFfmpegActionInput):
    rotation: Literal["90_cw", "90_ccw", "180"] = "90_cw"


class FlipVideoInput(BaseFfmpegActionInput):
    direction: Literal["horizontal", "vertical"] = "horizontal"


class PadLetterboxInput(BaseFfmpegActionInput):
    target_aspect: Literal["16:9", "4:3", "1:1"] = "16:9"
    color: Literal["black", "white"] = "black"


# =============================================================================
# F. TRAITEMENT AUDIO DANS LA VIDÉO
# =============================================================================

class MuteVideoInput(BaseFfmpegActionInput):
    pass


class BoostVolumeInput(BaseFfmpegActionInput):
    volume_multiplier: float = Field(default=1.5, ge=0.1, le=5.0, description="1.0 = original, 2.0 = double, 0.5 = moitié")


class NormalizeLoudnessInput(BaseFfmpegActionInput):
    target_lufs: float = Field(default=-16.0, ge=-24.0, le=-14.0, description="Niveau sonore cible (-16 YouTube/Web, -23 Broadcast TV)")


class AudioFadeInput(BaseFfmpegActionInput):
    fade_in_s: float = Field(default=2.0, ge=0.0)
    fade_out_s: float = Field(default=2.0, ge=0.0)

class FixAudioDelayInput(BaseFfmpegActionInput):
    delay_ms: int = Field(default=200, ge=0, le=5000, description="Retard audio en millisecondes")
    
class ReplaceAudioInput(BaseFfmpegActionInput):
    new_audio_file: str = UploadRef(description="Nouvelle piste audio remplaçant l'originale")


class AddBackgroundMusicInput(BaseFfmpegActionInput):
    music_file: str = UploadRef(description="Fichier musical de fond")
    music_volume: float = Field(default=0.2, ge=0.05, le=1.0, description="Volume de la musique (0.2 = 20%)")


# =============================================================================
# G. INCRUSTATIONS & EFFETS VISUELS
# =============================================================================

class AddWatermarkInput(BaseFfmpegActionInput):
    watermark_image: str = UploadRef(description="Image PNG/JPG avec transparence recommandée")
    position: Literal["top_left", "top_right", "bottom_left", "bottom_right", "center"] = "bottom_right"
    margin_px: int = Field(default=15, ge=0, le=100)


class BurnSubtitlesInput(BaseFfmpegActionInput):
    subtitles_file: str = UploadRef(description="Fichier de sous-titres (.srt ou .vtt)")


class AdjustColorEqInput(BaseFfmpegActionInput):
    brightness: float = Field(default=0.0, ge=-0.5, le=0.5, description="Luminosité (-0.5 à +0.5)")
    contrast: float = Field(default=1.0, ge=0.2, le=2.0, description="Contraste (1.0 = normal)")
    saturation: float = Field(default=1.0, ge=0.0, le=3.0, description="Saturation (0.0 = N&B, 1.0 = normal)")


class BlurVideoInput(BaseFfmpegActionInput):
    intensity: int = Field(default=5, ge=1, le=20, description="Rayon du flou gaussien")


# =============================================================================
# H. ASSEMBLAGE & MULTI-FICHIERS
# =============================================================================

class ConcatVideosInput(BaseModel):
    inputs: List[str] = UploadRef(description="Liste ordonnée des vidéos à assembler")
    has_audio: bool = Field(
        default=True,
        description="Conserver la piste audio (désactiver si les vidéos sources sont muettes)"
    )


class ImagePlusAudioInput(BaseModel):
    image_file: str = UploadRef(description="Image de couverture (statique)")
    audio_file: str = UploadRef(description="Piste audio (podcasts, musique)")