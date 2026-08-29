# Motion Primitive Contract

Primitives are named operations on a layer.
The DSL stores the name and timing. It does not store engine math.

## Common fields

Every primitive:

| Field | Meaning |
|---|---|
| `type` | One of the V1 names below |
| `start_ms` | Scene-local start |
| `duration_ms` | Length. `0` only allowed for instantaneous types |
| `easing` | `linear` `ease_in` `ease_out` `ease_in_out` |
| `target` | Optional region `{x,y,w,h}` in `0..1` |
| `params` | Type-specific bag. Unknown keys inside `params` are allowed. Unknown `type` is not |

Instantaneous V1 types: `cut`, `cursor_click`.
These may use `duration_ms: 0`.

## V1 types

| type | Meaning | `target` | `params` (v0.1) |
|---|---|---|---|
| `crop_9_16` | Place the asset into the 9:16 canvas | optional crop window on the asset, normalized | — |
| `cut` | Hard start of this layer at `start_ms` | — | — |
| `fade` | Opacity change | — | `direction`: `in` or `out` |
| `zoom_to_region` | Animate transform toward `target` | required | — |
| `pan_to_region` | Translate toward `target` without zoom | required | — |
| `highlight_box` | Draw a box at `target` | required | `style`: `rect` (only V1) |
| `spotlight_dim` | Dim outside `target` | required | `dim`: 0..1, default `0.55` |
| `cursor_move` | Move cursor overlay | optional dest box | `from` `{x,y}`, `to` `{x,y}` |
| `cursor_click` | Click pulse at a point | optional | `position` `{x,y}` |
| `kinetic_text` | Animate overlay copy | optional anchor | `from_cue_id` optional |
| `hold` | Keep last transform | — | — |

Unknown `type` → validation failure.
No aliases. No engine names (`zoompan`, `xfade`, `overlay`).

## Coordinate target

`target` is a project-normalized box:

```json
{ "x": 0.12, "y": 0.18, "w": 0.40, "h": 0.16 }
```

It is not pixels.
It is not a CSS selector.
Named UI regions (`#mrr-card`) are not in v0.1. Director must resolve names to boxes before the plan is valid.

## Easing

Easing names are semantic.
The renderer maps them later.
Do not put bezier control points in v0.1.

## Stacking

Primitives on one layer run on that layer's local time.
They may overlap on the same layer when the combination is meaningful
(example: `hold` under a `highlight_box` that lives on another layer).

V1 recommendation: one transforming primitive (`zoom_to_region` / `pan_to_region` / `fade`) active on a layer at a time.
Two transforming primitives that overlap on one layer = invalid.
Non-transforming overlays live on their own layers.

## What this contract does not say

- frame interpolation method
- cursor PNG
- font file for kinetic text
- highlight stroke width in pixels
- FFmpeg filter equivalents
