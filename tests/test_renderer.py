"""Phase 2 renderer tests. Real FFmpeg. No mocks."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from renderer.errors import RenderError
from renderer.render import frame_count, render

MINIMAL = REPO / "tests" / "fixtures" / "valid_minimal_project.json"
UI_MOTION = REPO / "tests" / "fixtures" / "valid_ui_motion_project.json"


def probe(path: Path) -> dict:
    raw = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        text=True,
    )
    return json.loads(raw)


class RendererTests(unittest.TestCase):
    def test_minimal_project_renders_mp4(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.mp4"
            render(MINIMAL, out)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 1000)
            info = probe(out)
            video = next(s for s in info["streams"] if s["codec_type"] == "video")
            self.assertEqual(int(video["width"]), 1080)
            self.assertEqual(int(video["height"]), 1920)
            rate = video.get("r_frame_rate") or video.get("avg_frame_rate")
            num, den = rate.split("/")
            self.assertEqual(round(int(num) / int(den)), 30)
            duration = float(info["format"]["duration"])
            expected = frame_count(15000, 30) / 30
            self.assertAlmostEqual(duration, expected, delta=0.08)
            self.assertEqual(video["codec_name"], "h264")
            self.assertIn("mp4", info["format"]["format_name"])
            self.assertFalse(any(s["codec_type"] == "audio" for s in info["streams"]))

    def test_missing_asset_fails(self):
        project = json.loads(MINIMAL.read_text(encoding="utf-8"))
        project["assets"][0]["uri"] = "asset://examples/does-not-exist.png"
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "missing.json"
            src.write_text(json.dumps(project), encoding="utf-8")
            with self.assertRaises(RenderError) as ctx:
                render(src, Path(tmp) / "out.mp4")
            self.assertIn("Missing asset", str(ctx.exception))

    def test_unsupported_primitive_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RenderError) as ctx:
                render(UI_MOTION, Path(tmp) / "out.mp4")
            self.assertIn("Unsupported primitive", str(ctx.exception))

    def test_repeat_render_same_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.mp4"
            b = Path(tmp) / "b.mp4"
            render(MINIMAL, a)
            render(MINIMAL, b)
            pa, pb = probe(a), probe(b)
            va = next(s for s in pa["streams"] if s["codec_type"] == "video")
            vb = next(s for s in pb["streams"] if s["codec_type"] == "video")
            self.assertEqual((va["width"], va["height"]), (vb["width"], vb["height"]))
            self.assertEqual(va["nb_frames"], vb["nb_frames"])
            self.assertEqual(va["r_frame_rate"], vb["r_frame_rate"])
            self.assertAlmostEqual(float(pa["format"]["duration"]), float(pb["format"]["duration"]), places=2)

    def test_works_from_other_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "cwd.mp4"
            subprocess.run(
                [sys.executable, "-m", "renderer", str(MINIMAL), "-o", str(out)],
                cwd="/tmp",
                check=True,
                env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": str(REPO)},
            )
            self.assertTrue(out.is_file())
            video = next(s for s in probe(out)["streams"] if s["codec_type"] == "video")
            self.assertEqual((int(video["width"]), int(video["height"])), (1080, 1920))


if __name__ == "__main__":
    unittest.main()
