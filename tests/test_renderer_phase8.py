"""Phase 8 zoom then pan composition. Phase 6/7 primitives unchanged."""

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

from renderer.compose import camera_crop, ms_for_frame, pan_crop, zoom_crop
from renderer.render import frame_count, render
from validator.validate import validate_project

SRC = REPO / "examples" / "phase8_zoom_pan.json"
A0 = {"x": 0.02, "y": 0.14, "w": 0.48, "h": 0.28}
A1 = {"x": 0.04, "y": 0.16, "w": 0.36, "h": 0.20}
B1 = {"x": 0.54, "y": 0.16, "w": 0.36, "h": 0.20}


def probe(path: Path) -> dict:
    return json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            text=True,
        )
    )


class Phase8ZoomPanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = json.loads(SRC.read_text(encoding="utf-8"))
        cls.layer = cls.project["scenes"][0]["layers"][0]
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "phase8.mp4"
        render(SRC, cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_plan_valid(self):
        self.assertTrue(validate_project(self.project)["valid"])

    def test_pre_zoom(self):
        self.assertIsNone(zoom_crop(self.layer, 599))
        self.assertIsNone(camera_crop(self.layer, ms_for_frame(17, 30)))

    def test_zoom_start(self):
        self.assertEqual(ms_for_frame(18, 30), 600)
        box = camera_crop(self.layer, 600)
        self.assertAlmostEqual(box["w"], A0["w"], places=4)
        self.assertAlmostEqual(box["x"], A0["x"], places=4)

    def test_zoom_end(self):
        self.assertEqual(ms_for_frame(44, 30), 1466)
        pre = camera_crop(self.layer, 1499)
        self.assertLess(pre["w"], A0["w"])
        self.assertGreater(pre["w"], A1["w"] - 0.002)

    def test_pan_starts_after_zoom(self):
        self.assertIsNone(pan_crop(self.layer, 1499))
        self.assertEqual(ms_for_frame(45, 30), 1500)
        z = zoom_crop(self.layer, 1500)
        p = pan_crop(self.layer, 1500)
        c = camera_crop(self.layer, 1500)
        self.assertAlmostEqual(z["w"], A1["w"], places=4)
        self.assertAlmostEqual(p["w"], A1["w"], places=4)
        self.assertAlmostEqual(p["x"], A1["x"], places=4)
        self.assertAlmostEqual(c["x"], p["x"], places=4)
        self.assertAlmostEqual(c["w"], z["w"], places=4)

    def test_no_snap_at_1500(self):
        a = camera_crop(self.layer, 1499)
        b = camera_crop(self.layer, 1500)
        self.assertAlmostEqual(a["w"], b["w"], places=3)
        self.assertAlmostEqual(a["h"], b["h"], places=3)
        self.assertLess(abs(a["x"] - b["x"]), 0.01)
        self.assertLess(abs(a["y"] - b["y"]), 0.01)

    def test_pan_mid_translates_same_scale(self):
        mid = camera_crop(self.layer, ms_for_frame(60, 30))
        self.assertGreater(mid["x"], A1["x"])
        self.assertLess(mid["x"], B1["x"])
        self.assertAlmostEqual(mid["w"], A1["w"], places=4)
        self.assertAlmostEqual(mid["h"], A1["h"], places=4)

    def test_pan_end_and_hold(self):
        self.assertEqual(ms_for_frame(69, 30), 2300)
        end = camera_crop(self.layer, 2300)
        hold = camera_crop(self.layer, 2800)
        self.assertAlmostEqual(end["x"], B1["x"], places=4)
        self.assertAlmostEqual(end["w"], A1["w"], places=4)
        self.assertEqual(end, hold)

    def test_mp4(self):
        info = probe(self.out)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        self.assertEqual((int(video["width"]), int(video["height"])), (1080, 1920))
        self.assertEqual(video["r_frame_rate"], "30/1")
        self.assertAlmostEqual(float(info["format"]["duration"]), frame_count(3000, 30) / 30, delta=0.12)

    def test_repeat(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.mp4", Path(tmp) / "b.mp4"
            render(SRC, a)
            render(SRC, b)
            pa, pb = probe(a), probe(b)
            va = next(s for s in pa["streams"] if s["codec_type"] == "video")
            vb = next(s for s in pb["streams"] if s["codec_type"] == "video")
            self.assertEqual((va["width"], va["height"], va["r_frame_rate"]), (vb["width"], vb["height"], vb["r_frame_rate"]))
