# Fixtures

| File | Expected gate | Why it exists |
|---|---|
| `valid_minimal_project.json` | accept | smallest legal plan |
| `valid_ui_motion_project.json` | accept | Truth UI + Atmosphere + primitives |
| `valid_phase3_layers.json` | accept | UI + highlight + spotlight + kinetic text |
| `valid_phase4_cursor.json` | accept | UI + cursor_move + cursor_click |
| `valid_phase5_voice.json` | accept | Phase 4 visuals + USER_VOICE |
| `invalid_unknown_primitive.json` | schema fail | `type` not in V1 enum |
| `invalid_missing_required_field.json` | schema fail | no `project_id` |
| `invalid_negative_duration.json` | schema fail | `duration_ms < 0` |
| `invalid_out_of_bounds.json` | schema fail | `transform.x > 1` |
| `invalid_bad_truth_level.json` | schema fail | `truth_level` not in enum |
| `invalid_missing_asset.json` | contract fail | layer points at missing id |
| `invalid_truth_band_mismatch.json` | contract fail | `TRUTH` layer uses `AI_GENERATED` asset |

Schema-valid but contract-invalid fixtures prove that Phase 1 needs more than JSON Schema.
