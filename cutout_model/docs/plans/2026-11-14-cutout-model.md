# Mirai Cut-out Model Implementation Plan (Google Colab, A100)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Steps marked **(a person, in Colab)** can't be done by an agent: hand them to the person with the exact cell to run, and wait for the numbers they report.

**Goal:** Train a small model from random weights that turns a box around a subject into that subject's mask, and measure it against GrabCut and SAM 2.1 on hand-labelled picture-book pages.

**Architecture:** A 7.8M-weight U-Net looks at a 320 px crop around the box (RGB plus one channel marking the box) and predicts the subject's pixels. It trains on DUTS-TR (10,553 photos with hand-drawn masks), then on drawn cut-outs pasted onto backgrounds. All code lives in a new top-level folder, `cutout_model/`. The pipeline reaches it through one new `SEGMENTER` value that Bryan adds.

**Tech Stack:**
- **Laptop:** code and CPU tests, Python 3.13 in a uv venv. The code must also run on the server's Python 3.11.
- **Google Colab, A100 runtime:** training and scoring, with Colab's preinstalled PyTorch built for CUDA.
- Libraries: NumPy, OpenCV, pytest. No torchvision in our code.

**Spec:** There is no separate design document. The Design section below records the decisions made with Andrew on 2026-11-14. This work is outside both project documents, by Andrew's explicit choice.

## Design

- **Why:** Andrew wants to try a self-trained model for the cut-out step. The honest expectation, agreed in conversation, is "better than GrabCut, not better than SAM 2.1". The value is a model the team trained and a numbers table for the pitch.
- **No SAM in training.** Labels come only from people (DUTS) or from transparency (pasted cut-outs).
- **Box prompts only.** The model handles the automatic cut-out for each Gemini box and the tidy-outline box. Anything with a click stays on SAM 2.1.
- **Order:** train on DUTS alone, score on 15 hand-labelled pages, then add pasted drawings and score again. The 15 pages are the only measure that counts.
- **Ship rule:** offer the model to Bryan only if its mean overlap on the 15 pages beats GrabCut's. Switch the server to it only if it is also within 0.05 of SAM 2.1 and the team agrees. Otherwise it stays a slide.

## Global Constraints

