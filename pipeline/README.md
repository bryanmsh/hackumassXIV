# pipeline (Owner A)

Turns a PDF into page images, text, subject candidates and masks. No database and no web
code: it reads and writes files under a book folder and returns the types in
`contracts/types.py`.

## Install and test

```bash
python -m venv .venv && .venv/bin/pip install -r pipeline/requirements.txt
.venv/bin/python -m pytest pipeline/tests -q          # the subject model is faked, except where torch is installed
```

Run everything from the repo root so `contracts` and `pipeline` import.

## What is here

| File | What it does |
| --- | --- |
| `ingest.py` | `rasterize(pdf_path, out_dir)`: master and working-copy PNGs, text, `spread` and `low_quality` flags |
| `masks.py` | Mask cleanup, saving under the mask's own hash, polygon fill, box and IoU helpers |
| `outline.py` | `mask_from_outline(...)`: the teacher's drawn shape as the mask. `tidy=False` calls no model; tidy=True uses the segmenter's mask when it overlaps the drawing by 30 % or more, clipped to the drawing's box grown by 15 %; otherwise the drawing is kept. |
| `segment.py` | `segment(image, box=None, points=None)`: the one door to the segmenter, chosen by `SEGMENTER` |
| `sam.py` | SAM 2.1 small and EdgeTAM through transformers. The only file that imports torch |
| `subjects.py` | `choose_subjects(view_path, text)` and `label_crop(png_bytes)`: the one door to our subject model (`subject_model/`), the guards on its answer, and the trust rule |
| `process.py` | `process_page(asset, out_dir, force=False)`: our subject model, a mask per candidate, the state rules. Never raises |
| `click.py` | `segment_at_point(image_path, x, y, out_dir)` and `refine_mask(image_path, mask_path, x, y, out_dir)` |
| `cascade.py` | `SEGMENTER=mirai` and `cascade`: our cut-out model, its confidence checks, and the hand-off to SAM 2 |
| `calibrate_cascade.py` | Command line: measures our cut-out model against SAM 2 and picks `CASCADE_MIN_CONFIDENCE` |
| `credits.py` | `read_credits(pdf_path)`: author, illustrator, publisher, source and license copied from the PDF's text layer (first 2 and last 4 pages); `None` when not printed, never raises, never guesses |
| `run_book.py` | Command line: process a whole PDF with no API and no database |

## Run a whole book

```bash
.venv/bin/python -m pipeline.run_book path/to/book.pdf data/books/my-book
```

Run it from the repo root: it reads `.env` there for `SEGMENTER`, `PAGE_CONCURRENCY` (default
4 pages at once) and the model weight paths. Everything runs on this machine; nothing is sent
to an outside service. It prints one line per page (state, reason, seconds) and writes
`summary.json` beside the page and mask folders. A page that fails does not stop the others.

## Files written (Contract 3)

```text
{out_dir}/pages/{n}.png          master: RGB, 300 DPI, longer side at most 3,000 px
{out_dir}/pages/{n}_view.png     working copy: longer side at most 1,600 px
{out_dir}/masks/{n}_{hash}.png   8-bit, one channel, master size, 255 = subject
```

## Settings

