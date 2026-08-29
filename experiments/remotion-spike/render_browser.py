#!/usr/bin/env python3
"""Browser-model spike renderer. Reads the same semantic JSON. Not the production renderer."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CHROME = shutil.which("google-chrome") or shutil.which("google-chrome-stable")


def render(project_path: Path, output_path: Path) -> Path:
    project = json.loads(Path(project_path).read_text(encoding="utf-8"))
    html = (HERE / "compose.html").read_text(encoding="utf-8")
    injected = html.replace(
        "const PLAN = window.__PLAN__;",
        "const PLAN = " + json.dumps(project, ensure_ascii=False) + ";",
    )
    fps = int(project["fps"])
    duration_ms = int(project["duration_ms"])
    frames = max(1, duration_ms * fps // 1000)
    if not CHROME:
        raise SystemExit("google-chrome not found")
    tmp = Path(tempfile.mkdtemp(prefix="rspike_"))
    try:
        page = tmp / "compose.html"
        page.write_text(injected, encoding="utf-8")
        shutil.copy(HERE / "ui-console.png", tmp / "ui-console.png")
        for i in range(frames):
            t = i * 1000 // fps
            dest = tmp / f"f{i:05d}.png"
            url = page.as_uri() + f"?t={t}"
            subprocess.run(
                [
                    CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--no-sandbox", f"--window-size={project['width']},{project['height']}",
                    f"--screenshot={dest}", url,
                ],
                check=True, capture_output=True,
            )
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-framerate", str(fps), "-i", str(tmp / "f%05d.png"),
                "-frames:v", str(frames), "-r", str(fps), "-an",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                str(output_path),
            ],
            check=True,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return output_path


if __name__ == "__main__":
    import sys
    src = Path(sys.argv[1] if len(sys.argv) > 1 else REPO / "examples/phase5_benchmark.json")
    out = Path(sys.argv[2] if len(sys.argv) > 2 else HERE / "remotion-render.mp4")
    print(render(src, out))
