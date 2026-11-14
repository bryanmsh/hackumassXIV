# Commit notes (Kevin, lane B)

One entry per commit, newest first: what changed, why, and what is still open.

## Add commit notes

- Started this file. Every commit from here on gets an entry.
- No code changes.

## 0ceec2a: Owner B: render, overlay, run_checks, second_look with samples, tests and pitch drafts

**What changed**
- `render/`: `render()` for all four levels (Tinted, Cut-out, Faded page, Outlined), `overlay()` for subject review, `RENDER_VERSION = "b1"`. Size, position, extra outline and the text band (Atkinson Hyperlegible) are already in, though the plan lists them as Phase 2.
- `render/samples/`: two generated stand-in pages (bird, rabbit) with masks, plus two deliberately bad masks. These are stand-ins until Bryan's real pages land.
- `checks/`: `run_checks()` (fidelity, page edge, background, contrast, size, text contrast) and `second_look()` (Gemini, warning only). Also `swatch_contrast()` for the profile screen's 3 to 1 warning.
- `pitch/`: draft teacher email with mock-up images, first demo script.
- 45 tests in `render/tests` and `checks/tests`, including the source-fidelity proof at Cut-out.

**Why some choices**
- WebP encoder method 0: about 25 ms faster per page. Median render is now 116 ms on the laptop, against a 150 ms target.
- Edge softening only goes inward, so no pixel from outside the mask can ever show.
- Types mirror Contract 2 locally and switch to Andrew's `contracts/types.py` automatically when it exists.

**Still open**
- `second_look` not yet tried against real Gemini (no key on this machine).
- Swap in Bryan's real pages (hour 5).
- Reader tests in `tests/` (hour 11).
- Email: trim to three questions, say "teacher" instead of "TVI." Demo script: add when the reset script runs.
