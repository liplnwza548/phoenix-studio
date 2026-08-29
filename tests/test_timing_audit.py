"""Frame-index timing audit for examples/phase5_voice.json.

t = frame_index * 1000 // 30
active when start_ms <= t < start_ms + duration_ms
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from renderer.compose import compose_frame, cursor_pos, ms_for_frame

SRC = REPO / "examples" / "phase5_voice.json"
FROM = (0.2593, 0.2135)
TO = (0.1667, 0.4010)


def load():
    project = json.loads(SRC.read_text(encoding="utf-8"))
    assets = {a["asset_id"]: a for a in project["assets"]}
    return project, assets


def without(project: dict, prefix: str) -> dict:
    out = copy.deepcopy(project)
    for layer in out["scenes"][0]["layers"]:
        layer["primitives"] = [p for p in layer["primitives"] if not p["type"].startswith(prefix)]
    return out


def delta_near(full, base, nx, ny, rad=20) -> int:
    x, y = int(round(nx * full.width)), int(round(ny * full.height))
    acc = 0
    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            px, py = x + dx, y + dy
            if 0 <= px < full.width and 0 <= py < full.height:
                if full.getpixel((px, py)) != base.getpixel((px, py)):
                    acc += 1
    return acc


class Phase5VoiceTimingAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project, cls.assets = load()
        cls.noc = without(cls.project, "cursor_")
        cls.notext = without(cls.project, "kinetic_")
        cls.move = next(
            p
            for ly in cls.project["scenes"][0]["layers"]
            for p in ly["primitives"]
            if p["type"] == "cursor_move"
        )

    def frame(self, n: int):
        t = ms_for_frame(n, 30)
        full = compose_frame(self.project, self.assets, SRC, t)
        return t, full

    def test_pre_cursor(self):
        for n in (0, 9, 12, 26):
            t, full = self.frame(n)
            base = compose_frame(self.noc, self.assets, SRC, t)
            self.assertEqual(delta_near(full, base, *FROM), 0, f"cursor leaked at n={n} t={t}")
            self.assertEqual(delta_near(full, base, *TO), 0, f"cursor leaked at n={n} t={t}")

    def test_cursor_start_n27(self):
        self.assertEqual(ms_for_frame(26, 30), 866)
        self.assertEqual(ms_for_frame(27, 30), 900)
        t, full = self.frame(27)
        base = compose_frame(self.noc, self.assets, SRC, t)
        self.assertGreater(delta_near(full, base, *FROM), 20)
        self.assertEqual(cursor_pos(self.move, 900), FROM)

    def test_cursor_moving_n30_n36(self):
        mid = cursor_pos(self.move, ms_for_frame(36, 30))
        self.assertNotAlmostEqual(mid[0], FROM[0], places=3)
        self.assertNotAlmostEqual(mid[0], TO[0], places=3)
        t, full = self.frame(36)
        base = compose_frame(self.noc, self.assets, SRC, t)
        self.assertGreater(delta_near(full, base, *mid), 20)

    def test_click_start_n45(self):
        self.assertEqual(ms_for_frame(45, 30), 1500)
        t, full = self.frame(45)
        base = compose_frame(self.noc, self.assets, SRC, t)
        self.assertGreater(delta_near(full, base, *TO, rad=36), 20)

    def test_click_end_n51(self):
        self.assertEqual(ms_for_frame(51, 30), 1700)
        t, full = self.frame(51)
        base = compose_frame(self.noc, self.assets, SRC, t)
        self.assertEqual(delta_near(full, base, *TO, rad=36), 0)

    def test_kinetic_at_n51(self):
        t, full = self.frame(51)
        base = compose_frame(self.notext, self.assets, SRC, t)
        acc = sum(1 for a, b in zip(full.getdata(), base.getdata()) if a != b)
        self.assertGreater(acc, 100)


if __name__ == "__main__":
    unittest.main()
