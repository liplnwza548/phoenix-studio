# Phase 5 renderer spike

Same input: `../../examples/phase5_benchmark.json`

- Track A: `current-render.mp4` via production `python -m renderer`
- Track B: `remotion-render.mp4` via `render_browser.py` (Chrome headless + HTML)

Full `npm install @remotion/cli` timed out in this environment.
Track B therefore tests the **browser compositing model** Remotion uses, not a production Remotion Studio project.
