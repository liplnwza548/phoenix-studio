# Timeline Contract

The Timeline DSL is the list of `scenes` inside a project.
It is renderer-agnostic. It describes *what happens when*, not *how pixels are drawn*.

## Time model

- Unit: integer milliseconds
- Project range: `[0, duration_ms)`
- Every timed object uses `start_ms` + `duration_ms`
- End is exclusive: `end = start_ms + duration_ms`

## Scene

A scene is a contiguous span of the project.

Required:

| Field | Meaning |
|---|---|
| `scene_id` | Unique in the project |
| `start_ms` | Offset on the project timeline |
| `duration_ms` | Explicit length. Never inferred |
| `layers` | Visual stack |
| `cues` | Timed text / emphasis on this scene |

V1 packing rule: scenes tile the project.

- First scene `start_ms` = 0
- Each next scene starts where the previous ends
- Last scene ends at `project.duration_ms`
- Scenes do not overlap
- Gaps are invalid

`shot` is not a separate object in v0.1.
If a Director wants a shot label, put it in `label` (optional string). See open questions.

## Layer

Required:

| Field | Meaning |
|---|---|
| `layer_id` | Unique in the scene |
| `asset_id` | Must exist in `project.assets` |
| `z_index` | Integer. Higher draws above |
| `visibility` | When the layer may draw |
| `transform` | Placement in project coordinates |
| `primitives` | Motion list, may be empty |
| `band` | `TRUTH` or `ATMOSPHERE` |

Optional:

| Field | Meaning |
|---|---|
| `exclusive_track` | If set, two layers sharing it must not overlap in time |
| `label` | Human note. Not interpreted |

`visibility`:

```json
{ "from_ms": 0, "to_ms": 1500 }
```

Times are **scene-local**. `0` is the start of the scene.
`to_ms` omitted means "until scene end".
`from_ms` omitted means `0`.

Empty `primitives` means the layer is a still, placed by `transform`, for its visibility window.

## Transform

V1 fields, all normalized except rotation and opacity:

```json
{
  "x": 0.0,
  "y": 0.0,
  "w": 1.0,
  "h": 1.0,
  "rotation_deg": 0,
  "opacity": 1.0
}
```

- `x`,`y` = top-left of the layer box
- `w`,`h` = box size
- box must stay in `0..1` after placement (no off-canvas V1)
- no matrices, no crop-in-asset pixels, no camera FOV

Motion primitives may animate toward a `target` region. They do not replace this schema.

## Cues

Scene-local timed text.

```json
{
  "cue_id": "c1",
  "start_ms": 0,
  "duration_ms": 1200,
  "text": "ปิดงานได้ *เร็วขึ้น*",
  "emphasis": "kinetic_text"
}
```

`text` may mark one `*span*` for emphasis.
Cue times are scene-local.
Cues are not primitives. They may *trigger* the `kinetic_text` primitive on a layer, or stand as overlay copy. V1 treats them as overlay copy. Binding to a layer is an open question.

## Primitive placement on the timeline

Primitive `start_ms` / `duration_ms` are **scene-local**.
A primitive must fit inside its scene.
A primitive may start before its layer's visibility, but it has no effect outside visibility. Validators warn; they do not have to fail V1. Recommendation: fail if primitive interval is completely outside visibility.

## Audio is not a scene layer

Audio lives in `project.audio`.
Do not put voice assets on visual layers.

## Forbidden in this DSL

- FFmpeg filter graphs
- codec names as motion
- CSS / SVG path data as the only way to express a move
- floating seconds
- pixel coordinates
- inferred scene length from asset duration
- inferred cue length from word count
