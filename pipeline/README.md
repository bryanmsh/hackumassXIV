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
| `sam.py` | SAM 2.1 small and EdgeTAM through transformers. The only file that imports torch |
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
| Time per call | 9.4 s for one page (1600 px view, no page text), one sample |

## Settings

| Setting | Values | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | your key | Read from the environment only. Never printed or logged |
| `GEMINI_MODEL` | a Flash model name | Empty uses `gemini-3.8-flash` |
| `SEGMENTER` | `grabcut` (default), `stub`, `sam2`, `edgetam` | `sam2` is the recommended setting on the server. `edgesam` raises: it has no installable package |
| `MODEL_CACHE_DIR` | a folder | Where model weights download on first use. Empty means `$DATA_DIR/models` (the mounted `data/` folder in Docker) |
| `TORCH_THREADS` | a number | Threads torch may use. Empty means every core |

## Segmenter: SAM 2.1 small

`SEGMENTER=sam2` runs Meta's SAM 2.1 small (`facebook/sam2.1-hiera-small`, Apache-2.0) on the
CPU through Hugging Face `transformers`. `pipeline/sam.py` is the only file that imports torch,
and it imports it lazily, so `stub` and `grabcut` run without torch installed.

How it works:
- **Load once.** The model loads on first use and stays loaded for the life of the process.
- **Encode once per page.** The image encoder, the slow part, runs once per page. Its output
  is cached by the page's pixel hash (the last 8 pages), so the up-to-3 Gemini boxes on a page,
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
(closer to Gemini's boxes), "click" is one point on the body. Torch limited to 4 threads to
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
