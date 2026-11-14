# Training data plan: fine-tuning SAM 2.1 small for picture books

Goal: get about 2,000 synthetic and about 150 real picture-book subjects with masks,
plus a real-only test set, in about 1.5–2 hours, for about $1–2 of GPU time.
Training itself is covered in a separate plan.

Nothing here changes the app. All data lives in `data/train/`, which is gitignored
(`data/` is already ignored). Only the scripts and this plan are committed.

## Why two kinds of data

| Set | Where from | Masks | Strength | Weakness |
|---|---|---|---|---|
| **Composites** | Public-domain clipart pasted on illustrated backgrounds | Perfect (from the alpha channel) | Free and unlimited | Pasted subjects are easier to find than real ones |
| **Real** | CC-BY picture-book pages | SAM 2.1 large, then accepted or rejected by a person | Real art, real difficulty | Only as good as the large model, and slow to review |

We train on both and **test on real pages only**. A good score on composites
proves nothing about books.

## Folder layout

```
data/train/
  clipart/raw/        downloaded SVG files plus meta.jsonl (id, title, author, license, url)
  clipart/png/        rendered RGBA PNGs, cropped to the subject
  clipart/rejected.txt
  backgrounds/        illustrated backgrounds (from real pages, with no subject box over them)
  books/pdf/          CC-BY book PDFs plus CREDITS.md
  books/pages/        rasterized pages (pipeline.ingest.rasterize, 3,000 px master)
  books/boxes.jsonl   Gemini candidates per page (page, label, box, confidence)
  books/masks/        SAM 2.1 large masks, one PNG per (page, box)
  books/review.jsonl  decisions: keep / reject / test
  composites/img/     composite images
  composites/mask/    mask per image (255 = target subject)
  composites/meta.jsonl  image, target box, list of pasted ids, scale, blend settings
  splits.json         train / val / test file lists
```

## Step 1: clipart cut-outs (about 25 min, mostly script)

**Source:** Openclipart (every file public domain, CC0). It is all vector art in a
flat, outlined, picture-book style, close to our pages. If its API blocks us,
the fallback is Openverse filtered to `license=cc0,by` and `extension=png,svg`.

**Search terms**, about 300 files total, about 10 per term. These are the subjects
picture books are about:
animals (rabbit, bird, cat, dog, bear, fish, elephant, owl, frog, duck, lion, cow,
horse, mouse, turtle, butterfly, snail, monkey, giraffe, pig), people (child, girl,
boy, grandmother, farmer), things (ball, kite, boat, tree, flower, house, car, bus,
umbrella, apple, cake, hat, moon, sun, star).

**`fetch_clipart.py`:**
1. Query each term, then download the SVG and save its metadata line.
2. Render with `cairosvg` (pure pip install, no system dependency on Linux;
   on Windows it needs the Cairo DLL, so run it on the server or use the PNG preview).
   Render at a 1,024 px long side, with a transparent background.
3. Crop to the alpha bounding box.
4. **Auto-reject:**
   - opaque area under 5% or over 95% of the canvas (empty, or a full scene with a background)
   - more than 20% semi-transparent pixels (alpha 10–245): glow or drop shadow
   - a white border: over 60% of the 3 px edge ring is near-white
   - more than 3 separate opaque pieces of meaningful size: a sticker sheet, not one subject
5. Keep a license line per file. CC0 needs no credit, but we credit anyway in
   `CREDITS.md`.

**You (10 min):** `review.html` shows a grid of thumbnails. Click to reject the
bad ones (text logos, photos, abstract shapes, multi-object sheets), then press
`s` to save `rejected.txt`. Target: at least 250 kept.

## Step 2: real pages (about 30–45 min, partly by hand)

**Source:** StoryWeaver (Pratham Books), CC-BY 4.0, the same source as our
Animal Homes fixture. Prefer level 1–2 books: one big subject per page, which
is our use case.

**Getting the PDFs:** our script got 403 from StoryWeaver before, so plan on
doing this by hand: sign in, pick books, download the PDFs into
`data/train/books/pdf/`. About 1 minute per book; **15–20 books gives about
150–200 pages**. Write the title, author, illustrator and URL of each in
`CREDITS.md`. The CC-BY license requires it.

**Exclude** any book we use in the demo or eval (Animal Homes and the backup
books), so the test is fair.

**`prep_books.py`** (runs on the existing CPU server, no GPU):
1. `pipeline.ingest.rasterize` → 3,000 px master pages. Skip the cover, credits and
   text-only pages (those with no Gemini candidates).
