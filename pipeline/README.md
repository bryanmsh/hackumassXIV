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

## Files written (Contract 3)

```text
{out_dir}/pages/{n}.png          master: RGB, 300 DPI, longer side at most 3,000 px
{out_dir}/pages/{n}_view.png     working copy: longer side at most 1,600 px
{out_dir}/masks/{n}_{hash}.png   8-bit, one channel, master size, 255 = subject
```

## Gemini findings (to post to the team)

| Question | Answer |
| --- | --- |
| Model name | not yet confirmed |
| Box format | not yet confirmed (expected `[ymin, xmin, ymax, xmax]`, 0 to 1000) |
| Four calls at once | not yet tested |

## Settings

| Setting | Values | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | your key | Read from the environment only. Never printed or logged |
| `GEMINI_MODEL` | a Flash model name | Empty uses `gemini-flash-latest` |
| `SEGMENTER` | `grabcut` (default), `stub`, `edgesam`, `sam2` | `edgesam` and `sam2` are not built: they raise `NotImplementedError` until the PyTorch code is added in `segment.py` |

## Adding the PyTorch segmenter (Bryan)

Fill in `_edgesam` or `_sam2` in `segment.py`. The docstring on `_edgesam` states the exact
input and output. Add torch to `pipeline/requirements.txt` yourself; nothing else changes.
