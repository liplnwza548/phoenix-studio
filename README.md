# Phoenix Studio

Evolution of Phoenix-Cut. Deterministic 9:16 renderer.

```
AI Director → Structured Plan → Validation → Timeline DSL → Deterministic Renderer → QC → MP4
```

Rule: **AI thinks. Renderer obeys.**
The Timeline DSL never contains FFmpeg, SVG filters, or engine calls.

## Status (Phase 5A–8)

Phase 0: documents, JSON Schemas, examples, fixtures.
Phase 1: deterministic plan validator.
Phase 2: still-image renderer → MP4.
Phase 3: layered UI + highlight + spotlight + kinetic text.
Phase 4: cursor_move + cursor_click.
Phase 5: USER_VOICE mux.
Phase 5A: visual timing audit locked.
Phase 6: zoom_to_region.
Phase 7: pan_to_region.
Phase 8: zoom_to_region then pan_to_region composition.

```text
python -m validator examples/minimal_project.json
python -m validator --json tests/fixtures/invalid_missing_asset.json
python /path/to/phoenix-studio/validate --json plan.json
python -m renderer examples/minimal_project.json -o /tmp/minimal.mp4
```

Install: `pip install -r requirements.txt` (`jsonschema` only).

## Camera Engine

- `zoom_to_region` changes crop scale toward a target.
- `pan_to_region` translates a fixed-size crop.
- `camera_crop` composes zoom then pan without resetting scale.
- Overlays stay in canvas space and do not follow the camera.

## JSON → MP4

Validated project JSON + local assets → PIL compose → FFmpeg encode/mux.

## QA protocol

Frame index timing: `t = frame_index * 1000 // fps`.
Regression: `python3 -m unittest tests.test_renderer_phase8 tests.test_renderer_phase7 tests.test_renderer_phase6 tests.test_timing_audit tests.test_validator -v`

## Read first

1. `references/ARCHITECTURE.md`
2. `references/TIMELINE_CONTRACT.md`
3. `references/ASSET_CONTRACT.md`
4. `references/MOTION_CONTRACT.md`
5. `references/VALIDATION_CONTRACT.md`
6. `references/TRUTH_RULES.md`
7. `SKILL.md`

## Layout

```
schemas/           machine contracts (JSON Schema)
validator/         Phase 1 plan checker
renderer/          deterministic MP4 renderer
examples/          valid projects a human can read
tests/             fixtures + unittest
references/        human contracts
```

Recommended V1 output: `1080×1920`, `9:16`, integer milliseconds on the timeline.

## What this repo is not

Not Phoenix-Cut copied forward.
Not an FFmpeg wrapper.
Not a Flow/Veo client.
Not a mobile editor.
