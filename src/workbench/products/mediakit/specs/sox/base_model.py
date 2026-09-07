#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Sep  1 18:24:36 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Modèles d'input Pydantic complets pour toutes les actions SoX.
"""

from typing import Literal
from pydantic import BaseModel, Field
from workbench.specs.uploads import UploadRef


class BaseSoxActionInput(BaseModel):
    """Socle commun pour toute action SoX avec fichier audio source."""
    input_file: str = UploadRef(description="Fichier audio source principal")


# ─── A. CONVERT, SAMPLE RATE & CANAUX ───
class ConvertAudioInput(BaseSoxActionInput):
    output_format: Literal["mp3", "wav", "flac", "ogg"] = "mp3"


class ResampleAudioInput(BaseSoxActionInput):
    sample_rate: Literal["48000", "44100", "22050", "16000", "8000"] = "44100"
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class ChannelsRemixInput(BaseSoxActionInput):
    channels: Literal["1", "2"] = "1"
    output_format: Literal["wav", "mp3", "flac"] = "wav"


class ExtractChannelInput(BaseSoxActionInput):
    channel: Literal["left", "right"] = "left"
    output_format: Literal["wav", "mp3", "flac"] = "wav"


class ChangeBitDepthInput(BaseSoxActionInput):
    bit_depth: Literal["16", "24", "32"] = "16"
    output_format: Literal["wav", "flac"] = "wav"


# ─── B. VOLUME, DYNAMIQUE & NETTOYAGE ───
class NormalizeGainInput(BaseSoxActionInput):
    target_db: float = Field(default=-1.0, le=0.0, ge=-24.0, description="Niveau crête max (ex: -1.0 dB pour éviter le clipping)")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class AdjustGainInput(BaseSoxActionInput):
    gain_db: float = Field(default=3.0, ge=-30.0, le=30.0, description="Ajustement de volume en dB (+ ou -)")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class CompandDynamicsInput(BaseSoxActionInput):
    profile: Literal["podcast_voice", "loudness_booster", "subtle_compression"] = "podcast_voice"
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class StripSilenceInput(BaseSoxActionInput):
    threshold_percent: float = Field(default=1.0, ge=0.1, le=10.0, description="Seuil de détection du silence (1% recommandé)")
    min_silence_duration: float = Field(default=0.5, ge=0.1, le=5.0, description="Durée min d'un silence à supprimer (secondes)")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


# ─── C. DÉCOUPE, VITESSE & TIMING ───
class TrimAudioInput(BaseSoxActionInput):
    start_seconds: float = Field(default=0.0, ge=0.0, description="Début du segment en secondes")
    duration_seconds: float = Field(default=30.0, gt=0.01, description="Durée du segment en secondes")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class FadeAudioInput(BaseSoxActionInput):
    curve: Literal["t", "q", "h"] = "t"
    fade_in_s: float = Field(default=3.0, ge=0.0)
    fade_out_s: float = Field(default=3.0, ge=0.0)
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class PadSilenceInput(BaseSoxActionInput):
    pad_start_s: float = Field(default=0.0, ge=0.0, description="Secondes de silence à ajouter au début")
    pad_end_s: float = Field(default=2.0, ge=0.0, description="Secondes de silence à ajouter à la fin")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class ChangeTempoInput(BaseSoxActionInput):
    factor: float = Field(default=1.2, ge=0.5, le=2.5, description="Facteur tempo sans changer la hauteur de voix (1.0 = normal)")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class ChangePitchInput(BaseSoxActionInput):
    cents: int = Field(default=200, ge=-1200, le=1200, description="Hauteur en centièmes de demi-ton (+100 = 1 demi-ton plus haut)")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class ReverseAudioInput(BaseSoxActionInput):
    output_format: Literal["wav", "flac", "mp3"] = "wav"


# ─── D. ÉGALISATION & FILTRES FRÉQUENTIELS ───
class BassTrebleInput(BaseSoxActionInput):
    bass_db: float = Field(default=3.0, ge=-20.0, le=20.0, description="Gain des basses en dB")
    treble_db: float = Field(default=0.0, ge=-20.0, le=20.0, description="Gain des aigus en dB")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class LowPassFilterInput(BaseSoxActionInput):
    cutoff_hz: int = Field(default=3000, ge=200, le=20000, description="Fréquence de coupure haute (Hz)")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class HighPassFilterInput(BaseSoxActionInput):
    cutoff_hz: int = Field(default=100, ge=20, le=5000, description="Fréquence de coupure basse pour éliminer le rumble (Hz)")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class ParametricEqualizerInput(BaseSoxActionInput):
    frequency_hz: int = Field(default=1000, ge=40, le=16000, description="Fréquence centrale de la bande")
    bandwidth_hz: int = Field(default=200, ge=10, le=4000, description="Largeur de la bande passante (Hz)")
    gain_db: float = Field(default=3.0, ge=-24.0, le=24.0, description="Amplification ou atténuation en dB")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


# ─── E. EFFETS ACOUSTIQUES & MODULATION ───
class ReverbAudioInput(BaseSoxActionInput):
    reverberance: int = Field(default=50, ge=0, le=100, description="Pourcentage de réverbération")
    damping: int = Field(default=50, ge=0, le=100, description="Amortissement des hautes fréquences")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class EchoAudioInput(BaseSoxActionInput):
    delay_ms: int = Field(default=250, ge=50, le=2000, description="Délai de l'écho en millisecondes")
    decay: float = Field(default=0.4, ge=0.1, le=0.9, description="Atténuation de l'écho (0.4 = 40%)")
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class ChorusAudioInput(BaseSoxActionInput):
    intensity: Literal["subtle", "medium", "heavy"] = "medium"
    output_format: Literal["wav", "flac", "mp3"] = "wav"


class OverdriveAudioInput(BaseSoxActionInput):
    gain_db: int = Field(default=10, ge=1, le=40, description="Niveau de saturation/distorsion harmonique en dB")
    colour: int = Field(default=20, ge=0, le=100, description="Couleur harmonique")
    output_format: Literal["wav", "flac", "mp3"] = "wav"