| Setting | Values | Notes |
| --- | --- | --- |
| `SEGMENTER` | `grabcut` (default), `stub`, `sam2`, `edgetam`, `mirai`, `cascade` | `sam2` is the recommended setting on the server. `edgesam` raises: it has no installable package. `mirai` is our own cut-out model alone; `cascade` runs it first and sends unsure boxes to SAM 2 (`pipeline/cascade.py`) |
| `CASCADE_MIN_CONFIDENCE` | 0 to 1 | Empty means 0.65, from `calibrate_cascade` on *Animal Homes* with the run B weights: our model keeps 67% of boxes at 0.919 agreement with SAM 2.1. Below it, a box goes to the fallback |
| `CASCADE_FALLBACK` | a segmenter name | Empty means `sam2`. Not `cascade` or `mirai` |
| `CASCADE_FLIP` | `1` (default) or `0` | `0` skips the mirrored-page check, which halves our model's time per box but makes it a worse judge of itself: at the same agreement it keeps 53% of boxes instead of 67% (threshold 0.75). The mirror pass runs only when the first pass clears the threshold, since it can only lower the score |
| `CUTOUT_MODEL` | empty or `standin` | `standin` replaces our model with GrabCut with blurred edges, until the weights exist |
| `NAMER_WEIGHTS`, `FINDER_WEIGHTS` | paths | Our subject model's weights. Empty means `$DATA_DIR/models/namer.pt` and `finder.pt`; the trained ones are in `subject_model/weights/` |
| `SUBJECT_MODEL` | empty or `standin` | `standin` is a placeholder that finds nothing, for a machine without torch or the weights: every page asks the teacher |
| `SUBJECT_FINDER` | not used | Chose between Gemini and our model until 2026-11-15. Any old value only logs one warning |
| `MODEL_CACHE_DIR` | a folder | Where model weights download on first use. Empty means `$DATA_DIR/models` (the mounted `data/` folder in Docker) |
| `TORCH_THREADS` | a number | Threads torch may use. Empty means every core |

**Cut-out cascade speed on CPU (measured on *Animal Homes*, 36 boxes, 13 pages).** SAM 2.1 spends about 2.1 s studying a page once, then about 0.29 s per extra box; one pass of our model is about 0.27 s per box. So on a CPU server no cascade setting is meaningfully faster than SAM alone while staying as accurate: box-by-box at threshold 0.65 it is 1.03x SAM's speed at 0.947 agreement, and any stricter setting is slower than SAM. The speed-up needs a GPU (our model 0.02 s vs SAM 0.10 s a box on an L4). The live server runs `SEGMENTER=cascade` at threshold 0.75 anyway, to cut with our own model where it is sure, at about SAM's speed.


## How subjects are found

Our subject model (`subject_model/`, trained from scratch) answers every page; no outside AI
service is called.

- The **finder**, a half-width U-Net, marks up to a few blobs that stand out on the page.
- The **namer**, a ResNet-18 over 347 names, names each blob from a cut-out on white.
- The **page text** confirms a name when it mentions it ("Crocodiles live in swamps."), which
  raises that candidate's confidence. Printed words, marks and settings are dropped.
- Guards in `subjects.py` hold on every answer: the setting is dropped (forest, sky, ground,
  grass, background...), a box holding two or more other candidates is dropped as a group, and
  two boxes on the same object keep the more confident one.
- The same page always gives the same answer.

**The trust rule** (`subjects.local_is_enough`). Our model finds things that stand out well but
names them poorly and misses second subjects, so a page is pre-selected only when all three hold:

1. `process.decide_state` would pre-select exactly one subject;
2. the page text names it (`subject_model.local.CONFIRMED`);
3. the text is not about anything else: no "and", "&", "or", "with", and no other name our
   model knows.

