"""Probe and mux USER_VOICE. FFmpeg stays inside this module."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from renderer.assets import resolve_uri
from renderer.errors import RenderError

VOICE_ROLES = frozenset({"voice"})


def probe_audio(path: Path) -> dict:
    if not path.is_file():
        raise RenderError(f"Missing audio file: {path}")
    raw = subprocess.check_output(
        [
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", str(path),
        ],
        text=True,
    )
    info = json.loads(raw)
    stream = next((s for s in info.get("streams") or [] if s.get("codec_type") == "audio"), None)
    if stream is None:
        raise RenderError(f"No audio stream in {path}")
    duration_s = float(stream.get("duration") or info.get("format", {}).get("duration") or 0)
    return {
        "path": path,
        "codec": stream.get("codec_name"),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "channels": int(stream.get("channels") or 0),
        "duration_ms": int(round(duration_s * 1000)),
    }


def voice_tracks(project: dict) -> list[dict]:
    audio = project.get("audio") or {}
    tracks = audio.get("tracks") or []
    return [t for t in tracks if t.get("role") == "voice"]


def require_audio_file(asset: dict, project_path: Path) -> Path:
    if asset.get("kind") != "audio":
        raise RenderError(f"Audio track asset kind must be audio, got '{asset.get('kind')}'.")
    path = resolve_uri(asset.get("uri", ""), project_path)
    if not path.is_file():
        raise RenderError(f"Missing audio file: {path}")
    return path


def mux_user_voice(video_path: Path, project: dict, assets: dict, project_path: Path, output_path: Path) -> Path:
    """Place user voice onto a finished silent video. Video duration is authority."""
    tracks = voice_tracks(project)
    if not tracks:
        raise RenderError("mux_user_voice called with no voice tracks.")
    if len(tracks) > 1:
        raise RenderError("Phase 5 supports one USER_VOICE track.")
    track = tracks[0]
    asset = assets[track["asset_id"]]
    src = require_audio_file(asset, project_path)
    meta = probe_audio(src)
    video_ms = int(project["duration_ms"])
    start_ms = int(track["start_ms"])
    src_start = int(track.get("source_start_ms") or 0)
    src_end = track.get("source_end_ms")

    filters = []
    if src_start > 0 or src_end is not None:
        if src_end is None:
            filters.append(f"atrim=start={src_start/1000}")
        else:
            filters.append(f"atrim=start={src_start/1000}:end={int(src_end)/1000}")
        filters.append("asetpts=PTS-STARTPTS")
    if start_ms > 0:
        filters.append(f"adelay={start_ms}|{start_ms}")
    filters.append("apad")
    filters.append(f"atrim=0:{video_ms/1000}")
    filters.append("asetpts=PTS-STARTPTS")
    _ = meta
    afilter = ",".join(filters)
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video_path),
        "-i", str(src),
        "-filter_complex", f"[1:a]{afilter}[a]",
        "-map", "0:v",
        "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "48000",
        "-ac", "2",
        "-movflags", "+faststart",
        str(output_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()[-400:]
        raise RenderError(f"Audio mux failed: {detail or exc}") from exc
    return output_path
