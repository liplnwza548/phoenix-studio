"""Phase 6 zoom_to_region tests."""

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

from renderer.compose import compose_frame, ms_for_frame, zoom_crop
from renderer.errors import RenderError
from renderer.render import frame_count, render
from validator.validate import validate_project

SRC = REPO / "examples" / "phase6_zoom.json"
END = {"x": 0.04, "y": 0.14, "w": 0.46, "h": 0.24}


def probe(path: Path) -> dict:
    return json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            text=True,
        )
    )


class Phase6ZoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = json.loads(SRC.read_text(encoding="utf-8"))
        cls.assets = {a["asset_id"]: a for a in cls.project["assets"]}
        cls.layer = cls.project["scenes"][0]["layers"][0]
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "phase6.mp4"
        render(SRC, cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_plan_valid(self):
        self.assertTrue(validate_project(self.project)["valid"])

    def test_zoom_inactive_before_start(self):
        self.assertIsNone(zoom_crop(self.layer, 599))

    def test_zoom_start_is_full_frame(self):
        box = zoom_crop(self.layer, 600)
        self.assertAlmostEqual(box["x"], 0.0, places=3)
        self.assertAlmostEqual(box["w"], 1.0, places=3)

    def test_zoom_mid_interpolates(self):
        box = zoom_crop(self.layer, 1050)
        self.assertGreater(box["x"], 0.0)
        self.assertLess(box["x"], END["x"])
        self.assertLess(box["w"], 1.0)
        self.assertGreater(box["w"], END["w"])

    def test_zoom_holds_after_end(self):
        box = zoom_crop(self.layer, 2000)
        self.assertAlmostEqual(box["x"], END["x"], places=4)
        self.assertAlmostEqual(box["w"], END["w"], places=4)

    def test_timing_boundaries(self):
        self.assertEqual(ms_for_frame(18, 30), 600)
        self.assertIsNone(zoom_crop(self.layer, ms_for_frame(17, 30)))
        self.assertIsNotNone(zoom_crop(self.layer, ms_for_frame(18, 30)))

    def test_ui_number_survives_zoom(self):
        late = compose_frame(self.project, self.assets, SRC, 2000)
        bright = 0
        for y in range(200, 900, 20):
            for x in range(80, 1000, 20):
                r, g, b = late.getpixel((x, y))
                if r > 180 and g > 180 and b > 180:
                    bright += 1
        self.assertGreater(bright, 5)

    def test_mp4_structure(self):
        info = probe(self.out)
        video = next(s for s in info["streams"] if s["codec_type"] == "video")
        self.assertEqual((int(video["width"]), int(video["height"])), (1080, 1920))
        num, den = video["r_frame_rate"].split("/")
        self.assertEqual(round(int(num) / int(den)), 30)
        self.assertAlmostEqual(float(info["format"]["duration"]), frame_count(2800, 30) / 30, delta=0.12)

    def test_missing_target_fails(self):
        bad = copy.deepcopy(self.project)
        for p in bad["scenes"][0]["layers"][0]["primitives"]:
            if p["type"] == "zoom_to_region":
                del p["target"]
        self.assertFalse(validate_project(bad)["valid"])

    def test_repeat_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.mp4", Path(tmp) / "b.mp4"
            render(SRC, a)
            render(SRC, b)
            pa, pb = probe(a), probe(b)
            va = next(s for s in pa["streams"] if s["codec_type"] == "video")
            vb = next(s for s in pb["streams"] if s["codec_type"] == "video")
            self.assertEqual((va["width"], va["height"], va["r_frame_rate"]), (vb["width"], vb["height"], vb["r_frame_rate"]))

    def test_unsupported_still_fails(self):
        bad = copy.deepcopy(self.project)
        bad["scenes"][0]["layers"][0]["primitives"].append(
            {"type": "fade", "start_ms": 0, "duration_ms": 200, "easing": "linear"}
        )
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bad.json"
            src.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(RenderError):
                render(src, Path(tmp) / "x.mp4")


if __name__ == "__main__":
    unittest.main()
