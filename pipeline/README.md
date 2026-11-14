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