- Edit only `cutout_model/` and `CLAUDE_NOTES.md`. Never edit `pipeline/`, `api/`, `render/`, `checks/`, `web/`, `infra/`, `Dockerfile` or `compose.yaml`. Task 8 hands Bryan a change; it does not make it.
- Never create a file named `requirements.txt` in `cutout_model/`. The `Dockerfile` installs every `*/requirements.txt`, and a second torch pin would break the server image. The file is `requirements-train.txt`, and it does **not** list torch: Colab's preinstalled CUDA build must not be replaced.
- Code must run on Python 3.11 (the server image). No syntax newer than 3.11.
- Code never hard-codes a Colab or Drive path. Every path is a command argument or a setting.
- **Where files live:**

  | What | Where |
  | --- | --- |
  | Code | git, branch `model` |
  | Laptop venv | `cutout_model/.venv/` (ignored by the `.venv/` rule) |
  | Datasets during a Colab session | `/content/datasets/` (the runtime's fast local disk; wiped at disconnect) |
  | Dataset zips, checkpoints, logs, test pages, results | Google Drive, `MyDrive/mirai-train/`, which survives disconnects |

  None of it goes in git.
- Kevin's 20 evaluation pages and the demo book (Animal Homes) are never used for training, model selection or the 15 test pages.
- The model outputs a mask only. It never draws or changes artwork.
- Masks follow the project format: `uint8`, shape `(height, width)` of the master page, 255 = subject, 0 = everything else.
- Run every command from the repo root so `contracts`, `pipeline` and `cutout_model` import. In Colab the repo root is `/content/hackumassXIV`.
- Commit to branch `model` only, staging named files, and push `model` so Colab can pull it. Never push or merge to `main`. Colab only reads the repo; it never commits or pushes.
- After each task's commit, append an entry to `CLAUDE_NOTES.md` in the format in `CLAUDE.md`, with real numbers where there are any.
- Credits for the writeup: DUTS (Wang et al., CVPR 2017; annotations all rights reserved, research use), anime-segmentation (CC0), Book Dash (CC BY 4.0).

## Review Focus

1. **A box that is empty or off the page** (Gemini sometimes returns one): `predict` returns an all-zero mask and does not raise. Pinned in Tasks 1 and 5.
2. **The weights file is missing on the server:** `predict` raises `FileNotFoundError` naming the path, so `process_page` records a Failed page with a readable reason. Pinned in Task 5.
3. **Four pages processed at once** (`PAGE_CONCURRENCY=4`): concurrent `predict` calls load the model once and return the same mask as a single call. Pinned in Task 5.
4. **A training mask that is all black, or a different size from its photo:** the dataset still returns a valid example and training does not stop. Pinned in Task 3.
5. **A test page whose hand mask is missing, empty or the wrong size:** `score` raises `ValueError` naming the page before running any model. Pinned in Task 6.
6. **Colab disconnects mid-run:** rerunning the same command with `--resume` continues from the last finished epoch, with the same learning-rate schedule and an unbroken `log.csv`, and loses at most one epoch. Pinned in Task 4.

## Where to run

| Work | Where | Who |
| --- | --- | --- |
| Writing code, all `pytest` runs (tiny CPU data) | Laptop | Agent |
| Downloading datasets, timing, runs A and B, scoring | Colab, A100 runtime, `cutout_model/colab.ipynb` | A person, who reports the numbers back |
| Painting the 15 hand masks | Laptop, then uploaded to Drive | A person |

**Colab facts this plan relies on:**
- The A100 runtime has 40 GB of GPU memory (sometimes 80 GB), about 12 CPU cores and 80+ GB of RAM.
- It supports bf16.
- It uses compute units: Colab Pro, or pay-as-you-go. The runtime picker shows the rate per hour, so check it before starting. Budget about 3–4 A100 hours for the whole plan.
- Sessions end after about 90 minutes of no interaction with the page, or at about 12–24 hours.
- An A100 is sometimes not available. Then use an L4 (24 GB, also bf16) with `--batch 32`, and note it in the results table.

**One-time Colab setup (a person, about 10 minutes):**
1. Get Colab Pro, or buy compute units, at `colab.research.google.com/signup`. The free tier has no A100.
2. Make a GitHub fine-grained token at github.com → Settings → Developer settings → Fine-grained tokens:
   - repository access: only `bryanmsh/hackumassXIV`
   - permission: Contents, Read-only
   - expiry: 7 days
3. In Colab, open the key icon (Secrets) in the left bar. Add a secret named `GH_TOKEN` with the token, and turn on notebook access.
4. In Google Drive, make the folder `MyDrive/mirai-train/` with `datasets/`, `models/` and `cutout_testset/` inside it.
5. Open the notebook from GitHub: `https://colab.research.google.com/github/bryanmsh/hackumassXIV/blob/model/cutout_model/colab.ipynb`. The first time, Colab asks to connect to GitHub so it can read the private repo.
6. Runtime → Change runtime type → A100 GPU, with High-RAM on if it's offered → Save.

## File Structure

| File | Responsibility |
| --- | --- |
| `cutout_model/__init__.py` | Empty package marker |
| `cutout_model/requirements-train.txt` | Packages for training and scoring, without torch |
| `cutout_model/prompts.py` | Crop geometry and the 4-channel model input. Shared by training and inference; NumPy and OpenCV only |
| `cutout_model/model.py` | The U-Net |
| `cutout_model/data.py` | DUTS pairs to training examples |
| `cutout_model/train.py` | Loss, metric, checkpoints, resume, the training command |
| `cutout_model/predict.py` | `predict(image, box)`: load weights once, return a page-sized mask |
| `cutout_model/evaluate.py` | Score segmenters on the hand-labelled test pages |
| `cutout_model/paste.py` | Pasted-drawing examples |
| `cutout_model/colab.ipynb` | The Colab notebook: setup, data, timing, runs A and B, scoring |
| `cutout_model/README.md` | How to train and score, results table, credits |
| `cutout_model/tests/` | One test file per module, plus `conftest.py` |

---

### Task 1: Setup, crop geometry and model input

**Files:**
- Create: `cutout_model/__init__.py`, `cutout_model/requirements-train.txt`, `cutout_model/prompts.py`, `cutout_model/tests/__init__.py`, `cutout_model/tests/test_prompts.py`

**Interfaces:**
- Produces: `INPUT_SIZE = 320`, `MARGIN = 0.25`
- Produces: `crop_window(box, width, height, margin=MARGIN) -> tuple[int, int, int, int] | None`
- Produces: `build_input(image, box, margin=MARGIN, size=INPUT_SIZE) -> tuple[np.ndarray, tuple[int, int, int, int]] | None`

- [ ] **Step 1: Bring the branch up to date.** `git fetch origin && git switch model && git merge origin/main`. `model` was branched from main at `9a11d59`, so this is usually "Already up to date". Expected: `ls pipeline/sam.py` succeeds.

- [ ] **Step 2: Write `requirements-train.txt`** with exactly: `transformers==5.22.1`, `timm==1.0.31`, `numpy`, `opencv-python-headless`, `pillow`, `pymupdf`, `pydantic>=2,<3`, `pytest`, `huggingface_hub`. First line: `# torch and torchvision are not listed: Colab ships a CUDA build; on the laptop install them first (see README).` Transformers and timm are there only so `SEGMENTER=sam2` runs in Task 6.

- [ ] **Step 3: Create the laptop environment** (for writing code and running tests on CPU):

```bash
uv venv --python 3.13 cutout_model/.venv
uv pip install -p cutout_model/.venv torch==2.15.0 torchvision==0.29.2
uv pip install -p cutout_model/.venv -r cutout_model/requirements-train.txt
cutout_model/.venv/bin/python -c "import torch; print(torch.__version__)"
```

On Windows the interpreter is `cutout_model/.venv/Scripts/python.exe`. Use that wherever this plan says `cutout_model/.venv/bin/python`. Expected: a version is printed. A GPU is not needed on the laptop. If the `torch==2.15.0` pin has no wheel for this machine, drop the two version pins and record the installed versions in `CLAUDE_NOTES.md`.

- [ ] **Step 4: Write the failing tests** in `cutout_model/tests/test_prompts.py`:

```python
import numpy as np
from cutout_model.prompts import build_input, crop_window


def test_crop_window_grows_box_by_margin_and_clips():
    assert crop_window((100, 100, 300, 200), 1000, 800, margin=0.25) == (50, 75, 350, 225)
    assert crop_window((0, 0, 100, 100), 1000, 800, margin=0.25) == (0, 0, 125, 125)


def test_crop_window_orders_corners():
    assert crop_window((300, 200, 100, 100), 1000, 800, margin=0.25) == (50, 75, 350, 225)


def test_crop_window_is_none_for_empty_or_offpage_box():
    assert crop_window((500, 500, 500, 500), 1000, 800) is None
    assert crop_window((1200, 900, 1300, 950), 1000, 800) is None
    assert crop_window((999.5, 10, 1400, 60), 1000, 800) is None  # under 2 px left on the page


def test_build_input_shape_values_and_box_channel():
    image = np.full((800, 1000, 3), 255, np.uint8)
    x, window = build_input(image, (100, 100, 300, 200), size=64)
    assert x.shape == (4, 64, 64) and x.dtype == np.float32
    assert window == (50, 75, 350, 225)
    assert x[:3].min() == 1.0 and x[:3].max() == 1.0      # pixels scaled to 0..1
    assert x[3, 32, 32] == 1.0 and x[3, 0, 0] == 0.0      # inside the box / in the margin
    assert abs(x[3].mean() - 0.444) < 0.03                 # box is 2/3 of the window each way


def test_build_input_is_none_for_empty_box():
    image = np.zeros((800, 1000, 3), np.uint8)
    assert build_input(image, (500, 500, 500, 500)) is None
```

- [ ] **Step 5: Run** `cutout_model/.venv/bin/python -m pytest cutout_model/tests/test_prompts.py -q`. Expected: FAIL, `prompts` has no such names.

- [ ] **Step 6: Implement `prompts.py`.** `crop_window`: order the corners, clip the box to the page, return `None` if the clipped box is under 2 px wide or tall, then grow each side by `margin` times the clipped box's width (left, right) or height (top, bottom), round to integers, clip to the page. `build_input`: crop the window from `image`, stretch it to `size` by `size` with `cv2.INTER_AREA`, scale to 0..1, and add a fourth channel that is 1.0 where the (clipped) box falls inside the window, built at window size then resized with `cv2.INTER_NEAREST`. Channel order is R, G, B, box; layout is channels-first.

- [ ] **Step 7: Run the tests.** Expected: 5 passed.

- [ ] **Step 8: Commit.** `git add cutout_model/__init__.py cutout_model/requirements-train.txt cutout_model/prompts.py cutout_model/tests/__init__.py cutout_model/tests/test_prompts.py cutout_model/docs/plans/2026-11-14-cutout-model.md && git commit -m "cutout_model: crop geometry and model input"`

---

### Task 2: The U-Net

**Files:**
- Create: `cutout_model/model.py`, `cutout_model/tests/test_model.py`

**Interfaces:**
- Produces: `class UNet(torch.nn.Module)` with `__init__(self, in_channels=4, widths=(32, 64, 128, 256, 512))`. `forward` takes `(batch, 4, S, S)` with `S` divisible by 16 and returns logits `(batch, 1, S, S)`. `UNet.head` is the final 1x1 `nn.Conv2d`.

- [ ] **Step 1: Write the failing tests:**

```python
import torch
from cutout_model.model import UNet


def test_unet_shape_and_size():
    model = UNet()
    assert model(torch.zeros(2, 4, 64, 64)).shape == (2, 1, 64, 64)
    count = sum(p.numel() for p in model.parameters())
    assert 7_000_000 < count < 9_000_000


def test_unet_takes_the_real_input_size():
    assert UNet()(torch.zeros(1, 4, 320, 320)).shape == (1, 1, 320, 320)


def test_unet_head_is_a_one_by_one_conv():
    head = UNet().head
    assert isinstance(head, torch.nn.Conv2d) and head.kernel_size == (1, 1) and head.out_channels == 1
```

- [ ] **Step 2: Run** `cutout_model/.venv/bin/python -m pytest cutout_model/tests/test_model.py -q`. Expected: FAIL, no module `cutout_model.model`.

- [ ] **Step 3: Implement `UNet`.** Five levels at the given widths. Each level is two 3x3 convolutions, each followed by `BatchNorm2d` and `ReLU`. Go down with 2x2 max-pooling. Go up with bilinear upsampling by 2, concatenate the matching level's output, then one two-convolution block at that level's width. Finish with `head`.

- [ ] **Step 4: Run the tests.** Expected: 3 passed.

- [ ] **Step 5: Commit.** `git add cutout_model/model.py cutout_model/tests/test_model.py && git commit -m "cutout_model: U-Net"`

---

### Task 3: DUTS examples

**Files:**
- Create: `cutout_model/data.py`, `cutout_model/tests/conftest.py`, `cutout_model/tests/test_data.py`

**Interfaces:**
- Consumes: `build_input`, `crop_window`, `INPUT_SIZE`, `MARGIN` from Task 1.
- Produces: `find_pairs(root) -> list[tuple[Path, Path]]` (photo, mask), sorted by name.
- Produces: `split(pairs, val_fraction=0.05, seed=0) -> tuple[list, list]` (train, val).
- Produces: `components(mask, min_fraction=0.01) -> list[np.ndarray]` (bool arrays, largest first).
- Produces: `jitter_box(box, width, height, rng, amount=0.10) -> tuple[float, float, float, float]`.
- Produces: `make_example(image, target, box, margin=MARGIN, size=INPUT_SIZE) -> tuple[np.ndarray, np.ndarray] | None`: input `(4, size, size)` float32 and target `(1, size, size)` float32 of 0.0 and 1.0.
- Produces: `class CutoutDataset(torch.utils.data.Dataset)` with `__init__(self, pairs, train, size=INPUT_SIZE)`; items are `(input tensor, target tensor)`.
- Produces (tests): fixture `duts_root` in `conftest.py`.

- [ ] **Step 1: Write `conftest.py`.** Fixture `art(tmp_path)` (used in Task 7) writes 3 RGBA PNGs to `tmp_path/fg` (a 200 by 200 fully transparent image with an opaque solid-red filled circle of radius 80) and 2 solid-blue 600 by 800 JPEGs to `tmp_path/bg`, and returns `(tmp_path / "fg", tmp_path / "bg")`. Fixture `duts_root(tmp_path)` writes 8 pairs under `tmp_path/DUTS-TR/DUTS-TR-Image/{i}.jpg` and `.../DUTS-TR-Mask/{i}.png`: a 128 wide by 96 tall random-noise photo (seeded with `i`) with one solid-colour filled ellipse, centre `(64, 48)`, radii `(30, 20)`, and the matching 0/255 mask. It returns `tmp_path/DUTS-TR`.

- [ ] **Step 2: Write the failing tests** in `test_data.py`:

```python
import cv2
import numpy as np
import pytest
import torch
from cutout_model.data import CutoutDataset, components, find_pairs, jitter_box, split


def test_find_pairs_matches_photos_to_masks(duts_root):
    pairs = find_pairs(duts_root)
    assert len(pairs) == 8
    assert all(photo.stem == mask.stem for photo, mask in pairs)


def test_find_pairs_raises_when_the_folder_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_pairs(tmp_path / "nowhere")


def test_split_is_disjoint_and_repeatable(duts_root):
    pairs = find_pairs(duts_root)
    train, val = split(pairs, val_fraction=0.25, seed=0)
    assert len(train) == 6 and len(val) == 2 and not set(train) & set(val)
    assert split(pairs, val_fraction=0.25, seed=0) == (train, val)


def test_components_splits_objects_and_drops_specks():
    mask = np.zeros((100, 100), np.uint8)
    mask[10:40, 10:40] = 255      # 900 px
    mask[60:80, 60:80] = 255      # 400 px
    mask[95:97, 95:97] = 255      # 4 px, under 1% of the image
    parts = components(mask)
    assert [int(p.sum()) for p in parts] == [900, 400]


def test_jitter_box_stays_on_the_page_and_within_ten_percent():
    rng = np.random.default_rng(0)
    for _ in range(200):
        x0, y0, x1, y1 = jitter_box((100, 100, 300, 200), 320, 240, rng)
        assert 80 <= x0 <= 120 and 280 <= x1 <= 320
        assert 90 <= y0 <= 110 and 190 <= y1 <= 210


def test_val_items_have_the_right_shape_and_repeat(duts_root):
    data = CutoutDataset(find_pairs(duts_root), train=False, size=64)
    x, y = data[0]
    assert x.shape == (4, 64, 64) and x.dtype == torch.float32
    assert y.shape == (1, 64, 64) and set(y.unique().tolist()) <= {0.0, 1.0}
    assert 0.2 < float(y.mean()) < 0.6                       # a tight box is mostly subject
    again_x, again_y = data[0]
    assert torch.equal(x, again_x) and torch.equal(y, again_y)


def test_train_items_vary(duts_root):
    data = CutoutDataset(find_pairs(duts_root), train=True, size=64)
    assert any(not torch.equal(data[0][0], data[0][0]) for _ in range(5))


def test_black_mask_and_wrong_size_mask_still_give_an_example(duts_root):
    pairs = find_pairs(duts_root)
    cv2.imwrite(str(pairs[0][1]), np.zeros((96, 128), np.uint8))               # nothing labelled
    cv2.imwrite(str(pairs[1][1]), cv2.resize(cv2.imread(str(pairs[1][1]), 0), (64, 48)))  # half size
    data = CutoutDataset(pairs, train=False, size=64)
    for index in (0, 1):
        x, y = data[index]
        assert x.shape == (4, 64, 64) and float(y.sum()) > 0
```

- [ ] **Step 3: Run** `cutout_model/.venv/bin/python -m pytest cutout_model/tests/test_data.py -q`. Expected: FAIL, no module `cutout_model.data`.

- [ ] **Step 4: Implement `data.py`.**
  - `find_pairs`: `root/DUTS-TR-Image/*.jpg` matched to `root/DUTS-TR-Mask/{stem}.png`; photos without a mask are skipped.
  - `split`: shuffle with the seed; the validation part is `max(1, round(len(pairs) * val_fraction))` items, so it is never empty.
  - `components`: 8-connected regions of `mask > 127` with area at least `min_fraction` of the image, largest first.
  - `jitter_box`: move each edge by a uniform amount within `amount` times the box's width (left, right) or height (top, bottom), clipped to the page.
  - `make_example`: `build_input` for the input; crop `target` with the same window, resize with `cv2.INTER_NEAREST`. `None` when `build_input` is `None`.
  - `CutoutDataset.__getitem__`: read the photo as RGB; read the mask as grey and resize it to the photo with nearest-neighbour if the sizes differ. The target is one component: the largest when `train=False`, a random one when `train=True`. If `components` is empty, use the largest region of any size; if the mask is all black, return the item at `(index + 1) % len`. The box is the target's bounding box. When `train=True` also apply, in this order: horizontal flip with probability 0.5; brightness and contrast each scaled by a factor in 0.7 to 1.3; saturation scaled by 0.6 to 1.4; `jitter_box`; a margin drawn from 0.15 to 0.40. When `train=False`: no changes, margin `MARGIN`.
  - Randomness for `train=True` comes from a `np.random.default_rng()` created on first use inside the dataset object, so each data-loading worker gets its own stream.
  - Call `cv2.setNumThreads(0)` at import, so each of the 10 Colab workers doesn't start its own OpenCV thread pool.

- [ ] **Step 5: Run the tests.** Expected: 8 passed.

- [ ] **Step 6: Commit.** `git add cutout_model/data.py cutout_model/tests/conftest.py cutout_model/tests/test_data.py && git commit -m "cutout_model: DUTS training examples"`

---

### Task 4: Training command with resume, the Colab notebook, then the first run

**Files:**
- Create: `cutout_model/train.py`, `cutout_model/tests/test_train.py`, `cutout_model/colab.ipynb`

**Interfaces:**
- Consumes: `UNet` (Task 2); `find_pairs`, `split`, `CutoutDataset` (Task 3); `INPUT_SIZE`, `MARGIN` (Task 1).
- Produces: `bce_dice(logits, target) -> torch.Tensor`, `mean_iou(logits, target) -> float`, `pick_device() -> str`.
- Produces: `save_checkpoint(path, model, *, input_size, margin, epoch, val_iou) -> None`. The file is a dict with keys `model` (state dict), `widths` (list of int), `input_size`, `margin`, `epoch`, `val_iou`. This is the format of `best.pt` and the only format `predict` reads.
- Produces: `last.pt` holds the same six keys plus `optimizer`, `scheduler` (state dicts) and `best_val_iou`, so a run can resume.
- Produces: `main(argv=None) -> Path` (path of `best.pt`). Arguments: `--duts PATH` (required), `--out DIR` (required), `--epochs 40`, `--batch 64`, `--size 320`, `--workers 8`, `--lr 0.001`, `--resume` (flag).

- [ ] **Step 1: Write the failing tests:**

```python
import csv
import torch
from cutout_model import train


def test_bce_dice_is_low_when_right_and_high_when_wrong():
    target = torch.zeros(1, 1, 8, 8)
    target[..., 2:6, 2:6] = 1.0
    right = (target * 2 - 1) * 20.0
    assert float(train.bce_dice(right, target)) < 0.01
    assert float(train.bce_dice(-right, target)) > 1.0


def test_mean_iou():
    target = torch.zeros(2, 1, 4, 4)
    target[:, :, :2, :] = 1.0
    logits = torch.full((2, 1, 4, 4), -5.0)
    logits[0, :, :2, :] = 5.0          # first: exact, IoU 1.0
    logits[1, :, :1, :] = 5.0          # second: half of it, IoU 0.5
    assert abs(train.mean_iou(logits, target) - 0.75) < 1e-6


def test_main_trains_and_writes_checkpoint_and_log(duts_root, tmp_path):
    out = tmp_path / "run"
    best = train.main(["--duts", str(duts_root), "--out", str(out), "--epochs", "6",
                       "--batch", "4", "--size", "64", "--workers", "0"])
    assert best == out / "best.pt" and best.exists() and (out / "last.pt").exists()
    saved = torch.load(best, map_location="cpu", weights_only=True)
    assert set(saved) == {"model", "widths", "input_size", "margin", "epoch", "val_iou"}
    assert saved["input_size"] == 64 and saved["widths"] == [32, 64, 128, 256, 512]
    rows = list(csv.DictReader(open(out / "log.csv")))
    assert [row["epoch"] for row in rows] == ["1", "2", "3", "4", "5", "6"]
    assert set(rows[0]) == {"epoch", "train_loss", "val_iou", "seconds"}
    assert float(rows[-1]["train_loss"]) < float(rows[0]["train_loss"])


def test_resume_continues_after_a_disconnect(duts_root, tmp_path):
    out = tmp_path / "run"
    args = ["--duts", str(duts_root), "--out", str(out), "--batch", "4", "--size", "64", "--workers", "0"]
    train.main(args + ["--epochs", "4"])
    cut = list(csv.DictReader(open(out / "log.csv")))[:2]          # pretend it died after epoch 2
    with open(out / "log.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(cut[0]))
        writer.writeheader()
        writer.writerows(cut)
    last = torch.load(out / "last.pt", map_location="cpu", weights_only=False)
    last["epoch"] = 2
    torch.save(last, out / "last.pt")
    train.main(args + ["--epochs", "4", "--resume"])
    rows = list(csv.DictReader(open(out / "log.csv")))
    assert [row["epoch"] for row in rows] == ["1", "2", "3", "4"]


def test_resume_without_last_checkpoint_starts_fresh(duts_root, tmp_path):
    out = tmp_path / "fresh"
    train.main(["--duts", str(duts_root), "--out", str(out), "--epochs", "1", "--batch", "4",
                "--size", "64", "--workers", "0", "--resume"])
    assert [row["epoch"] for row in csv.DictReader(open(out / "log.csv"))] == ["1"]
```

- [ ] **Step 2: Run** `cutout_model/.venv/bin/python -m pytest cutout_model/tests/test_train.py -q`. Expected: FAIL, no module `cutout_model.train`.

- [ ] **Step 3: Implement `train.py`.**
  - `bce_dice`: binary cross-entropy on logits plus `1 - Dice`, where Dice is computed per example on `sigmoid(logits)` with 1.0 added to numerator and denominator, then averaged.
  - `mean_iou`: per example, threshold logits at 0, IoU against `target > 0.5`, with 1.0 when both are empty; average over the batch.
  - `pick_device`: `cuda`, else `mps`, else `cpu`.
  - `main`: `find_pairs`, then `split` with the defaults (5% validation, seed 0). `AdamW`, weight decay `1e-4`, learning rate following a cosine curve from `--lr` to 0 over all steps (`--epochs` times steps per epoch). A validation split smaller than one batch is still scored. After each epoch: score `mean_iou` on the validation split, append one row to `log.csv`, write `last.pt`, and write `best.pt` when `val_iou` is the best so far (the first epoch always writes it). Print the same row with `flush=True`, so Colab shows it live. Checkpoints record `margin=MARGIN`.
  - **Resume:** with `--resume` and an existing `{out}/last.pt`:
    1. Load the model, optimizer and scheduler state, and `best_val_iou`.
    2. Continue from `epoch + 1`.
    3. Rewrite `log.csv` to keep only rows up to that epoch, then keep appending.

    With `--resume` and no `last.pt`, start fresh. Write `last.pt` to a temporary name in the same folder, then `os.replace` it into place, so a disconnect in the middle of a save can't leave a broken file.
  - **On `cuda`:**
    - `torch.autocast("cuda", dtype=torch.bfloat16)`; no `GradScaler` is needed with bf16
    - `torch.backends.cudnn.benchmark = True`
    - `pin_memory=True`
    - when `--workers` > 0, also `persistent_workers=True` and `prefetch_factor=4`
  - End the file with `if __name__ == "__main__": main()`.

- [ ] **Step 4: Run the tests.** Expected: 5 passed (under a minute on CPU).

- [ ] **Step 5: Write `cutout_model/colab.ipynb`.** It's a notebook with one markdown cell at the top: what it is, "Runtime → Change runtime type → A100", and "after a disconnect, run cells 1–4 again, then rerun the cell that was running; `--resume` picks up". Then these code cells in order. Every path is a variable set in cell 2.

  1. **GPU check.**
     ```python
     !nvidia-smi
     import torch
     print(torch.__version__, torch.cuda.get_device_name(0))
     assert "A100" in torch.cuda.get_device_name(0), "Runtime → Change runtime type → A100 (or set BATCH = 32 for L4)"
     ```
  2. **Drive and paths.**
     ```python
     from google.colab import drive
     drive.mount("/content/drive")
     import os
     DRIVE = "/content/drive/MyDrive/mirai-train"
     LOCAL = "/content/datasets"
     REPO = "/content/hackumassXIV"
     BATCH, WORKERS = 64, min(10, os.cpu_count() - 2)
     os.makedirs(LOCAL, exist_ok=True)
     for d in ("datasets", "models", "cutout_testset"):
         os.makedirs(f"{DRIVE}/{d}", exist_ok=True)
     os.environ.update(HF_HOME="/content/hf", MODEL_CACHE_DIR="/content/hf/sam")
     ```
  3. **Get the code** (branch `model`, read-only token from Colab Secrets). The token is removed from the saved remote after cloning.
     ```python
     from google.colab import userdata
     token = userdata.get("GH_TOKEN")
     if not os.path.exists(REPO):
         !git clone -q -b model https://x-access-token:{token}@github.com/bryanmsh/hackumassXIV.git {REPO}
         !git -C {REPO} remote set-url origin https://github.com/bryanmsh/hackumassXIV.git
     else:
         !git -C {REPO} pull -q https://x-access-token:{token}@github.com/bryanmsh/hackumassXIV.git model
     %cd {REPO}
     !git log --oneline -1
     ```
  4. **Packages.** `!pip install -q -r cutout_model/requirements-train.txt`. Then check that torch is still Colab's CUDA build:
     ```python
     import torch
     print(torch.__version__, torch.cuda.is_available())
     ```
     If pip replaced torch, restart the runtime and pin it to the version this printed before installing.
  5. **Tests on the GPU box.** `!python -m pytest cutout_model/tests -q`. Expected: all pass.
  6. **DUTS.**
     - Download the zip to Drive once: if `{DRIVE}/datasets/DUTS-TR.zip` is missing, run `!wget -q -O {DRIVE}/datasets/DUTS-TR.zip http://saliencydetection.net/duts/download/DUTS-TR.zip`.
     - Every session, unzip it to the local disk: `!unzip -q -o {DRIVE}/datasets/DUTS-TR.zip -d {LOCAL}/duts`. Reading 10,553 small files from Drive during training would be far slower than from `/content`.
     - Print the file counts of `DUTS-TR-Image` and `DUTS-TR-Mask`. Expected: 10553 each.
  7. **Time one epoch.** `!python -m cutout_model.train --duts {LOCAL}/duts/DUTS-TR --out /content/timing --epochs 1 --batch {BATCH} --workers {WORKERS}`. Then `!nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv`.
  8. **Run A.** `EPOCHS_A = ...`, a number the person fills in from cell 7, then:
     `!python -m cutout_model.train --duts {LOCAL}/duts/DUTS-TR --out {DRIVE}/models/run_a --epochs {EPOCHS_A} --batch {BATCH} --workers {WORKERS} --resume 2>&1 | tee -a {DRIVE}/models/run_a.log`
  9. **Score.** `RUN = "run_a"`, then:
     - copy `{DRIVE}/cutout_testset` to `/content/cutout_testset`, leaving out `books/` and `raw/`
     - `!CUTOUT_WEIGHTS={DRIVE}/models/{RUN}/best.pt python -m cutout_model.evaluate /content/cutout_testset --save-masks {DRIVE}/cutout_testset/out_{RUN[-1]}`
     - copy `/content/cutout_testset/results.json` to `{DRIVE}/cutout_testset/results_{RUN[-1]}.json`
  10. **Drawn cut-outs (Task 7).** A cell that lists the archives in `skytnt/anime-segmentation` with `huggingface_hub.list_repo_files(..., repo_type="dataset")` and prints them with sizes. Then a cell where the person fills in `FG_FILES = [...]` (two) and `BG_FILES = [...]` (one); it downloads them to `{DRIVE}/datasets/anime_seg/`, skipping files already there, and unzips them to `{LOCAL}/anime_seg/fg` and `{LOCAL}/anime_seg/bg`.
  11. **Run B.** The same as cell 8, with `--cutouts {LOCAL}/anime_seg/fg --backgrounds {LOCAL}/anime_seg/bg --init {DRIVE}/models/run_a/best.pt --out {DRIVE}/models/run_b --epochs {EPOCHS_B}`. Then rerun cell 9 with `RUN = "run_b"`.

  Check the notebook is valid JSON with `cutout_model/.venv/bin/python -c "import json; json.load(open('cutout_model/colab.ipynb'))"`. Save it with no outputs.

- [ ] **Step 6: Commit and push.** `git add cutout_model/train.py cutout_model/tests/test_train.py cutout_model/colab.ipynb && git commit -m "cutout_model: training command with resume, Colab notebook" && git push origin model`. Colab clones from GitHub, so this push is required before the next step.

- [ ] **Step 7 (a person, in Colab): set up and time one epoch.** Do the one-time Colab setup in "Where to run" if it isn't done. Open the notebook, set the runtime to A100, and run cells 1–7. Report back:
  - the GPU name and memory
  - `torch.__version__`
  - the `seconds` from cell 7
  - GPU utilization

  If GPU utilization is under about 70%, data loading is the limit. Try `WORKERS = os.cpu_count()` and time it again. The A100's memory easily fits `--batch 64`. Keep 64, so the results can be compared with any run elsewhere.

- [ ] **Step 8 (a person, in Colab): run A.** Choose `EPOCHS_A` so that it times the measured seconds is at most 75 minutes, capped at 40. Run cell 8.
  - Keep the Colab tab open and click in it now and then, so the session isn't closed for inactivity.
  - If it disconnects, reconnect, run cells 1–4 and 6, then run cell 8 again. `--resume` continues from the last finished epoch.

  Continue with Tasks 5 and 6 on the laptop while it trains. When it ends, record the device, seconds per epoch, number of disconnects and final `val_iou` in `CLAUDE_NOTES.md`. The person reads `val_iou` from `{DRIVE}/models/run_a/log.csv`.

---

### Task 5: Prediction on a full page

**Files:**
- Create: `cutout_model/predict.py`, `cutout_model/tests/test_predict.py`

**Interfaces:**
- Consumes: `UNet`, `UNet.head` (Task 2); `build_input` (Task 1); `save_checkpoint` and its file format (Task 4).
- Produces: `weights_path() -> str`: the `CUTOUT_WEIGHTS` setting if set, else `os.path.join(DATA_DIR or "data", "models", "cutout.pt")`.
- Produces: `predict(image, box) -> np.ndarray`: `image` is RGB `uint8` `(height, width, 3)`; `box` is `(x0, y0, x1, y1)` in page pixels. Returns `uint8` `(height, width)`, 255 = subject.
- Produces: `_loaded: dict[str, tuple]`, the per-path model cache (tests read its length).

- [ ] **Step 1: Write the failing tests.** Add this fixture to `test_predict.py`: `all_subject(tmp_path, monkeypatch)` builds a `UNet`, sets `head.weight` to 0 and `head.bias` to 10.0 (so every pixel is predicted as subject), saves it with `save_checkpoint(path, model, input_size=64, margin=0.25, epoch=0, val_iou=0.0)`, sets `CUTOUT_WEIGHTS` to that path, clears `predict._loaded`, and returns the path.

```python
import threading
from pathlib import Path
import numpy as np
import pytest
from cutout_model import predict


def page():
    return np.random.default_rng(0).integers(0, 255, (300, 400, 3), dtype=np.uint8)


def test_mask_is_page_sized_and_covers_exactly_the_window(all_subject):
    mask = predict.predict(page(), (100, 100, 200, 180))
    assert mask.shape == (300, 400) and mask.dtype == np.uint8
    assert set(np.unique(mask).tolist()) <= {0, 255}
    expected = np.zeros((300, 400), np.uint8)
    expected[80:200, 75:225] = 255          # the box grown by the checkpoint's 0.25 margin
    assert np.array_equal(mask, expected)


def test_empty_or_offpage_box_gives_an_empty_mask(all_subject):
    assert not predict.predict(page(), (50, 50, 50, 50)).any()
    assert not predict.predict(page(), (900, 900, 950, 950)).any()


def test_missing_weights_raise_with_the_path(tmp_path, monkeypatch):
    missing = tmp_path / "none.pt"
    monkeypatch.setenv("CUTOUT_WEIGHTS", str(missing))
    predict._loaded.clear()
    with pytest.raises(FileNotFoundError, match="none.pt"):
        predict.predict(page(), (100, 100, 200, 180))


def test_default_path_follows_data_dir(monkeypatch):
    monkeypatch.delenv("CUTOUT_WEIGHTS", raising=False)
    monkeypatch.setenv("DATA_DIR", "/srv/data")
    assert Path(predict.weights_path()) == Path("/srv/data/models/cutout.pt")   # "\" on Windows


def test_four_threads_load_once_and_agree(all_subject):
    image, box = page(), (100, 100, 200, 180)
    results = [None] * 4
    def work(i):
        results[i] = predict.predict(image, box)
    threads = [threading.Thread(target=work, args=(i,)) for i in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(predict._loaded) == 1
    assert all(np.array_equal(results[0], other) for other in results[1:])
```

- [ ] **Step 2: Run** `cutout_model/.venv/bin/python -m pytest cutout_model/tests/test_predict.py -q`. Expected: FAIL, no module `cutout_model.predict`.

- [ ] **Step 3: Implement `predict.py`.** One module-level `threading.Lock` guards loading and the forward pass, as `pipeline/sam.py` does. Load with `torch.load(path, map_location=device, weights_only=True)`, build `UNet(widths=saved["widths"])`, `eval()`; the device is `cuda` when available, else `cpu`. `map_location` is what lets weights trained on Colab's A100 load on the server's CPU. Use the checkpoint's own `input_size` and `margin` in `build_input`. Run under `torch.inference_mode()`, take `sigmoid`, resize the probability map to the window's size with `cv2.INTER_LINEAR`, threshold at 0.5, and write 255 into a zero page-sized mask at the window. When `build_input` returns `None`, return the zero mask without loading the model.

- [ ] **Step 4: Run the tests.** Expected: 5 passed.

- [ ] **Step 5: Commit and push.** `git add cutout_model/predict.py cutout_model/tests/test_predict.py && git commit -m "cutout_model: page-sized prediction" && git push origin model`

---

### Task 6: Scoring on hand-labelled pages, then the first verdict

**Files:**
- Create: `cutout_model/evaluate.py`, `cutout_model/tests/test_evaluate.py`

**Interfaces:**
- Consumes: `predict` (Task 5); from the repo, `pipeline.segment.segment(image, box=...)`, `pipeline.masks.clean_mask`, `pipeline.masks.iou`, `pipeline.masks.mask_box`.
- Produces: `grow_box(box, width, height, amount=0.05) -> tuple[float, float, float, float]`.
- Produces: `load_testset(testset_dir) -> list[tuple[str, np.ndarray, np.ndarray]]` (name, RGB page, mask).
- Produces: `score(testset_dir, names=("grabcut", "sam2", "mirai"), save_masks=None) -> dict` with keys `pages` (list of `{"name", "iou": {segmenter: float}, "seconds": {segmenter: float}}`), `mean_iou`, `median_seconds`, `device`. It also writes the dict to `{testset_dir}/results.json`.
- Produces: `main(argv=None)`: `python -m cutout_model.evaluate TESTSET_DIR [--names ...] [--save-masks DIR]`, printing one row per page and the means.
- Test-set layout: `{testset_dir}/{name}.png` is a page; `{testset_dir}/{name}_mask.png` is its hand mask, the same size, white on the subject. Subfolders (such as `books/` and `raw/`) are ignored.

- [ ] **Step 1: Write the failing tests.** Fixture `testset(tmp_path)` writes `tmp_path/ball.png` (400 by 300, light background with mild noise in the range 200 to 255, one filled dark ellipse, centre `(200, 150)`, radii `(80, 50)`) and `tmp_path/ball_mask.png` (the same ellipse, 255 on 0), and returns `tmp_path`.

```python
import json
import os
import cv2
import numpy as np
import pytest
from cutout_model.evaluate import grow_box, load_testset, score


def test_grow_box_adds_five_percent_each_side_and_clips():
    assert grow_box((100, 100, 300, 200), 400, 300) == (90, 95, 310, 205)
    assert grow_box((0, 0, 400, 300), 400, 300) == (0, 0, 400, 300)


def test_score_ranks_grabcut_above_the_rectangle(testset, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "sam2")
    result = score(testset, names=("stub", "grabcut"))
    assert result["mean_iou"]["grabcut"] >= 0.9 > result["mean_iou"]["stub"]
    assert result["pages"][0]["name"] == "ball"
    assert set(result["pages"][0]["seconds"]) == {"stub", "grabcut"}
    assert json.load(open(testset / "results.json"))["mean_iou"] == result["mean_iou"]
    assert os.environ["SEGMENTER"] == "sam2"            # the caller's setting is put back


def test_score_saves_masks_when_asked(testset, tmp_path):
    out = tmp_path / "masks"
    score(testset, names=("grabcut",), save_masks=out)
    saved = cv2.imread(str(out / "ball_grabcut.png"), cv2.IMREAD_GRAYSCALE)
    assert saved.shape == (300, 400)


@pytest.mark.parametrize("damage", ["missing", "empty", "wrong_size"])
def test_bad_hand_mask_is_reported_by_page_name(testset, damage):
    path = testset / "ball_mask.png"
    if damage == "missing":
        path.unlink()
    elif damage == "empty":
        cv2.imwrite(str(path), np.zeros((300, 400), np.uint8))
    else:
        cv2.imwrite(str(path), np.full((30, 40), 255, np.uint8))
    with pytest.raises(ValueError, match="ball"):
        load_testset(testset)
```

- [ ] **Step 2: Run** `cutout_model/.venv/bin/python -m pytest cutout_model/tests/test_evaluate.py -q`. Expected: FAIL, no module `cutout_model.evaluate`.

- [ ] **Step 3: Implement `evaluate.py`.** For each page the prompt is `grow_box(mask_box(hand_mask), ...)`, the same for every segmenter. The name `mirai` calls `cutout_model.predict.predict(image, box)`; any other name sets `SEGMENTER` to it and calls `pipeline.segment.segment(image, box=box)`, restoring the previous value in a `finally`. Every result goes through `clean_mask` before `iou`. Before timing, make one untimed call per segmenter on the first page so model loading is not counted. `--save-masks` writes `{name}_{segmenter}.png`. `load_testset` treats every `*.png` directly in the folder not ending in `_mask.png` as a page and validates all masks before returning. `device` in the result is `torch.cuda.get_device_name(0)` when CUDA is available, else `cpu`.

- [ ] **Step 4: Run the tests.** Expected: 6 passed.

- [ ] **Step 5: Commit and push.** `git add cutout_model/evaluate.py cutout_model/tests/test_evaluate.py && git commit -m "cutout_model: score segmenters on hand-labelled pages" && git push origin model`

- [ ] **Step 6 (a person, on the laptop, about 45 minutes, can overlap with run A): build the test set.**
  1. Download 5 Book Dash books as PDFs from `bookdash.org/books/` into `data/cutout_testset/books/` (gitignored). Do not use these 5 anywhere else.
  2. Make page images: for each PDF, `cutout_model/.venv/bin/python -c "from pipeline.ingest import rasterize; rasterize('data/cutout_testset/books/NAME.pdf', 'data/cutout_testset/raw/NAME')"`. Pages appear in `raw/NAME/pages/{n}.png`.
  3. Pick 15 pages, 3 per book, each with one clear subject. Copy each to `data/cutout_testset/NAME_{n}.png`, using only letters, digits, `-` and `_` in names.
  4. For each, paint the subject white and everything else black in any image editor, at the same size, with antialiasing off, and save it as `data/cutout_testset/NAME_{n}_mask.png`. This is the method the build plan used for Kevin's sample masks at hour 0.
  5. Check locally: `cutout_model/.venv/bin/python -c "from cutout_model.evaluate import load_testset; print(len(load_testset('data/cutout_testset')))"`. Expected: 15, with no error.
  6. Upload the 30 PNGs (pages and masks, not `books/` or `raw/`) to `MyDrive/mirai-train/cutout_testset/` in Google Drive.

- [ ] **Step 7 (a person, in Colab): score run A.** When run A has finished, run notebook cell 9 with `RUN = "run_a"`. The first `sam2` call downloads its weights, and SAM 2.1 runs on the A100 here. Open several masks in `MyDrive/mirai-train/cutout_testset/out_a/` and look at them. Download `results_a.json` to the laptop at `data/cutout_testset/results_a.json`, so the agent can read it. Record the three mean overlaps and median seconds in `CLAUDE_NOTES.md`.

- [ ] **Step 8: Report to Andrew** with the table. This is the first verdict; Task 7 goes ahead unless he stops it here.

---

### Task 7: Pasted drawings, then the second run

**Files:**
- Create: `cutout_model/paste.py`, `cutout_model/tests/test_paste.py`
- Modify: `cutout_model/train.py` (new arguments), `cutout_model/tests/test_train.py` (one new test)

**Interfaces:**
- Consumes: `make_example`, `jitter_box` (Task 3); `main` and the checkpoint format (Task 4).
- Produces: `compose(background, cutouts, rng, canvas=512) -> tuple[np.ndarray, np.ndarray]`: `background` is RGB `uint8`; `cutouts` is a list of 1 to 3 RGBA `uint8` arrays; returns an RGB `uint8` `(canvas, canvas, 3)` picture and a bool `(canvas, canvas)` mask of the last cut-out pasted.
- Produces: `class PasteDataset(torch.utils.data.Dataset)` with `__init__(self, cutout_paths, background_paths, length, size=INPUT_SIZE)`; items have the same shapes and types as `CutoutDataset` items.
- Produces: new `train.main` arguments `--cutouts DIR`, `--backgrounds DIR`, `--paste-share 0.5`, `--init CHECKPOINT`.

- [ ] **Step 1: Write the failing tests** in `test_paste.py`. They use the `art` fixture from `conftest.py` (Task 3).

```python
import cv2
import numpy as np
import torch
from cutout_model.paste import PasteDataset, compose


def red_circle():
    art = np.zeros((200, 200, 4), np.uint8)
    cv2.circle(art, (100, 100), 80, (255, 0, 0, 255), -1)
    return art


def test_compose_mask_matches_the_pasted_pixels():
    blue = np.zeros((600, 800, 3), np.uint8)
    blue[..., 2] = 255
    rng = np.random.default_rng(0)
    for _ in range(20):
        picture, mask = compose(blue, [red_circle()], rng)
        assert picture.shape == (512, 512, 3) and mask.shape == (512, 512) and mask.dtype == bool
        assert 0.02 < mask.mean() < 0.60
        assert (picture[mask][:, 0] > 200).mean() > 0.90      # masked pixels are red (edges blend)
        assert (picture[~mask][:, 2] > 200).mean() > 0.95     # the rest is still blue


def test_compose_mask_is_the_top_cutout_only():
    blue = np.zeros((600, 800, 3), np.uint8)
    blue[..., 2] = 255
    green = red_circle()
    green[..., :3] = (0, 255, 0)
    picture, mask = compose(blue, [red_circle(), green], np.random.default_rng(1))
    assert (picture[mask][:, 1] > 200).mean() > 0.90          # only the last one pasted


def test_paste_dataset_items_match_the_duts_items(art):
    fg, bg = art
    data = PasteDataset(sorted(fg.glob("*.png")), sorted(bg.glob("*.jpg")), length=10, size=64)
    assert len(data) == 10
    x, y = data[3]
    assert x.shape == (4, 64, 64) and x.dtype == torch.float32
    assert y.shape == (1, 64, 64) and 0.05 < float(y.mean()) < 0.8
```

Add to `test_train.py`:

```python
def test_main_mixes_pasted_examples_and_starts_from_a_checkpoint(duts_root, art, tmp_path):
    fg, bg = art
    first = train.main(["--duts", str(duts_root), "--out", str(tmp_path / "a"), "--epochs", "1",
                        "--batch", "4", "--size", "64", "--workers", "0"])
    best = train.main(["--duts", str(duts_root), "--out", str(tmp_path / "b"), "--epochs", "1",
                       "--batch", "4", "--size", "64", "--workers", "0",
                       "--cutouts", str(fg), "--backgrounds", str(bg), "--init", str(first)])
    assert best.exists()
```

- [ ] **Step 2: Run** `cutout_model/.venv/bin/python -m pytest cutout_model/tests/test_paste.py cutout_model/tests/test_train.py -q`. Expected: FAIL, no module `cutout_model.paste`.

- [ ] **Step 3: Implement `paste.py` and the `train.py` arguments.**
  - `compose`: scale the background so its shorter side is at least `canvas`, take a random `canvas`-square crop. For each cut-out in order: crop it to its opaque bounding box, flip it left-right with probability 0.5, scale it so its longer side is 20% to 70% of `canvas`, place its centre uniformly within the middle 60% of the canvas, and alpha-blend it on. The mask is the last cut-out's alpha above 0.5, clipped to the canvas.
  - `PasteDataset.__getitem__`: choose a background and 1 to 3 cut-outs at random, `compose`, then build the example exactly as `CutoutDataset` does for `train=True` from the box step onward (`jitter_box`, margin from 0.15 to 0.40, `make_example`). Cut-out and background files are read on demand, not held in memory.
  - `train.main`: when `--cutouts` and `--backgrounds` are both given, the training set is the DUTS training set plus a `PasteDataset` whose length makes pasted examples `--paste-share` of the total (with 0.5, the same count as DUTS). Validation stays DUTS only. `--init` loads the checkpoint's `model` weights before training. When `--resume` finds a `last.pt` in `--out`, it wins over `--init`, so rerunning cell 11 after a disconnect continues run B instead of restarting it from run A.

- [ ] **Step 4: Run the tests.** Expected: all pass, including every earlier test file.

- [ ] **Step 5: Commit and push.** `git add cutout_model/paste.py cutout_model/train.py cutout_model/tests/test_paste.py cutout_model/tests/test_train.py cutout_model/tests/conftest.py && git commit -m "cutout_model: pasted-drawing examples" && git push origin model`

- [ ] **Step 6 (a person, in Colab): get the drawn cut-outs and backgrounds.** Run cells 1–4 (cell 3 pulls the new code), then cell 10.
  - The listing shows the archive names and sizes in `skytnt/anime-segmentation`. The whole set is 18 GB.
  - Fill in two foreground archives and one background archive, then run the download cell. The zips go to Drive once, and are unzipped to `/content` every session.
  - Expected: several thousand transparent PNGs in `fg/` and at least a thousand JPEGs in `bg/`.
  - Show three of each with `PIL.Image.open(...)` to confirm they are character cut-outs and scenes.

- [ ] **Step 7 (a person, in Colab): run B.** Time one epoch first, using cell 7 with the run B arguments: pasted examples use more CPU per item than DUTS photos. Then choose `EPOCHS_B` with the same rule as run A, at most 75 minutes, and run cell 11. The same disconnect rule as run A applies.

- [ ] **Step 8 (a person, in Colab): score run B.** Run cell 9 with `RUN = "run_b"`. Download `results_b.json` to the laptop at `data/cutout_testset/results_b.json`. Record both runs side by side in `CLAUDE_NOTES.md`.

---

### Task 8: Results, credits and the handoff to Bryan

**Files:**
- Create: `cutout_model/README.md`

- [ ] **Step 1: Write `cutout_model/README.md`:**
  - what the model is, in two sentences
  - how to run it: the one-time Colab setup, the notebook link and the order of cells, and laptop setup for tests
  - where the weights go
  - a results table from `results_a.json` and `results_b.json`: mean overlap and median seconds for GrabCut, SAM 2.1, run A and run B on 15 pages, with the device (Colab A100, or L4 if it was used)
  - the known limits: box prompts only; 320 px masks scaled up, so edges are softer than SAM's; photos and anime art in training, no picture books
  - the credits from Global Constraints

- [ ] **Step 2: Commit and push.** `git add cutout_model/README.md && git commit -m "cutout_model: results and credits" && git push origin model`

- [ ] **Step 3: Apply the ship rule** from the Design section and tell Andrew which case holds, with the table.

- [ ] **Step 4: If the better run beats GrabCut, send Bryan this change for `pipeline/`.** Do not make it yourself.

In `pipeline/segment.py`, above `_SEGMENTERS`:

```python
def _mirai(image, box, points) -> np.ndarray:
    """The team's own small model (cutout_model/). Box prompts only: anything with a
    click goes to SAM 2.1."""
    if box is None or points:
        return _sam2(image, box, points)
    from cutout_model.predict import predict
    return predict(image, box)
```

and `"mirai": _mirai` in `_SEGMENTERS`. One test for `pipeline/tests/test_segment.py`: with `SEGMENTER=mirai` and `cutout_model.predict.predict` patched to return a known mask, `segment(image, box=...)` returns that mask, and `segment(image, points=[(600, 450)])` calls `_sam2` instead. One row for the `SEGMENTER` table in `pipeline/README.md`.

To get the weights to the server:
1. Download `MyDrive/mirai-train/models/run_X/best.pt` from Drive.
2. `scp best.pt root@140.82.15.107:/opt/mirai/data/models/cutout.pt`. That's the mounted `data/` folder, where `predict` looks by default.

No new packages: torch is already in the image, and `map_location` loads GPU-trained weights on its CPU. Copying weights to the server and changing its `SEGMENTER` are Bryan's actions and need his go-ahead each time.

---

## Stop rules

- If run A is not scored two hours before the feature freeze (checkpoint 3), stop. Score GrabCut against SAM 2.1 on the 15 pages with `--names grabcut sam2` and use that table.
- If run A's mean overlap is more than 0.15 below GrabCut's, skip Task 7 unless Andrew says otherwise: pasted drawings are unlikely to close a gap that large.
- If Colab has no A100 when you need it, use an L4 with `BATCH = 32`. If it has neither, or compute units run out, run the same commands on the Vultr A40 (`vcg-a40-24c-120g-48vram`, `lax`, $1.71/hour) and destroy it afterwards.
- `main` and the server are untouched by Tasks 1 to 7. Nothing here can break the demo until Bryan chooses to merge Task 8's change.

## Not in this plan

- Sharpening edges with a GrabCut pass seeded from the model's mask. Decide after looking at the saved masks from Task 6.
- Click prompts for the model.
- Training on SAM-labelled picture-book pages (ruled out by the Design section).
- Speed measurements on the 4-CPU Vultr server. The table's seconds come from Colab's A100, which is far faster than the server's CPU; say so on any slide.
