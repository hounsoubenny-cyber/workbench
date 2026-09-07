#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep  3 23:23:57 2026

@author: hounsousamuel
"""

"""
Workbench Mediakit — Actions FFmpeg : Traitement Audio au sein de la Vidéo.
Ce fichier gère le son à l'intérieur de la vidéo : couper le son, amplifier le volume, 
normaliser selon les standards YouTube/Broadcast (EBU R128), fondus audio, 
correction de désynchronisation, remplacement de la bande-son et ajout d'une musique d'ambiance.
"""

from workbench.specs.registry import collect_specs
from workbench.core.subprocess.wb_subprocess_types import (
    PathArg, EnumArg, PatternArg, BoolArg
)
from workbench.products.mediakit.specs.ffmpeg.base_spec import FfmpegSpec
from workbench.products.mediakit.specs.ffmpeg.base_model import (
    MuteVideoInput, BoostVolumeInput, NormalizeLoudnessInput,
    AudioFadeInput, FixAudioDelayInput, ReplaceAudioInput, AddBackgroundMusicInput
)

MIN_FFMPEG_VERSION = (4, 0)


# ─── 1. SUPPRIMER LE SON (MUTE) ──────────────────────────────────────────────
mute_video_spec = FfmpegSpec[MuteVideoInput](
    id="ffmpeg_mute_video",
    label="Supprimer complètement la piste sonore d'une vidéo",
    input_cls=MuteVideoInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="muted.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        BoolArg(flag="-an", value=True),
        EnumArg(flag="-c:v", value="copy", enum_values=["copy"]),
        PathArg(value="muted.mp4")
    ]
)


# ─── 2. AJUSTER / AMPLIFIER LE VOLUME ────────────────────────────────────────
boost_volume_spec = FfmpegSpec[BoostVolumeInput](
    id="ffmpeg_boost_volume",
    label="Ajuster le volume sonore (amplifier ou atténuer le gain)",
    input_cls=BoostVolumeInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="volume_adjusted.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-filter:a", value=f"volume={u.volume_multiplier}"),
        EnumArg(flag="-c:v", value="copy", enum_values=["copy"]),
        PathArg(value="volume_adjusted.mp4")
    ]
)


# ─── 3. NORMALISATION DU VOLUME (EBU R128 LOUDNORM) ──────────────────────────
normalize_loudness_spec = FfmpegSpec[NormalizeLoudnessInput](
    id="ffmpeg_normalize_loudness",
    label="Normaliser la puissance sonore (standard YouTube / Spotify à -16 LUFS)",
    input_cls=NormalizeLoudnessInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="normalized_audio.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-filter:a", value=f"loudnorm=I={u.target_lufs}:LRA=11:TP=-1.5"),
        EnumArg(flag="-c:v", value="copy", enum_values=["copy"]),
        PathArg(value="normalized_audio.mp4")
    ]
)


# ─── 4. FONDUS AUDIO ENTRANT ET SORTANT (FADE IN / OUT) ──────────────────────
def _build_audio_fade_filter(u: AudioFadeInput) -> str:
    # Si fade_out est demandé, l'astuce areverse applique le fade-out sur la fin
    # sans avoir besoin de connaître la durée totale du fichier
    if u.fade_out_s > 0:
        return f"afade=t=in:ss=0:d={u.fade_in_s},areverse,afade=t=in:ss=0:d={u.fade_out_s},areverse"
    return f"afade=t=in:ss=0:d={u.fade_in_s}"


audio_fade_spec = FfmpegSpec[AudioFadeInput](
    id="ffmpeg_audio_fade",
    label="Ajouter un fondu sonore progressif au début et à la fin",
    input_cls=AudioFadeInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="audio_faded.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-filter:a", value=_build_audio_fade_filter(u)),
        EnumArg(flag="-c:v", value="copy", enum_values=["copy"]),
        PathArg(value="audio_faded.mp4")
    ]
)


# ─── 5. CORRIGER LA DÉSYNCHRONISATION SON / IMAGE ────────────────────────────
fix_audio_delay_spec = FfmpegSpec[FixAudioDelayInput](
    id="ffmpeg_fix_audio_delay",
    label="Corriger un décalage entre la voix et l'image (avance/retard en ms)",
    input_cls=FixAudioDelayInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="audio_synced.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PatternArg(flag="-filter:a", value=f"adelay={u.delay_ms}|{u.delay_ms}"),
        EnumArg(flag="-c:v", value="copy", enum_values=["copy"]),
        PathArg(value="audio_synced.mp4")
    ]
)


# ─── 6. REMPLACER LA BANDE SON PAR UN AUTRE FICHIER ──────────────────────────
replace_audio_spec = FfmpegSpec[ReplaceAudioInput](
    id="ffmpeg_replace_audio",
    label="Remplacer complètement la bande-son par un nouveau fichier audio",
    input_cls=ReplaceAudioInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="audio_replaced.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PathArg(flag="-i", value=u.new_audio_file, must_exist=True),
        PatternArg(flag="-map", value="0:v:0"),
        PatternArg(flag="-map", value="1:a:0"),
        EnumArg(flag="-c:v", value="copy", enum_values=["copy"]),
        EnumArg(flag="-c:a", value="aac", enum_values=["aac"]),
        BoolArg(flag="-shortest", value=True),
        PathArg(value="audio_replaced.mp4")
    ]
)


# ─── 7. AJOUTER UNE MUSIQUE D'AMBIANCE DE FOND (MIXAGE) ──────────────────────
add_background_music_spec = FfmpegSpec[AddBackgroundMusicInput](
    id="ffmpeg_add_background_music",
    label="Ajouter une musique de fond par-dessus la voix existante",
    input_cls=AddBackgroundMusicInput,
    validate_arg=True,
    min_version=MIN_FFMPEG_VERSION,
    output_filename_template="music_mixed.mp4",
    build_args=lambda u: [
        PathArg(flag="-i", value=u.input_file, must_exist=True),
        PathArg(flag="-i", value=u.music_file, must_exist=True),
        PatternArg(
            flag="-filter_complex",
            value=f"[1:a]volume={u.music_volume}[bg];[0:a][bg]amix=inputs=2:duration=first[aout]"
        ),
        PatternArg(flag="-map", value="0:v"),
        PatternArg(flag="-map", value="[aout]"),
        EnumArg(flag="-c:v", value="copy", enum_values=["copy"]),
        EnumArg(flag="-c:a", value="aac", enum_values=["aac"]),
        PathArg(value="music_mixed.mp4")
    ]
)


# =============================================================================
# COLLECTE AUTOMATIQUE DU MODULE
# =============================================================================
FFMPEG_AUDIO_ACTIONS = collect_specs(__name__)
__all__ = ["FFMPEG_AUDIO_ACTIONS"]