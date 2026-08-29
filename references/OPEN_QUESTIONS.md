# Unresolved questions

Not locked. Do not invent runtime to close them.

## 1. Scene versus shot

- Question: Is `scene` the only timeline unit, or do we need `shot`?
- Current recommendation: scene only. Optional `label` may say "shot 3".
- Why: V1 packing is already tiled. A second object duplicates time.
- Experiment: storyboard 10 SaaS ads. If editors keep splitting one packed scene into editorial shots, add `shot_id` as a label group, not a time object.

## 2. Transform model

- Question: Is a box + opacity + rotation enough?
- Current recommendation: yes for V1.
- Why: zoom/pan are primitives that animate that box. A matrix invites engine math into the DSL.
- Experiment: try `zoom_to_region` on a tall screenshot. If we need camera tilt or asset-space crop separate from project-space box, add one field then, not now.

## 3. Target region representation

- Question: raw box vs named regions (`mrr_card`)?
- Current recommendation: raw `{x,y,w,h}` in the plan. Director resolves names before validation.
- Why: names need a registry and screenshot-specific layout. That is a Director concern.
- Experiment: Gemini box_2d on 20 dashboards. If names are stable across screens, add an optional `region_id` later.

## 4. Audio layering

- Question: How do voice, music, and sfx share time?
- Current recommendation: tracks in `audio.tracks`. Optional `exclusive_track` for one voice at a time. File duration is authority. No word-count timing.
- Why: matches Phoenix-Cut evidence without copying its mixer.
- Experiment: one user-voice + one music bed. Decide ducking as renderer policy, not DSL, unless two products need different ducking.

## 5. Cue-to-layer binding

- Question: Are cues free overlay text or do they attach to `kinetic_text` on a layer?
- Current recommendation: cues are overlay copy. `params.from_cue_id` is optional glue.
- Why: keeps text readable if no kinetic layer exists.
- Experiment: one plan with only cues, one plan with cues + kinetic layer. Keep both legal.

## 6. QC tolerances

- Question: How many ms may output duration drift?
- Current recommendation: not in schema. QC later. Do not guess 0.5s into the contract.
- Why: tolerance is engine-specific.
- Experiment: Phase 2 renderer on `valid_minimal_project`. Measure drift. Then write QC numbers.

## 7. Primitive params bag

- Question: Open `params` vs per-type schemas.
- Current recommendation: open bag, closed `type` enum.
- Why: unknown types must die; new optional params must not die.
- Experiment: after three primitives ship, freeze params that actually got used.

## 8. Atmosphere bridges of Truth frames

- Question: May first/last-frame Flow video sit on a Truth band if both ends are real screenshots?
- Current recommendation: no. The generated middle is `AI_GENERATED`. Keep it Atmosphere or wait for an experiment that proves glyphs hold.
- Experiment: research E2 (screenshot first/last frame). If glyphs survive every frame, consider a new truth_level. Do not reuse `VERIFIED_PRODUCT`.

## 9. Off-canvas transforms

- Question: May a layer start partly outside 0..1 for a slide-in?
- Current recommendation: no in V1. Slide later as a primitive that stays legal at each sampled frame, or pre-crop.
- Why: simpler validator.
- Experiment: one slide-in ad. If needed, allow `x` in `-0.5..1.5` only for named slide primitives.

## 10. fps as composition vs capture

- Question: Is `project.fps` output fps or source fps?
- Current recommendation: output composition fps. Source fps stays on the asset if known.
- Why: one canvas clock.
- Experiment: 24fps screen recording into a 30fps project. Document frame mapping in Phase 2, not here.
