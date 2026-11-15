# Trained weights for the local subject finder

Trained by the team from random weights on 2026-11-14 (no pretrained weights). Training and scoring are in
`subject_model/README.md`.

| File | Size | What | sha256 |
| --- | --- | --- | --- |
| `namer.pt` | 43.4 MB | ResNet-18 naming a crop with one of 347 names; validation top-1 0.590 | `6f04cafbc24f312b4c25a74154bcac3ff3a2b20e7533277f87f215fd02a50065` |
| `finder.pt` | 7.5 MB | half-width U-Net marking what stands out on a page; validation IoU 0.827 | `bbc6d532342bfd211a95867118cfdd5da4a0119e1e5a82fb385bfd8fd2d60a8e` |

## Using them

The code reads `NAMER_WEIGHTS` and `FINDER_WEIGHTS` when set, else `$DATA_DIR/models/namer.pt` and `finder.pt`
(`/opt/mirai/data/models/` on the server). Either point the two settings at these files, or copy them there.
A missing file raises `FileNotFoundError` naming the path.

- Needs torch and torchvision (already in the image). About 740 MB of memory with both loaded; the first call
  loads them (about 3 s); one lock means the two models never run at once. About 0.07 s a page on a CPU.
- The Dockerfile's `COPY . .` copies this folder into the image (about 51 MB); `.dockerignore` only skips `data`.

## For the cascade

`from subject_model.local import local_answer` gives a `pipeline.gemini.SubjectAnswer`, already through the
pipeline's own guard. **Do not use it unconditionally.** On Animal Homes, 4 of the 7 pages it called Ready had a
wrong cut-out (the whole pond, a burrow, a block of printed text, a banner); all 3 it was right on were pages
where the page text confirmed the name.

Gate on that: accept the local answer only when `decide_state(answer.page_kind, answer.candidates)` selects
exactly one candidate and that candidate's `reason` equals `subject_model.local.CONFIRMED` ("Stands out on the
page and the text names it."). Otherwise, or on any exception (including missing weights), ask Gemini.
On the 38 test pages that rule would answer 4 of 37 pages (about 1 in 10) with no API call, right on all 4.

## Credits

DomainNet (non-commercial research and education), anime-segmentation (CC0) and DUTS (research use): see the
credits in `subject_model/README.md`. The weights are derived from them.
