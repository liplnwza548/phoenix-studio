"""Phase 7 pan_to_region tests. Does not change Phase 5/6 timing."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from renderer.compose import compose_frame, ms_for_frame, pan_crop, zoom_crop
from renderer.errors import RenderError
from renderer.render import frame_count, render
from validator.validate import validate_project

SRC = REPO / "examples" / "phase7_pan.json"
ZOOM = REPO / "examples" / "phase6_zoom.json"
START = {"x": 0.02, "y": 0.14, "w": 0.48, "h": 0.28}
END = {"x": 0.50, "y": 0.14, "w": 0.48, "h": 0.28}


def probe(path: Path) -> dict:
    return json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            text=True,
        )
    )


class Phase7PanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = json.loads(SRC.read_text(encoding="utf-8"))
        cls.assets = {a["asset_id"]: a for a in cls.project["assets"]}
        cls.layer = cls.project["scenes"][0]["layers"][0]
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "phase7.mp4"
        render(SRC, cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_plan_valid(self):
        self.assertTrue(validate_project(self.project)["valid"])

    def test_pre_pan_static(self):
        self.assertIsNone(pan_crop(self.layer, 599))
        self.assertEqual(ms_for_frame(17, 30), 566)
        self.assertIsNone(pan_crop(self.layer, ms_for_frame(17, 30)))

    def test_pan_start(self):
        self.assertEqual(ms_for_frame(18, 30), 600)
        box = pan_crop(self.layer, 600)
        self.assertAlmostEqual(box["x"], START["x"], places=4)
        self.assertAlmostEqual(box["y"], START["y"], places=4)
        self.assertAlmostEqual(box["w"], START["w"], places=4)
        self.assertAlmostEqual(box["h"], START["h"], places=4)

    def test_midpoint_translates_not_scales(self):
        box = pan_crop(self.layer, 1050)
        self.assertGreater(box["x"], START["x"])
        self.assertLess(box["x"], END["x"])
        self.assertAlmostEqual(box["w"], START["w"], places=4)
        self.assertAlmostEqual(box["h"], START["h"], places=4)
        self.assertAlmostEqual(box["y"], START["y"], places=4)

    def test_pan_end(self):
        box = pan_crop(self.layer, 1499)
        self.assertGreater(box["x"], START["x"])
        self.assertAlmostEqual(box["w"], START["w"], places=4)

    def test_hold_after_pan(self):
        box = pan_crop(self.layer, 2000)
        self.assertAlmostEqual(box["x"], END["x"], places=4)
        self.assertAlmostEqual(box["y"], END["y"], places=4)
        self.assertAlmostEqual(box["w"], END["w"], places=4)

    def test_phase6_zoom_untouched(self):
        zoom_proj = json.loads(ZOOM.read_text(encoding="utf-8"))
        layer = zoom_proj["scenes"][0]["layers"][0]
        self.assertIsNone(zoom_crop(layer, 599))
        start = zoom_crop(layer, 600)
        self.assertAlmostEqual(start["w"], 1.0, places=3)
        held = zoom_crop(layer, 2000)
        self.assertAlmostEqual(held["x"], 0.04, places=4)
        self.assertAlmostEqual(held["w"], 0.46, places=4)

    def test_mp4_structure(self):
        info = probe(self.out)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        self.assertEqual((int(video["width"]), int(video["height"])), (1080, 1920))
        num, den = video["r_frame_rate"].split("/")
        self.assertEqual(round(int(num) / int(den)), 30)
        self.assertAlmostEqual(float(info["format"]["duration"]), frame_count(2800, 30) / 30, delta=0.12)

    def test_repeat_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.mp4", Path(tmp) / "b.mp4"
            render(SRC, a)
            render(SRC, b)
            pa, pb = probe(a), probe(b)
            va = next(s for s in pa["streams"] if s["codec_type"] == "video")
            vb = next(s for s in pb["streams"] if s["codec_type"] == "video")
            self.assertEqual((va["width"], va["height"], va["r_frame_rate"]), (vb["width"], vb["height"], vb["r_frame_rate"]))

    def test_missing_from_fails_render(self):
        bad = copy.deepcopy(self.project)
        for p in bad["scenes"][0]["layers"][0]["primitives"]:
            if p["type"] == "pan_to_region":
                p["params"] = {}
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bad.json"
            src.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(RenderError):
                render(src, Path(tmp) / "x.mp4")