Otherwise the answer is marked `trusted=False` and the page asks the teacher, with our
candidates still offered. Without checks 1 and 2 our model pre-selected a wrong cut-out on 4 of
7 Ready pages of *Animal Homes*; check 3 came from page 11 ("Deer live in forests. And so do
tigers!"), where it chose the tiger and never offered the deer. `subjects.last_subject_route()`
says why each page was or was not trusted.

**Naming a click.** `label_crop` asks the namer about the crop around the clicked cut-out. It
answers only when it is at least 0.5 sure; otherwise the name is empty and the teacher types it.

On *Animal Homes* (16 pages, measured 2026-11-15) one page comes back Ready, and it is right
(page 10, the crocodile). The other 15 ask the teacher; on 6 of them the trust check held back a
single guess, 4 of which were wrong (pages 6, 7, 12 and 16) and 2 right but on pages about two
things (the bear and the tiger, whose page text also names wolves and deer). No page failed.
The whole book took 93 s on a laptop CPU with `SEGMENTER=cascade`, 4 pages at a time.

Until 2026-11-15 Gemini Flash chose subjects, with our model in front of it as a cascade.
Gemini found about two of every three labelled subjects; ours finds about one in seven
(`subject_model/README.md`), so the teacher now picks the subject on most pages.

## What gets pre-selected

A page about one thing comes back Ready with its top candidate selected. A page with several
main subjects offers a combined cut-out but does not pre-select it: the subject is what the
story is about, and that is the teacher's call. The teacher still confirms or changes every page.

| Page | Pre-selected | State |
| --- | --- | --- |
| About one thing (`single`), and the trust rule holds | The top candidate, if its confidence is 0.5 or more | Ready |
| About one thing, but the trust rule fails | Nothing; our candidates are offered | Needs subject ("The app is not sure this is the subject. Please check it.") |
| Several main subjects, or a scene | Nothing. One **combined cut-out** of every candidate at 0.5 or more is added after the single ones (for example "rabbit and rat"), one click away | Needs subject |
| Candidates found, none at 0.5 | Nothing | Needs subject |
| No candidates, or no usable cut-out | Nothing | No clear subject |
| The first choice had no usable cut-out | Nothing | Needs subject |

The combined cut-out is the single masks joined, not cleaned again, so a small subject beside
a large one is kept. Its synonyms are every member's names, its confidence the lowest member's.
The page text no longer blocks a selection, and the old 0.7 / 0.2-ahead thresholds are gone.
**This departs from the spec**, which sends `several` pages to Needs subject and scenes to
No clear subject (Andrew's decision, 2026-11-14).

On *Animal Homes*: page 2 selects "children, woodpecker and ants", page 3 "beehive, bird and
bird nest", page 7 "rabbit and rat" (both rabbits and both rats), page 10 "crocodile".

## Segmenter: SAM 2.1 small

`SEGMENTER=sam2` runs Meta's SAM 2.1 small (`facebook/sam2.1-hiera-small`, Apache-2.0) on the
CPU through Hugging Face `transformers`. `pipeline/sam.py` is the only file that imports torch,
and it imports it lazily, so `stub` and `grabcut` run without torch installed.

How it works:
- **Load once.** The model loads on first use and stays loaded for the life of the process.
- **Encode once per page.** The image encoder, the slow part, runs once per page. Its output
  is cached by the page's pixel hash (the last 8 pages), so the up-to-5 subject boxes on a page,
  and later clicks on it, only run the fast prompt decoder (about 0.15 s each).
- **One lock.** Up to 4 pages are processed in parallel threads, and torch already spreads one
  call across every core, so the model runs one call at a time.
- **Clicks.** One click is ambiguous (the wing, or the whole bird?), so the model returns 3
  masks, and the largest one that covers at most 60% of the page wins. The model scores the
  small part highest, but a teacher clicking an animal means the whole animal.
- **Fallback.** For a box, if the model scores its own mask below 0.5, or the mask fills more
  than half the box's edge (it picked the background inside the box), that prompt uses GrabCut
  instead. A rough cut-out of the right object beats a clean one of the wrong thing.
- **Weights.** About 180 MB, downloaded from Hugging Face on first use into `MODEL_CACHE_DIR`.
  In Docker that is `data/models`, which survives rebuilds. They are never committed. To fetch
  them ahead of time: `python -m pipeline.sam --fetch sam2`.
- **Install.** `requirements.txt` pins CPU-only torch from the PyTorch CPU index. On the GPU
  box, drop the `+cpu` suffixes and the index line; the device is picked automatically.

### Trial (2026-11-14)

Kevin's two hand-masked sample pages (`render/samples/1` bird on a branch, `2` rabbit), each
scored by IoU against his mask. "Tight" is the subject's box padded 3%, "loose" padded 12%
(closer to the boxes subject finding gives), "click" is one point on the body. Torch limited to 4 threads to
match the server. Measured on a laptop CPU; the server's 4 vCPUs may be somewhat slower.

| Segmenter | Bird tight | Bird loose | Bird click | Rabbit tight | Rabbit loose | Rabbit click | Encode per page | Per prompt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GrabCut | 0.81 | 0.81 | 0.25 | 0.87 | 0.34 | 0.38 | none | 1.7 to 4.7 s |
| **SAM 2.1 small** | **0.98** | 0.81 | **0.98** | **0.98** | **0.97** | **0.97** | 3.9 to 4.1 s | 0.13 to 0.16 s |
| EdgeTAM | 0.83 | 0.82 | 0.82 | 0.98 | 0.98 | 0.36 | 0.7 to 0.8 s | 0.10 to 0.17 s |

- The first call in a process also takes about 10 s to import torch and load the model.
- The bird's "loose" 0.81 is SAM keeping the branch the bird stands on: the branch touches
  the bird and sits inside the box. The teacher can fix that page by click or outline.
- A page with 3 candidates costs about 4 s of encoding plus 3 x 0.15 s with SAM 2, against
  about 3 x 3 s with GrabCut. So SAM 2 is both more accurate and no slower per page.
- EdgeTAM is 5x faster to encode but less accurate. Use it only if SAM 2 is too slow on the server.
- EdgeSAM, named in the spec, has no pip package (research-repo code only). EdgeTAM is its
  successor from the same group and is supported in transformers.

## Model cascade

The cut-out step runs a model we trained ourselves first and calls SAM 2.1 only when ours is
unsure. It falls back to SAM if our model is missing or fails, so `main` starts without the
weights. (Subject choosing used the same pattern in front of Gemini until 2026-11-15; it now
uses our model alone, see "How subjects are found".)

| Step | Ours first | Behind it | Setting | On the live server |
| --- | --- | --- | --- | --- |
| Cut-out | `cutout_model` (7.8M-parameter U-Net, trained from scratch) | SAM 2.1 small, then GrabCut | `SEGMENTER=cascade` | On, with `CASCADE_MIN_CONFIDENCE=0.75` (about 42% of boxes ours at 0.967 agreement on *Animal Homes*) |

### Cut-out cascade

For each box, our model gives a probability map and five checks score it from 0 to 1. The
mask's confidence is the **lowest** of the five, so one bad sign is enough to hand off:

| Check | What it asks |
| --- | --- |
| `sure` | Is the map decided (near 0 or 1) along the mask's outline? |
| `fill` | Does the mask fill a sensible share of its box (not a speck, not the whole box)? |
| `pieces` | Is the mask mostly one piece? |
| `border` | Does it avoid filling the box's edge (background inside the box)? Same rule as `sam.py` |
| `flip` | Does the model give the same mask on the mirrored page? |

At or above `CASCADE_MIN_CONFIDENCE` our mask is kept; below it the box goes to
`CASCADE_FALLBACK`. Clicks always go to the fallback. `cascade.last_route()` and
`cascade.route_counts` say which model answered and why (for example `unsure: flip`).

**Calibration**, done once ahead of time, not per book:

```bash
python -m pipeline.calibrate_cascade data/runs/animal-homes --fallback sam2
```

It runs both models on every box, tries thresholds from 0 to 1 in steps of 0.05, and picks
the one that keeps the most boxes on our model while the mean stays within the margin of the
fallback alone. It writes `calibration.json`, `.csv` and an `.svg` chart. The source is either a
hand-masked test set (IoU against the masks) or a `run_book` folder. A book has no hand masks,
so there it measures **agreement with SAM 2.1, not accuracy**.

Result on *Animal Homes* (36 single-subject boxes from a Gemini run, run B weights, laptop CPU):

| Threshold | Boxes kept by ours | Agreement with SAM 2.1 |
| --- | --- | --- |
| 0 (ours alone) | 100% | 0.786 |
| 0.50 | 89% | 0.842 |
| 0.60 | 78% | 0.890 |
| **0.65 (default)** | **67%** | **0.919** |
| 0.70 | 53% | 0.948 |
| 1 (SAM alone) | 0% | 1.000 |

Without the mirror check (`CASCADE_FLIP=0`) the best is 53% at 0.930, so the check stays on.

**Speed.** On a CPU the cascade is about as fast as SAM alone (0.92 against 0.90 s a box),
because our model runs twice (page and mirror) and the unsure third still pays for SAM. The
win needs a GPU: 0.02 s against 0.10 s a page on an L4 (`cutout_model/README.md`). That is why
the server stays on `sam2`. To switch on: put the weights at `data/models/cutout.pt` (or set
`CUTOUT_WEIGHTS`) and set `SEGMENTER=cascade`.