2. `pipeline.gemini` on each page → up to 3 candidate boxes. 4 at a time, the same
   concurrency as the app. About 150 pages at about 4 s each, so about 10–15 min.
   Uses our existing key, about 150 calls.
3. Cut **backgrounds** for step 3 from the same pages: crop regions that don't
   overlap any candidate box, at least 600 px. Each page gives 0–2.

**`mask_books.py`** (on the A40, about 10 min including setup):
- SAM 2.1 large (`facebook/sam2.1-hiera-large`) on each box. Save the mask and score.
- Use the same `LowConfidence` rules as `pipeline/sam.py`. Fails are dropped, not
  sent to GrabCut.
- Then **destroy the A40**, or keep it only if training starts right away.

**You (15–20 min):** `review.html` again, one card per (page, box), showing the
page with the mask tinted magenta. Keys: `k` keep, `r` reject, `t` move to the
test set. Aim for about 150 kept and about 40 test, with test cards taken from
books that have no training cards.

## Step 3: composites (about 5 min, laptop CPU)

**`make_composites.py`**, seeded so it can be rebuilt exactly. About 2,000 images:

| Setting | Values |
|---|---|
| Background | random crop from `backgrounds/`, resized to 1,024 px; 20% a flat pastel colour, like a book page |
| Objects per image | 1 target plus 0–3 distractors |
| Target size | 15–60% of the image's long side |
| Placement | random; 15% partly off the edge; 25% chance a distractor overlaps the target by 10–40% |
| Flip and rotate | horizontal flip 50%; rotate ±15° |
| Colour match | shift each object's mean and std per channel 30% toward the background's |
| Edge blend | feather the alpha by 1–2 px |
| Shared finish | the same light noise or paper texture over the whole image, then JPEG at quality 70–95 |
| Mask | target's alpha > 127, **minus** any distractor pasted over it |
| Box prompt | the mask's box, padded 0–15% per side at random, so it looks like Gemini's loose boxes |

Then check 30 at random by eye. If the seams are obvious, raise the feather and
the colour match.

## Step 4: splits

| Split | Contents | Size |
|---|---|---|
| train | composites (90%) + kept real masks (90%) | about 1,800 + 135 |
| val | composites (10%) + kept real (10%) | about 200 + 15 |
| **test, books** | `t` cards: real pages from held-out books | about 40 |
| **test, hand** | Kevin's `render/samples/1` and `2` masks, plus any hand masks we draw | 2+ |

Rules:
- Split by **book**, not by page, so pages from one book never sit on both sides.
- No clipart id appears in both train and val.
- `splits.json` records the seed and every file path.

Report both test sets separately. "test, books" uses masks that large got right,
so it flatters large. "test, hand" is the honest check.

## Scripts to write (all in `pipeline/train/`)

| File | Runs on | Needs |
|---|---|---|
| `fetch_clipart.py` | server or laptop | `requests`, `cairosvg` |
| `prep_books.py` | CPU server | existing pipeline, Gemini key |
| `mask_books.py` | A40 | torch with CUDA, transformers |
| `review.html` + `review_server.py` | laptop | standard library only (a tiny HTTP server that saves decisions) |
| `make_composites.py` | laptop | numpy, opencv, pillow (already installed) |
| `make_splits.py` | laptop | standard library |

Training packages go in `pipeline/train/requirements.txt`, so the app image stays
the same.

## Timeline

| Time | Step | Who |
|---|---|---|
| 0:00 | Start `fetch_clipart.py`; start downloading books by hand | script + you |
| 0:25 | Reject bad clipart (10 min) | you |
| 0:35 | `prep_books.py` on the server (Gemini boxes, backgrounds) | script |
| 0:50 | `make_composites.py`, then check 30 by eye | script + you |
| 0:55 | Create the A40, run `mask_books.py` | script |
| 1:10 | Review real masks (15–20 min) | you |
| 1:30 | `make_splits.py`, then train (separate plan) | script |

**Cost:** about 0.5 GPU-hours for masking, about $1. Gemini: about 150 calls.

## Risks and fallbacks

| Risk | Fallback |
|---|---|
| Openclipart API blocked or slow | Openverse (`license=cc0,by`); or reuse cut-outs taken from the real masks |
| StoryWeaver downloads by hand take too long | Stop at about 8 books; lean more on composites |
| Gemini rate limit | Run 2 at a time; or draw boxes from the large model's automatic masks |
| A40 out of stock in `lax` | 1× A16 in `ewr` ($0.47/h); large-model masking takes about 3× longer, still minutes |
| Composites look fake | Raise feathering and texture; cut composites to 50% of the train set |
| Fine-tuned small doesn't beat zero-shot on "test, hand" | Keep zero-shot and report the result honestly |
