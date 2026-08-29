"""Layered still renderer. FFmpeg stays inside this module."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from renderer.audio import mux_user_voice, voice_tracks
from renderer.compose import SUPPORTED, compose_frame, ms_for_frame
from renderer.errors import RenderError

REPO_ROOT = Path(__file__).resolve().parent.parent


def render(project_path: Path | str, output_path: Path | str) -> Path:
    project_path = Path(project_path).resolve()
    output_path = Path(output_path).resolve()
    if not project_path.is_file():
        raise RenderError(f"Missing project: {project_path}")

    from validator.validate import validate_path

    verdict = validate_path(project_path)
    if not verdict["valid"]:
        first = verdict["errors"][0]
        raise RenderError(
            f"Invalid project [{first['layer']} {first['code']}] {first['path']}: {first['message']}"
        )

    project = json.loads(project_path.read_text(encoding="utf-8"))
    _assert_supported(project)
    assets = {a["asset_id"]: a for a in project["assets"]}
    fps = int(project["fps"])
    duration_ms = int(project["duration_ms"])
    frames = frame_count(duration_ms, fps)

    if shutil.which("ffmpeg") is None:
        raise RenderError("ffmpeg is not on PATH.")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cuts = _change_times(project, duration_ms, fps)
    tmp = Path(tempfile.mkdtemp(prefix="pstudio_"))
    try:
        # One PNG per output frame, keyed by compositor time
        # t = frame_index * 1000 // fps
        # Concat-demuxer durations drift by ~1 frame around cuts.
        baked = {}
        for i in range(frames):
            t = ms_for_frame(i, fps)
            key = _interval_start(cuts, t)
            if key not in baked:
                baked[key] = compose_frame(project, assets, project_path, t)
            baked[key].save(tmp / f"f{i:05d}.png")
        silent = tmp / "silent.mp4"
        dest = silent if voice_tracks(project) else output_path
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-framerate", str(fps),
            "-i", str(tmp / "f%05d.png"),
            "-frames:v", str(frames),
            "-r", str(fps),
            "-an",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(dest),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()[-400:]
            raise RenderError(f"FFmpeg failed: {detail or exc}") from exc
        if voice_tracks(project):
            mux_user_voice(silent, project, assets, project_path, output_path)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RenderError(f"Renderer produced no file: {output_path}")
    return output_path


def frame_count(duration_ms: int, fps: int) -> int:
    """Floor: frames = duration_ms * fps // 1000. Minimum 1."""
    return max(1, (duration_ms * fps) // 1000)


def _change_times(project: dict, duration_ms: int, fps: int = 30) -> list[int]:
    marks = {0, duration_ms}
    for scene in project.get("scenes") or []:
        s0 = int(scene["start_ms"])
        marks.add(s0)
        marks.add(s0 + int(scene["duration_ms"]))
        for layer in scene.get("layers") or []:
            vis = layer.get("visibility") or {}
            marks.add(s0 + int(vis.get("from_ms", 0)))
            if "to_ms" in vis:
                marks.add(s0 + int(vis["to_ms"]))
            for prim in layer.get("primitives") or []:
                ps = int(prim["start_ms"])
                marks.add(s0 + ps)
                marks.add(s0 + ps + int(prim["duration_ms"]))
                ptype = prim.get("type")
                if ptype == "kinetic_text":
                    fade_ms = int((prim.get("params") or {}).get("fade_ms", 200))
                    for step in range(0, max(fade_ms, 0) + 1, 50):
                        marks.add(s0 + ps + step)
                if ptype in {"cursor_move", "cursor_click", "zoom_to_region", "pan_to_region"}:
                    step = max(1, 1000 // fps)
                    end = ps + int(prim["duration_ms"])
                    for mark in range(ps, end + 1, step):
                        marks.add(s0 + mark)
    return sorted(t for t in marks if 0 <= t <= duration_ms)


def _interval_start(cuts: list[int], t: int) -> int:
    start = 0
    for c in cuts:
        if c <= t:
            start = c
        else:
            break
    return start


def _assert_supported(project: dict) -> None:
    for scene in project.get("scenes") or []:
        for layer in scene.get("layers") or []:
            for prim in layer.get("primitives") or []:
                ptype = prim.get("type")
                if ptype not in SUPPORTED:
                    raise RenderError(
                        f"Unsupported primitive '{ptype}'. "
                        "Phase 7 supports hold, crop_9_16, highlight_box, spotlight_dim, kinetic_text, cursor_move, cursor_click, zoom_to_region, pan_to_region."
                    )
