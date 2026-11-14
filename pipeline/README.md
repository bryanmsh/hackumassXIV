# pipeline (Owner A)

Turns a PDF into page images, text, subject candidates and masks. No database and no web
code: it reads and writes files under a book folder and returns the types in
`contracts/types.py`.

## Install and test

```bash
python -m venv .venv && .venv/bin/pip install -r pipeline/requirements.txt
.venv/bin/python -m pytest pipeline/tests -q          # offline, Gemini is mocked
RUN_LIVE=1 .venv/bin/python -m pytest pipeline/tests -q -m live   # calls the real Gemini API
```

Run everything from the repo root so `contracts` and `pipeline` import.

## What is here

| File | What it does |
| --- | --- |
| `ingest.py` | `rasterize(pdf_path, out_dir)`: master and working-copy PNGs, text, `spread` and `low_quality` flags |
| `masks.py` | Mask cleanup, saving under the mask's own hash, polygon fill, box and IoU helpers |
| `outline.py` | `mask_from_outline(...)`: the teacher's drawn shape as the mask. `tidy=False` calls no model |
| `segment.py` | `segment(image, box=None, points=None)`: the one door to the segmenter, chosen by `SEGMENTER` |
| `gemini.py` | `choose_subjects(view_path, text)` and `label_crop(png_bytes)`: the one door to Gemini |
| `process.py` | `process_page(asset, out_dir, force=False)`: Gemini, a mask per candidate, the state rules. Never raises |
| `click.py` | `segment_at_point(image_path, x, y, out_dir)` and `refine_mask(image_path, mask_path, x, y, out_dir)` |
| `run_book.py` | Command line: process a whole PDF with no API and no database |

## Run a whole book

```bash
.venv/bin/python -m pipeline.run_book path/to/book.pdf data/books/my-book
```

Run it from the repo root: it reads `.env` there for `GEMINI_API_KEY`, `GEMINI_MODEL`,
`SEGMENTER` and `PAGE_CONCURRENCY` (default 4 pages at once). **This calls the real Gemini
API, one call per page.** It prints one line per page (state, reason, seconds) and writes
`summary.json` beside the page and mask folders. A page that fails does not stop the others.

## Files written (Contract 3)

```text
{out_dir}/pages/{n}.png          master: RGB, 300 DPI, longer side at most 3,000 px
{out_dir}/pages/{n}_view.png     working copy: longer side at most 1,600 px
{out_dir}/masks/{n}_{hash}.png   8-bit, one channel, master size, 255 = subject
```

## Gemini findings (to post to the team)

| Question | Answer |
| --- | --- |
| Model name | `gemini-3.8-flash` (newest Flash in the live model list, 2026-11-14). `gemini-flash-latest` does not exist for our key: 404 |
| Box format | `[ymin, xmin, ymax, xmax]`, integers 0 to 1000. Confirmed by eye on one page: both boxes landed on their objects |
| Four calls at once | not yet tested |
| Time per call | 9.4 s and 9.2 s for the same page (1600 px view, no page text), two samples |
| Tokens per call | 1,355 in (image plus prompt), 471 thinking, 203 answer; one sample |

## Settings

| Setting | Values | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | your key | Read from the environment only. Never printed or logged |
| `GEMINI_MODEL` | a Flash model name | Empty uses `gemini-3.8-flash` |
| `SEGMENTER` | `grabcut` (default), `stub`, `edgesam`, `sam2` | `edgesam` and `sam2` are not built: they raise `NotImplementedError` until the PyTorch code is added in `segment.py` |

## How subjects are found

One call per page asks Gemini for **every main subject**, up to 5, each as one clean object.

- The model first lists everything it sees (`things_on_page`), then ranks.
- Each candidate is one person, animal or object, or one tight group of the same kind that
  touch (two children playing). Things apart on the page are separate candidates.
- Guards in `gemini.py` hold even if the model ignores the prompt: the setting is dropped
  (forest, sky, ground, grass, background...), a box holding two or more other candidates is
  dropped as a group, and two boxes on the same object keep the more confident one.
- A fixed `seed` makes the same page give the same answer.

Measured on *Animal Homes* with `gemini-3.8-flash` (2026-11-14, 9 live calls):

| Page | Text | Result |
| --- | --- | --- |
| 2 | Animals live all around us. | `scene`: children 0.85, woodpecker 0.80, ants 0.75, ant 0.65, ant 0.65. Identical in 4 runs out of 4 |
| 3 | Birds build their homes up high. And so do bees. | `several`: beehive 0.95, bird 0.95, bird nest 0.90, bird 0.85 |
| 7 | Rabbits and rats live in burrows under the ground. | `several`: rabbit 0.95, rabbit 0.95, rat 0.90, rat 0.90 |
| 10 | Crocodiles live in swamps. | `single`: crocodile 1.00, so Ready |

Before this change the same page 2 gave a different answer on each of three runs, one of them
a grouped "bird and..." box, the "forest", and no children.

Per call: about 1,545 tokens in, 400 to 816 thinking, 161 to 509 answer; 7.6 to 12.9 s.
Sending the picture at high `media_resolution` changed neither the answer nor the token
count, so it is not set.

Cut-outs are a separate matter: on page 2 GrabCut cut the children and the woodpecker
cleanly, did poorly on the ants among leaves, and found no shape for one ant, which was
dropped. That is the segmenter's limit, not the finding step.

## Limits on one Gemini call

Set in `gemini.py`, far above normal use, so they trip only when a call goes badly wrong.

| Limit | Value | A real call on the demo page |
| --- | --- | --- |
| Thinking tokens (`MAX_THINKING_TOKENS`) | 8,192 | 400 to 816 across four pages |
| Thinking plus answer (`MAX_OUTPUT_TOKENS`) | 16,384 | 561 to 1,291 |
| Page text sent (`MAX_TEXT_CHARS`) | 8,000 characters | 0 (no text layer); a picture-book page is a few hundred |
| Time per attempt | 20 s | 7.6 to 12.9 s |
| Attempts per page | 2 | 1 |

An answer cut off at the output cap is treated as a failed call: one retry, then the page is
Failed with the reason "Gemini's answer was cut off at the output limit".

## Adding the PyTorch segmenter (Bryan)

Fill in `_edgesam` or `_sam2` in `segment.py`. The docstring on `_edgesam` states the exact
input and output. Add torch to `pipeline/requirements.txt` yourself; nothing else changes.
