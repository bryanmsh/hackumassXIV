# Mirai cut-out model

A 7.8M-weight U-Net, trained from random weights, that turns a box around a subject into that subject's mask. It looks at a 320 px crop around the box (RGB plus one channel marking the box) and predicts the subject's pixels. It never draws or changes artwork: it outputs a mask only.

## Results

Scored on 100 held-out test pages built by `make_testset.py`: anime-segmentation cut-outs (archives `fg-05`, `bg-04`, never used in training) pasted 1–3 at a time onto scenes, the top one being the subject and its transparency the mask. Every segmenter gets the same prompt: the true mask's box grown by 5 %.

| segmenter | mean IoU | median IoU | pages < 0.5 | beats GrabCut | beats SAM 2.1 | median s/page |
| --- | --- | --- | --- | --- | --- | --- |
| GrabCut | 0.776 | 0.831 | 11 | – | – | 2.545 (CPU) |
| SAM 2.1 small | **0.906** | **0.932** | 1 | – | – | 0.100 |
| Mirai run A (photos) | 0.768 | 0.798 | 2 | 45 / 100 | 4 / 100 | 0.018 |
| **Mirai run B (photos + drawings)** | **0.897** | **0.921** | **1** | **66 / 100** | **27 / 100** | **0.020** |

Hardware: Google Colab, NVIDIA L4 (23 GB), torch 2.14.1+cu130, bf16, batch 32. GrabCut ran on Colab's CPU and the other two on the GPU, so the seconds are not like-for-like, and none of them is the 4-CPU server's speed.

**What the table says.** Trained on photos alone (run A), the model matches GrabCut on average and fails far less often (2 bad pages against 11). Adding drawn cut-outs (run B) lifts it to within 0.009 of SAM 2.1 on the mean while being about 5x faster.

**What it does not say.** The test pages are made the same way as run B's drawn training examples (from different archives), so run B is tested on the kind of picture it trained on. That flatters it. These are drawn subjects on drawn scenes, not picture-book pages; the gap to SAM 2.1 on real books is unmeasured. Say "held-out drawings" on any slide.

## Spot check on a real picture book

*Animal Homes* (the demo book; never used for training or for the scores above): the 45 subject boxes Gemini found on its 16 pages, given to run B, SAM 2.1 and GrabCut. There are no hand masks for this book, so this measures agreement with SAM 2.1 (IoU against SAM's mask), not accuracy.

| boxes | run B vs SAM 2.1 (mean / median) | GrabCut vs SAM 2.1 (mean / median) | run B under 0.5 |
| --- | --- | --- | --- |
| 36 single-subject boxes | **0.786 / 0.835** | 0.688 / 0.764 | 4 |
| 9 combined boxes ("frog and fish") | 0.306 | – | – |

Run B is closer to SAM than GrabCut is on 23 of the 36 single-subject boxes. GrabCut returns nothing at all on 5 small subjects (a snail, an ant, a fish); run B finds all of them. Looking at the outlines: run B matches SAM closely on clear animals (tortoises, frogs, bears, crocodile, gibbons, tiger, woodpecker, lizard) and is weaker in busy scenes (deer among trees bleeds into the forest, a cluster of tiny ants, an abstract "home"). Combined boxes do not apply: the pipeline builds a combined cut-out by joining the single ones, never from one big box. Median time per box at 3,000 px: run B 0.074 s, SAM 2.1 0.151 s (L4). Contact sheet and per-box numbers: `MyDrive/mirai-train/book_check/`.

**Verdict:** on real book pages run B is a clear step up from GrabCut but not a replacement for SAM 2.1. Keep SAM 2.1 on the server; run B is a credible fast fallback where SAM is unavailable.

## Training

| run | data | epochs | s/epoch | best val IoU (DUTS) |
| --- | --- | --- | --- | --- |
| A | DUTS-TR, 10,025 train / 528 val | 27 | 133.5 (162 first) | 0.929 |
| B | DUTS-TR + the same number of pasted drawings (4,000 cut-outs from `fg-00`, `fg-01`; 2,000 backgrounds from `bg-00`), from run A's best | 16 | 267 (302 first) | 0.936 |

Loss is binary cross-entropy plus Dice; AdamW, weight decay 1e-4, learning rate 0.001 on a cosine curve to 0. During run A the L4 sat at 100 % utilization with the CPU 85 % idle, so training is GPU-bound.

## Running it

The Colab notebook `colab.ipynb` does everything: it clones branch `model`, installs `requirements-train.txt` without replacing Colab's torch, downloads DUTS once to `MyDrive/mirai-train/`, times one epoch, trains runs A and B with `--resume` (a disconnect loses at most one epoch), builds the test set and scores. On a laptop:

```bash
python -m cutout_model.train --duts data/datasets/duts/DUTS-TR --out data/models/run_a --epochs 27
python -m cutout_model.make_testset --cutouts FG_DIR --backgrounds BG_DIR --out data/cutout_testset --count 100
CUTOUT_WEIGHTS=data/models/run_a/best.pt python -m cutout_model.evaluate data/cutout_testset --save-masks out
python -m pytest cutout_model/tests -q
```

`predict(image, box)` loads weights from `CUTOUT_WEIGHTS`, else `{DATA_DIR}/models/cutout.pt`, once per process, and returns a page-sized `uint8` mask (255 = subject). An empty or off-page box gives an empty mask. The run B weights are at `MyDrive/mirai-train/models/run_b/best.pt`.

## Limits

- Box prompts only. Clicks stay on SAM 2.1.
- Masks are predicted at 320 px and scaled up, so edges are softer than SAM's.
- Trained on photos and anime-style drawings, never on picture books.

## Credits

- DUTS: Wang et al., "Learning to Detect Salient Objects with Image-level Supervision", CVPR 2017. Annotations all rights reserved; research use.
- anime-segmentation (skytnt): CC0.
- Book Dash: CC BY 4.0 (named in the plan for picture-book test pages; not used in the end).
