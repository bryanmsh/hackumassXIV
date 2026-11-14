# Better Subject Finding Implementation Plan

**Goal:** Every main subject of a page appears among the candidates, as one clean object each, and the answer changes less between runs.

**Why:** On the demo page ("Animals live all around us.") one run returned a grouped candidate ("bird and..."), the setting ("forest") and ants, and left the children out. Other runs of the same page returned children and woodpecker.

**Decided by Andrew (2026-11-14):** show up to 5 candidates, not 3. The page should surface all of its main subjects, not one. The state rules do not change.

**Files:** `pipeline/gemini.py`, `pipeline/tests/test_gemini.py`, `pipeline/README.md`. Nothing outside `pipeline/`.

## Global constraints

- Branch `bryan` only. Contract 2 types do not change: `PageResult.candidates` is already a list.
- Unit tests stay offline. Live calls are for measuring only, and each is counted in the dev log.
- The per-call limits (output, thinking, text, 20 s, one retry) stay as they are.

## Tasks

### Task 1: Ask for all main subjects, one object each

- [x] `MAX_CANDIDATES = 5`. Update the existing trim test: 7 candidates in, the 5 most confident out.
- [x] `SubjectAnswer` gains `things_on_page: list[str] = []` as its FIRST field, so the model lists every person, animal and object before it ranks. Test: an answer with and without the field parses.
- [x] New `PROMPT`: list every main subject; each candidate is exactly one thing, or one tight group of the same kind that touch (two children playing together); things apart on the page are separate candidates; people count; never the setting (forest, sky, ground, grass, background); box tight around that one thing; up to 5, most important first; do not leave a main subject out to make room for a minor one.

### Task 2: Guards that hold even when the model ignores the prompt

In `choose_subjects`, after tidying and before sorting and trimming. Each is a pure function with its own tests.

- [x] `_is_setting(label)`: true when any word of the label is in `SETTING_WORDS = {background, scene, scenery, landscape, forest, jungle, woods, sky, ground, grass}`. Tests: "forest" and "dense forest" dropped; "grasshopper", "tree" and "nest" kept.
- [x] Group or setting by shape: drop a candidate whose box holds two or more other candidates (at least 80% of each inside it). Tests: a tall box over a bird and ants is dropped and both are kept; a nest holding one bird is kept (an animal's home is a real subject).
- [x] Near-duplicates: of two boxes with IoU of 0.8 or more, keep the more confident. Test.

### Task 3: More repeatable, sharper view

- [x] `seed=SEED` (0) on every call. Test on the config.
- [x] `media_resolution` high: measured live, it changed neither the answer nor the token count on `gemini-3.8-flash`, so it was removed.

### Task 4: Measure

- [x] Demo page, new prompt, 4 runs: are the children there every time? Any group or setting? Do the answers agree?
- [x] 4 pages of the real book: single-subject pages must still come back `single` with a clear top candidate.
- [x] Record tokens per call, and the results, in `pipeline/README.md` and the dev log.
- [x] Ask twice and merge: NOT built. With the seed, four runs of the demo page were identical, so it is not needed.
