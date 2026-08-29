# Architecture — Phoenix Studio v0.1

Phoenix-Cut is ancestry, not a template to copy.
This system makes SaaS / UI / launch videos by separating thought from pixels.

## Canonical pipeline

```
AI Director
    → Structured Plan          (project JSON)
    → Validation               (schema + refs + time + truth)
    → Timeline DSL             (scenes / layers / primitives)
    → Deterministic Renderer   (Phase 1+, not in this tree)
    → QC                       (inspect the MP4)
    → MP4
```

Director writes a plan.
Renderer reads the plan.
Neither writes the other's language.

## Canonical project model

A project is one JSON object that declares:

| Field | Role |
|---|---|
| `project_id` | Stable id |
| `schema_version` | Contract version. V1 = `"0.1"` |
| `width` `height` `fps` | Composition canvas |
| `duration_ms` | Timeline length, integer ms |
| `assets` | All media + provenance + truth_level |
| `scenes` | The Timeline DSL |
| `audio` | Voice / music / sfx bindings |
| `output` | Container intent, not engine flags |

The project **is** the structured plan.
There is no second hidden graph.

## Two layers of meaning

```
Truth Layer        product UI, price, metrics, names, claims, logos, workflows
Atmosphere Layer   B-roll, mood, metaphor, environment, visual bridges
```

An asset carries `truth_level`.
A layer carries `band` = `TRUTH` or `ATMOSPHERE`.
Validation refuses an `AI_GENERATED` or `FICTIONAL` asset on a `TRUTH` band.
See `TRUTH_RULES.md`.

## Renderer boundary

Inside the DSL:

```json
{ "type": "zoom_to_region", "start_ms": 0, "duration_ms": 800, "target": { "x": 0.1, "y": 0.2, "w": 0.4, "h": 0.2 } }
```

Outside the DSL (forbidden here):

```
ffmpeg -vf "zoompan=..."
```

The renderer may be FFmpeg, SVG frames, a future compositor, or something else.
The DSL does not know.

Boundary rule: if a field only makes sense to one engine, it does not belong in the DSL.

## Time

Canonical unit: **integer milliseconds**.

- `start_ms`
- `duration_ms`

No floating-point seconds in contracts.
Conversion from `mm:ss.s` is a Director convenience and must be resolved before the plan is valid.

## Space

Normalized project coordinates:

- `x`, `y`, `w`, `h` in `0..1`
- origin: **top-left**
- `x` rightward, `y` downward

Pixel mapping is renderer work:
`px = round(norm * canvas)`.

## Overlap

Layer overlap is normal:

```
product UI
 + highlight
 + cursor
 + kinetic text
```

Illegal overlap is a **track conflict**, not "two things occupy pixels".
V1 conflict = two items share the same `exclusive_track` and their time ranges intersect.
Scenes themselves do not overlap. They tile `[0, duration_ms)`.

## Provenance versus truth

Do not store "this is real" in one field.

| Concern | Fields |
|---|---|
| Where it came from | `source`, `source_type`, `captured_at` |
| Whether a human/system accepted it | `verified` |
| How far it may stand in for the product | `truth_level` |

`verified: true` does not upgrade `AI_GENERATED` into product truth.

## Determinism plan (for later phases)

A plan plus pinned assets plus schema_version must yield the same timeline decisions.
Renderer determinism is a later proof (same command, same frames).
Phase 0 makes that proof possible by banning engine-specific drift in the plan.

Fixtures in `tests/fixtures/` are the seed of that proof.
Valid fixtures must keep passing.
Invalid fixtures must keep failing for the named reason.

## What validation guarantees

The plan is well-typed, referenced, timed, and truth-banded.
It does **not** guarantee the MP4 looks good or matches the brief.

## What QC guarantees (later)

The file exists and matches declared canvas / duration / audio presence.
It does **not** rewrite the plan.

Open decisions live in `OPEN_QUESTIONS.md`. They are not silent.

## Phase map

| Phase | Ships |
|---|---|
| 0 | Contracts, schemas, fixtures |
| 1 | Validator only (no pixels) |
| 2 | Still image + hold + crop_9_16 → MP4 |
| 3 | Multi-layer UI + highlight_box + spotlight_dim + kinetic_text |
| 4 (this) | cursor_move + cursor_click overlay |
| 5 | USER_VOICE mux |
| 6 | zoom_to_region |
| 7 (this) | pan_to_region |
| 8 | Next smallest: music bed or fade, not both |
