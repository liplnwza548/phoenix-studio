# Truth Rules

Product-facing facts must not appear from a model by accident.

## Truth Layer content

Treat as Truth when the viewer could take it as the product:

- product UI chrome
- prices
- metrics and dashboards
- people and company names
- feature names
- claims of outcome
- logos and marks
- step-by-step product workflows

## Atmosphere Layer content

- cinematic B-roll
- abstract motion
- rooms, cities, weather
- metaphor
- mood texture
- bridges between two real frames when the bridge itself is not the UI

Atmosphere is allowed to be `AI_GENERATED`.
It is not product truth even if it looks like a laptop.

## Binding rule

```
layer.band == TRUTH
    → asset.truth_level ∈ { USER_PROVIDED, VERIFIED_PRODUCT, PUBLIC_REFERENCE }
```

`PUBLIC_REFERENCE` on a Truth layer is allowed only for third-party marks the user supplied as reference, not for invented UI.
Prefer `VERIFIED_PRODUCT` for our own screens.

```
layer.band == ATMOSPHERE
    → any truth_level
```

## Promotion rule

Nothing automatic promotes media:

| Action | Allowed? |
|---|---|
| User uploads a screenshot, `USER_PROVIDED` | yes |
| Human marks it `verified: true` and `VERIFIED_PRODUCT` | yes, explicit |
| Flow clip arrives as `AI_GENERATED` | yes, Atmosphere only |
| Set `verified: true` on a Flow clip | yes, still Atmosphere |
| Change a Flow clip to `VERIFIED_PRODUCT` | no, unless a future process replaces the file with a real capture |

## Director rule

The Director may propose Atmosphere shots.
The Director may not invent prices, metrics, or UI copy and place them on a Truth layer.

If a brief lacks a real screen, the plan must either:

- stay Atmosphere-only, or
- fail closed and ask the user for a screenshot / recording

## Audio claims

Spoken claims are not `truth_level` on an asset.
They are content risk.
V1 does not schema-check words.
QC and human approval cover them.
