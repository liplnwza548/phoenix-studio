"""Phase 1 validator tests. Stdlib unittest only."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from validator.validate import validate_path, validate_project

FIXTURES = REPO / "tests" / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FixtureTests(unittest.TestCase):
    def test_valid_minimal_project(self):
        result = validate_path(FIXTURES / "valid_minimal_project.json")
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["errors"], [])

    def test_valid_ui_motion_project(self):
        result = validate_path(FIXTURES / "valid_ui_motion_project.json")
        self.assertTrue(result["valid"], result)
        self.assertEqual(result["errors"], [])

    def test_invalid_unknown_primitive_schema(self):
        result = validate_path(FIXTURES / "invalid_unknown_primitive.json")
        self.assertFalse(result["valid"])
        self.assertTrue(any(e["layer"] == "SCHEMA" and e["code"] == "SCHEMA_ERROR" for e in result["errors"]))
        self.assertTrue(any("zoompan" in e["message"] or "hold" in e["message"] or "enum" in e["message"].lower() or "not one of" in e["message"].lower() for e in result["errors"]))

    def test_invalid_missing_required_field_schema(self):
        result = validate_path(FIXTURES / "invalid_missing_required_field.json")
        self.assertFalse(result["valid"])
        self.assertTrue(any(e["layer"] == "SCHEMA" for e in result["errors"]))
        self.assertTrue(any("project_id" in e["message"] for e in result["errors"]))

    def test_invalid_negative_duration_caught(self):
        # Phase 0 schema already rejects duration_ms < 1, so SCHEMA fires first.
        result = validate_path(FIXTURES / "invalid_negative_duration.json")
        self.assertFalse(result["valid"])
        layers = {e["layer"] for e in result["errors"]}
        self.assertTrue("SCHEMA" in layers or "TIMELINE" in layers)
        self.assertTrue(
            any(e["code"] in {"SCHEMA_ERROR", "DURATION_NON_POSITIVE"} for e in result["errors"])
        )

    def test_invalid_out_of_bounds_schema_or_geometry(self):
        result = validate_path(FIXTURES / "invalid_out_of_bounds.json")
        self.assertFalse(result["valid"])
        layers = {e["layer"] for e in result["errors"]}
        self.assertTrue("SCHEMA" in layers or "GEOMETRY" in layers)

    def test_invalid_bad_truth_level_schema(self):
        result = validate_path(FIXTURES / "invalid_bad_truth_level.json")
        self.assertFalse(result["valid"])
        self.assertTrue(any(e["layer"] == "SCHEMA" for e in result["errors"]))

    def test_invalid_missing_asset_reference(self):
        result = validate_path(FIXTURES / "invalid_missing_asset.json")
        self.assertFalse(result["valid"])
        hits = [e for e in result["errors"] if e["code"] == "MISSING_ASSET"]
        self.assertTrue(hits, result["errors"])
        self.assertEqual(hits[0]["layer"], "REFERENCE")
        self.assertIn("does-not-exist", hits[0]["message"])

    def test_invalid_truth_band_mismatch(self):
        result = validate_path(FIXTURES / "invalid_truth_band_mismatch.json")
        self.assertFalse(result["valid"])
        hits = [e for e in result["errors"] if e["code"] == "TRUTH_BAND_MISMATCH"]
        self.assertTrue(hits, result["errors"])
        self.assertEqual(hits[0]["layer"], "TRUTH")


class OverlapAndDeterminismTests(unittest.TestCase):
    def test_legitimate_layer_overlap_remains_valid(self):
        project = load("valid_ui_motion_project.json")
        scene = next(s for s in project["scenes"] if s["scene_id"] == "s-ui")
        ids = {layer["layer_id"] for layer in scene["layers"]}
        self.assertTrue({"l-ui", "l-hi", "l-cursor"} <= ids)
        result = validate_project(project)
        self.assertTrue(result["valid"], result)

    def test_exclusive_track_overlap_fails(self):
        project = load("valid_minimal_project.json")
        layer = project["scenes"][0]["layers"][0]
        extra = copy.deepcopy(layer)
        extra["layer_id"] = "l-ui-2"
        extra["exclusive_track"] = "product-screen"
        layer["exclusive_track"] = "product-screen"
        project["scenes"][0]["layers"].append(extra)
        result = validate_project(project)
        self.assertFalse(result["valid"])
        self.assertTrue(any(e["code"] == "EXCLUSIVE_TRACK_OVERLAP" for e in result["errors"]))

    def test_error_order_is_deterministic(self):
        project = load("invalid_truth_band_mismatch.json")
        # Force a second independent error: missing asset on another layer.
        project["scenes"][0]["layers"][0]["asset_id"] = "ghost"
        first = validate_project(project)
        second = validate_project(copy.deepcopy(project))
        self.assertEqual(first, second)
        codes = [(e["layer"], e["path"], e["code"]) for e in first["errors"]]
        self.assertEqual(codes, sorted(codes, key=lambda t: ({"SCHEMA":0,"REFERENCE":1,"TIMELINE":2,"GEOMETRY":3,"TRUTH":4,"OUTPUT":5}[t[0]], t[1], t[2])))

    def test_repeated_validation_same_result(self):
        path = FIXTURES / "valid_ui_motion_project.json"
        a = validate_path(path)
        b = validate_path(path)
        self.assertEqual(a, b)

    def test_scene_gap_fails_timeline(self):
        project = load("valid_minimal_project.json")
        project["scenes"][0]["duration_ms"] = 10000
        result = validate_project(project)
        self.assertFalse(result["valid"])
        self.assertTrue(any(e["code"] == "SCENE_TILING" and e["layer"] == "TIMELINE" for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
