# Asset Contract

Every piece of media the plan can name is an asset.
Assets are declared once at project level. Layers only point at `asset_id`.

## Required fields

| Field | Meaning |
|---|---|
| `asset_id` | Unique in the project |
| `kind` | `image` `video` `audio` `font` `svg` |
| `uri` | Locator. File path, `asset://`, or URL. Opaque to the DSL |
| `source` | Who or what produced it (studio, user, flow, capture device) |
| `source_type` | How it entered: `upload` `capture` `generated` `url` `derived` |
| `verified` | Boolean. Accepted by a human or an approved checker |
| `captured_at` | ISO-8601 timestamp or `null` if unknown |
| `truth_level` | See below |

Optional: `label`, `notes`, `width_px`, `height_px`, `duration_ms`.

`duration_ms` on an audio/video asset is **file truth when known**.
The renderer and validator in later phases treat measured file duration as timing authority.
The plan must not invent duration from script length.

## Provenance and truth are different

```
source + source_type + captured_at     = provenance
verified                               = acceptance flag
truth_level                            = allowed use as product reality
```

Do not collapse these.

## truth_level

| Value | Meaning |
|---|---|
| `USER_PROVIDED` | User handed us this file |
| `VERIFIED_PRODUCT` | Confirmed to be the current product |
| `PUBLIC_REFERENCE` | Public third-party material, not our product UI |
| `AI_GENERATED` | Model output |
| `FICTIONAL` | Invented on purpose |

`USER_PROVIDED` is not automatically `VERIFIED_PRODUCT`.
A user can upload a mock.

`verified: true` on `AI_GENERATED` means "we accept this file as an atmosphere take".
It still cannot sit on a `TRUTH` band.

## kind versus use

`kind` is the bytes.
`band` on the layer is the use.
A `video` can be Truth (screen recording) or Atmosphere (street b-roll).

## Atmosphere ingest

Flow / Veo / Omni output enters as:

```json
{
  "source": "google-flow",
  "source_type": "generated",
  "truth_level": "AI_GENERATED",
  "verified": false
}
```

A human may later set `verified: true`.
Truth level stays `AI_GENERATED`.

## Forbidden

- Assets without `truth_level`
- Silent promotion of generated media to product UI
- Director-invented `duration_ms` for voice from word count
- Embedding raw media bytes in the plan
