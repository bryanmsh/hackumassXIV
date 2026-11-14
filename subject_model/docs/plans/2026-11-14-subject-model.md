# Mirai Local Subject Finder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Steps marked **(a person)** can't be done by an agent: hand them to the person with the exact thing to do, and wait for what they report.

**Goal:** Produce, with models the team trained from random weights, the same JSON that `pipeline.gemini.choose_subjects` gets from Gemini: up to five subjects of a page, each with a name, synonyms, a rectangle and a confidence.

**Architecture:** Three parts in a new top-level folder, `subject_model/`. A *namer* (ResNet-18 classifier trained on DomainNet's drawn images, plus a `person` class and a `text` class) names a crop. A *finder* (a U-Net of the cut-out model's design, trained on whole photos with every labelled object marked) marks what stands out on a page, and its separate blobs become rectangles. A *chooser* combines them with the page text and a word table into the JSON. The cut-out model is not changed; the finder imports its code.

**Tech Stack:** Python 3.13 on the laptop (code must also run on the server's 3.11), PyTorch 2.15 (MPS on the laptop), torchvision 0.29 (ResNet-18 architecture and image transforms only, never pretrained weights), NumPy, OpenCV, Pillow, pytest.

**Spec:** There is no separate design document. The Design section below records the decisions made with Andrew on 2026-11-14, and the changes that came out of a review of this plan's first version the same day (marked *review*). This work is outside both project documents, by Andrew's explicit choice. Companion plan: `cutout_model/docs/plans/2026-11-14-cutout-model.md` on branch `model` (the Colab version; this plan was checked against its code at commit `73ff4be`).
**Not yet run:** the test code in this plan has been checked by hand and against measurements listed under "Measured on this laptop", but no task has been implemented from it. Where a faithful implementation fails a test, fix the plan's test or rule, say so in the dev log, and carry on.

## Design

- **Why:** Andrew wants Mirai to be able to run with no outside AI. Gemini stays the default; this is a fallback mode a judge can see working with Gemini switched off.
- **Agreed expectation:** clearly worse than Gemini. Boxes are usually right for one clear subject on a simple background, weak on busy scenes and on subjects that touch. Names come from a fixed list of about 345 and will often be wrong. Both modes are measured on the same pages and both rows are shown.
- **The JSON is the contract.** `choose_subjects(view_path, text)` returns a dict that `pipeline.gemini.SubjectAnswer` accepts: `things_on_page`, `page_kind` (`single`, `several`, `scene`), and `candidates`, each with `label`, `synonyms`, `box_2d` as `[ymin, xmin, ymax, xmax]` integers from 0 to 1000, `confidence` and `reason`.
- **The page text does the ranking, with limits (*review*).** The namer offers five guesses per blob, and a guess the page text names gets a high confidence. Class names turn up in story text about once every 36 words by chance, so three limits apply. The text confirms a guess only when the namer gives it 0.10 or more. A general word ("animal", "bird") confirms only a blob's first guess. Any other guess needs its own name or a specific synonym, and such a name goes to one blob. Two blobs whose first guess is the same thing may both be confirmed ("Birds build their homes"), so the teacher is asked, as in Gemini mode.
- **How the confidences meet the pipeline (*review*).** `process_page` pre-selects a candidate at 0.5 or more (`SELECT_MIN_CONFIDENCE`). Every confirmed candidate is 0.64 or more. An unconfirmed one reaches 0.5 only when the namer gives it 0.625 or more. Two or more at 0.5 turn the page into "Needs subject" with a combined cut-out on offer. A wrong page that arrives Ready is the costly mistake, because "Confirm all" accepts it. Task 6 pins these rules against the pipeline's real `decide_state`, and Task 9 counts how many of the 15 pages arrive Ready and wrong.
- **Two word lists, not one (*review*).** `never_a_label`: a guess that is skipped while its blob stays (parts of the body, plain shapes, `saw`). "She waved her hand" must not rename a child as a hand, and a child's portrait named `face` must not be thrown away. `not_a_subject`: classes that mean the blob is not a thing at all (printed text, marks, settings); a blob is dropped when they hold half the namer's probability.
- **Printed words are not a subject (*review*).** A finder marks high-contrast print. Three guards: the finder trains on photos placed on paper with lines of words that are not in the target; the namer has a `text` class in `not_a_subject`; and the claim rules above.
- **People:** DomainNet has no class for a whole person, and picture books are full of children. One extra class, `person`, is added from drawn character cut-outs. It is capped at 550 images, about one average class, so it does not become the default guess (*review*).
- **The finder is trained for whole pages (*review*).** The cut-out weights learned "the subject fills the box"; they are tried only as a free comparison. A page much wider than it is tall is searched as two halves, because some picture-book PDFs (Book Dash, for one) are two-page spreads.
- **What is scored is what ships (*review*).** `local_answer` holds exactly the lines the pipeline's hook will run, including the pipeline's own guard, and the scoring uses it. The chooser settles nested rectangles itself, because that guard would otherwise delete a large main subject that has two small things on it.
- **Honest numbers (*review*).** The 15 hand-labelled pages are picked to have one clear subject, the easy case for this mode. So the results give found, first choice and named for each mode, the page outcomes the teacher would get (Ready and right, Ready and wrong, asked, nothing), how the pages were picked, and a second measure on pages nobody picked: how often the local mode's first choice is one of Gemini's subjects.
- **What this needs from the cut-out work.** Tasks 1 to 6 need nothing from `cutout_model/`. Tasks 7 and 8 need its code (the cut-out plan's Tasks 1 to 4) on branch `model`, where it arrived on 2026-11-14 (commit `eed081f`); they need no cut-out checkpoint. Task 9 makes its own 15 test pages: the cut-out plan stopped hand-labelling picture-book pages and now scores on pasted anime cut-outs.

## Global Constraints

- Edit only `subject_model/` and the dev log. Never edit `cutout_model/`, `pipeline/`, `api/`, `render/`, `checks/`, `web/`, `infra/`, `Dockerfile` or `compose.yaml`. Task 11 hands Bryan a change; it does not make it.
- **Branch `model`, in the main folder.** The cut-out code is on `model`, so this work is too. Andrew chose to run it in the main checkout, which was switched from `andrew` to `model` on 2026-11-14 with nothing else working in it. While this plan runs, no other session works in this folder. Never switch the branch while a training run is going: the run's worker processes load code from the folder. Go back with `git switch andrew` only between runs. `MAIN=$(git rev-parse --show-toplevel)` is this folder; the dev log `CLAUDE_NOTES.md` and `.env` are here and are not in git.
- Commit staging named files. After each task's commit: `git pull --rebase origin model && git push origin model` (the cut-out work is pushed to the same branch, in another folder). Never run `git pull --rebase` while holding an unpushed merge: it copies the merged commits under new hashes. Never push or merge to `main`.
- After each task's commit, append an entry to `$MAIN/CLAUDE_NOTES.md` in the format in `CLAUDE.md`, with real numbers where there are any.
- Never create a file named `requirements.txt` in `subject_model/`. The `Dockerfile` installs every `*/requirements.txt`. The file is `requirements-train.txt`, and it does not list torch or torchvision: Colab's CUDA build must not be replaced, and the laptop installs them first.
- Code must run on Python 3.11. No syntax newer than 3.11.
- No module changes a global setting when it is imported (`cv2.setNumThreads`, `torch.set_num_threads`): the server imports these modules inside the API process.
- No path of a laptop, Colab or Drive folder is written into code. Every path is a command argument or a setting.
- Datasets, weights, test pages and the virtual environment stay out of git, under `data/` and `subject_model/.venv/`.
- Kevin's 20 evaluation pages and the demo book (Animal Homes) are never used for training, tuning, the test pages or the agreement pages. Task 9 Step 12 runs the demo book once as a rehearsal; nothing is tuned on what it shows.
- The chooser's numbers and the word lists are fixed before any test page is scored. A change made after the first scoring run is recorded in the README with the counts before and after.
- No pretrained weights anywhere: `resnet18(weights=None)`.
- Nothing here draws or changes artwork a child sees; outputs are names, rectangles and numbers. The rendered lines of words in Task 2 are training pictures only.
- Report results as counts ("9 of 15"), never percentages, as the spec does.
- Run every command from the repo root.
- One training run at a time on the laptop.
- Credits for the writeup: DomainNet (Peng et al., ICCV 2019; no named licence, offered under a fair-use notice for non-commercial research and education), anime-segmentation (CC0), DUTS (Wang et al., CVPR 2017, research use), and the test books' publishers with the licences noted in Task 9 Step 6.

## Review Focus

1. **A page that arrives Ready with the wrong thing chosen:** the text confirms only a guess the namer gives 0.10 or more; a general word confirms only a first guess; the pipeline's own guard leaves the answer unchanged. Pinned in Task 6 against the real `decide_state` and `_drop_non_subjects`.
2. **Printed words marked as a subject:** a blob that is mostly `text` or marks to the namer is dropped. Pinned in Task 6. The finder's training photos sit on paper with drawn words that are not in the target. Pinned in Task 8.
3. **A plural, a name hidden inside another word, or a ligature:** "horses", "houses" and "cookies" match `horse`, `house` and `cookie`; "cat" in "catch" and "short" for `shorts` do not; "ﬁsh" stored as a ligature matches `fish`. Pinned in Task 5.
4. **A page with no text** (the PDF had no text layer): the chooser still returns candidates, using each blob's top guess. Pinned in Task 6.
5. **A page where nothing, or nearly everything, stands out:** the answer is `page_kind: "scene"` with no candidates, not an error. Pinned in Tasks 6 and 7.
6. **An unreadable, grey or transparent training image** among 190,000 files: training carries on and transparent art is placed on white. Pinned in Task 1.
7. **A weights file missing on the server:** `name` and `find_blobs` raise `FileNotFoundError` naming the path. Pinned in Tasks 4 and 7. The web app hides any reason that contains `Error:`, so Task 11 asks the hook to turn it into a plain sentence.

## Where to run

| Work | Where | Who |
| --- | --- | --- |
| Writing code, every `pytest` run (tiny data, `--device cpu`) | Laptop, this folder on branch `model` | Agent |
| Downloads: DomainNet (7.6 GB), one anime-segmentation archive (1.3 GB), DUTS-TR (0.4 GB) | Laptop, `data/datasets/` | Agent, in the background |
| The namer run, then the finder run (at most 60 minutes each) | Laptop, Apple M5 Max through MPS | Agent, in the background |
| Choosing five test books and 15 pages, checking the subject rectangles | Laptop | A person |

The cut-out model trains in Colab under its own plan, so the laptop's GPU is free for these two runs.

**Measured on this laptop (2026-11-14, torch 2.15.0, synthetic batches on MPS):**

| What | Speed | One epoch | In 60 minutes |
| --- | --- | --- | --- |
| Namer, 160 px, batch 256 | about 490 images a second | about 6 minutes | 10 epochs |
| Namer, 128 px, batch 256 | about 900 | about 3.5 minutes | 17 epochs |
| Finder, widths 32 to 512, 320 px, batch 64 | about 22 | about 7.5 minutes | 8 epochs |
| Finder, widths 16 to 256, 256 px, batch 64 | about 100 | about 100 seconds | 35 epochs |

The GPU is the limit, not image loading (12 workers load over 3,000 images a second). So on the laptop the namer trains at 128 px and the finder at half width and 256 px. Download speed from this network was 33 MB a second from the DomainNet server.

**The better finder, if a person and the A100 are free (a person).** The full-width finder at 320 px is a few minutes of A100 time (an estimate, not measured). In the Colab session the cut-out plan set up, after its notebook cells 1 to 4 and 6: `!pip install -q -r subject_model/requirements-train.txt`, then `!python -m subject_model.finder_train --duts {LOCAL}/duts/DUTS-TR --out {DRIVE}/models/finder_run --epochs 40 --batch {BATCH} --workers {WORKERS}`. Not while a cut-out run is training on the same GPU. Download `best.pt` from Drive to `data/models/finder.pt` on the laptop. Nothing in this plan waits for it.

## File Structure

| File | Responsibility |
| --- | --- |
| `subject_model/__init__.py` | Empty package marker |
| `subject_model/requirements-train.txt` | Packages for training and scoring, without torch |
| `subject_model/namer_data.py` | Image folders to classifier examples; image loading shared with prediction |
| `subject_model/text_images.py` | Draws lines of words: the `text` class's pictures, and the words drawn on the finder's training photos |
| `subject_model/fit.py` | One training loop, used by the namer and the finder |
| `subject_model/namer_train.py` | The namer's training command |
| `subject_model/namer.py` | `name(image, mask)`: five guesses with probabilities |
| `subject_model/classes.txt` | The class names, one per line, written from the datasets |
| `subject_model/words.json`, `words.py` | Synonyms, the word lists, matching names against page text |
| `subject_model/local.py` | `choose_subjects`, `local_answer` and `label_crop`: the Gemini-shaped JSON |
| `subject_model/finder.py` | `find_blobs(image)`: whole page to rectangles and rough masks |
| `subject_model/finder_train.py` | The finder's training command |
| `subject_model/evaluate.py` | Counts on the hand-labelled pages; agreement with Gemini on unpicked pages |
| `subject_model/try_book.py` | Runs a whole book through the real page code with the local mode |
| `subject_model/README.md` | How to train and score, results, limits, credits |
| `subject_model/tests/` | One test file per module, plus `conftest.py` |

---

### Task 1: Workspace, downloads and namer examples

**Files:**
- Create: `subject_model/__init__.py`, `subject_model/requirements-train.txt`, `subject_model/namer_data.py`, `subject_model/tests/__init__.py`, `subject_model/tests/conftest.py`, `subject_model/tests/test_namer_data.py`

**Interfaces:**
- Produces: `INPUT_SIZE = 160`
- Produces: `class_name(folder) -> str`: the folder name in lowercase with `_` and `-` replaced by a space.
- Produces: `find_images(roots) -> tuple[list[tuple[Path, int]], list[str]]`: every image under `{root}/{class folder}/` for each root, with its class index, and the sorted class names (`class_name` of the folders; the same name in two roots is one class). Indexes come only from these sorted names.
- Produces: `split(items, val_fraction=0.05, seed=0) -> tuple[list, list]` (train, val).
- Produces: `load_image(path, at_least=None) -> np.ndarray | None`: RGB `uint8` `(height, width, 3)`, transparent pixels on white; `None` when the file cannot be read. With `at_least=N` a large JPEG may be decoded smaller, but never with a side under `N`.
- Produces: `to_square(image, size=INPUT_SIZE) -> np.ndarray`: padded to a square with white, resized, `uint8` `(size, size, 3)`.
- Produces: `to_tensor(square) -> torch.Tensor`: float32 `(3, size, size)`, scaled to -1..1.
- Produces: `class NamerDataset(torch.utils.data.Dataset)` with `__init__(self, items, train, size=INPUT_SIZE)`; items are `(tensor, int)`.
- Produces (tests): fixture `image_roots` in `conftest.py`.

- [ ] **Step 1 (a person, then the agent): check the workspace.** It was set up on 2026-11-14: this folder is on `model`, and the old untracked copy of the cut-out plan was moved to `data/old/`.
  1. Andrew says yes, once, to this work being committed and pushed on `model`. The project rule is to push only to your own branch, and `model` is shared with the cut-out work.
  2. Do not merge `main` into `model`. Bryan did that on 2026-11-14 (commit `aa0edea`), and the pipeline on `model` already has `_drop_non_subjects` and the two-argument `decide_state` this plan uses. Another merge of the shared branch is his and Andrew's call, not a step here.
  3. Check the folder, and bring in the newest pushes to `model`:

```bash
git branch --show-current                      # model
git status --short                             # only "?? subject_model/"
git pull --ff-only origin model
ls cutout_model/train.py && grep -c _drop_non_subjects pipeline/gemini.py
MAIN=$(git rev-parse --show-toplevel)
```

  Expected: `model`; the one untracked folder; `cutout_model/train.py` listed; a number above 0. If the branch is not `model`, or anything else is uncommitted, stop and tell Andrew.

- [ ] **Step 2: Write `requirements-train.txt`** with exactly: `numpy`, `opencv-python-headless`, `pillow`, `pymupdf`, `google-genai`, `pydantic>=2,<3`, `pytest`. First line: `# torch and torchvision are not listed: Colab ships a CUDA build; on the laptop install them first (see README).` (`pymupdf` is there because importing anything from `pipeline` loads `pipeline/ingest.py`.)

- [ ] **Step 3: Create the environment.**

```bash
uv venv --python 3.13 subject_model/.venv
uv pip install -p subject_model/.venv torch==2.15.0 torchvision==0.29.2
uv pip install -p subject_model/.venv -r subject_model/requirements-train.txt
subject_model/.venv/bin/python -c "import torch, torchvision; print(torch.__version__, torchvision.__version__, torch.backends.mps.is_available())"
```

Expected: `2.15.0 0.29.2 True` (these pins were installed on this laptop on 2026-11-14).

- [ ] **Step 4: Start the downloads in the background.** Use exactly these three DomainNet archives. The `clipart.zip` and `painting.zip` one level up, without `groundtruth/`, have no class folders and are useless here. Running a `curl` line again continues a broken download.

```bash
mkdir -p data/datasets/domainnet data/datasets/anime_seg
base=https://csr.bu.edu/ftp/visda/2019/multi-source
for name in groundtruth/clipart groundtruth/painting sketch; do
  curl -fL -C - --retry 5 -o data/datasets/domainnet/$(basename $name).zip $base/$name.zip
done
for d in clipart painting sketch; do for p in train test; do
  curl -fsSL -o data/datasets/domainnet/${d}_${p}.txt $base/domainnet/txt/${d}_${p}.txt
done; done
curl -fL -C - --retry 5 -o data/datasets/anime_seg/fg-05.zip https://huggingface.co/datasets/skytnt/anime-segmentation/resolve/main/data/fg-05.zip
curl -fL -C - --retry 5 -o data/datasets/DUTS-TR.zip http://saliencydetection.net/duts/download/DUTS-TR.zip
```

Expected sizes in bytes (`ls -l`): `clipart.zip` 1270909081, `painting.zip` 3679366174, `sketch.zip` 2633992926, `fg-05.zip` 1335862655; `DUTS-TR.zip` is about 392 MB. At the measured speed the lot takes under 10 minutes.

- [ ] **Step 5: Unzip, and remove DomainNet's duplicate images.** The archives hold 5,455 images the authors later listed as duplicates. Left in, copies of training images would land in the validation split.

```bash
for d in clipart painting sketch; do unzip -q -o data/datasets/domainnet/$d.zip -d data/datasets/domainnet; done
unzip -q -o data/datasets/anime_seg/fg-05.zip -d data/datasets/anime_seg
unzip -q -o data/datasets/DUTS-TR.zip -d data/datasets/duts
subject_model/.venv/bin/python -c "
import pathlib
root = pathlib.Path('data/datasets/domainnet')
keep = {line.split()[0] for f in root.glob('*_t*.txt') for line in f.read_text().splitlines() if line.strip()}
gone = [p for p in root.glob('*/*/*.jpg') if p.relative_to(root).as_posix() not in keep]
[p.unlink() for p in gone]
print('removed', len(gone), 'of', len(gone) + len(keep))"
```

Expected: `removed 5455 of 194978`. Afterwards `clipart/`, `painting/` and `sketch/` each hold 345 class folders, with 48,129, 72,266 and 69,128 images; `data/datasets/duts/DUTS-TR/DUTS-TR-Image` and `DUTS-TR-Mask` hold 10,553 files each; `data/datasets/anime_seg/fg/` holds 1,802 PNGs. Open three images from `clipart/` and `sketch/` to confirm they are drawings (`painting/` also holds some photographs), and three from `fg/` to confirm they are drawn characters on transparent backgrounds.

- [ ] **Step 6: Write `conftest.py`.** Fixture `image_roots(tmp_path)` returns `[tmp_path / "clipart", tmp_path / "extra"]` after writing (colours are RGB):
  - `clipart/cat/0..3.jpg`: 64 by 48, solid red `(255, 0, 0)`.
  - `clipart/dog/0..3.jpg`: 64 by 48, solid green `(0, 255, 0)`.
  - `clipart/dog/bad.jpg`: the bytes `b"not an image"`.
  - `clipart/Sea_Turtle/0.jpg`: 64 by 48, solid yellow `(255, 255, 0)`.
  - `extra/person/0..2.png`: 48 by 48 RGBA, fully transparent except an opaque blue `(0, 0, 255)` square at rows and columns 16 to 32.
  - `extra/cat/grey.png`: 48 by 48 single-channel grey, value 128.

- [ ] **Step 7: Write the failing tests** in `test_namer_data.py`:

```python
from collections import Counter
import cv2
import numpy as np
import torch
from subject_model.namer_data import NamerDataset, class_name, find_images, load_image, split, to_square


def test_class_names_are_plain_lowercase_words():
    assert class_name("Sea_Turtle") == "sea turtle" and class_name("teddy-bear") == "teddy bear"
    assert class_name("The_Mona_Lisa") == "the mona lisa" and class_name("t-shirt") == "t shirt"


def test_find_images_merges_roots_and_names_classes(image_roots):
    items, classes = find_images(image_roots)
    assert classes == ["cat", "dog", "person", "sea turtle"]
    assert Counter(classes[i] for _, i in items) == {"cat": 5, "dog": 5, "person": 3, "sea turtle": 1}


def test_split_is_disjoint_and_repeatable(image_roots):
    items, _ = find_images(image_roots)
    train, val = split(items, val_fraction=0.2, seed=0)
    assert len(val) == 3 and len(train) == 11 and not set(train) & set(val)
    assert split(items, val_fraction=0.2, seed=0) == (train, val)
    assert len(split(items[:4], val_fraction=0.05)[1]) == 1          # never empty


def test_load_image_puts_transparent_art_on_white_and_widens_grey(image_roots):
    person = load_image(image_roots[1] / "person" / "0.png")
    assert person.shape == (48, 48, 3)
    assert person[0, 0].tolist() == [255, 255, 255] and person[24, 24].tolist() == [0, 0, 255]
    assert load_image(image_roots[1] / "cat" / "grey.png").shape == (48, 48, 3)
    assert load_image(image_roots[0] / "dog" / "bad.jpg") is None


def test_load_image_may_decode_a_large_jpeg_smaller(tmp_path):
    cv2.imwrite(str(tmp_path / "big.jpg"), np.full((480, 640, 3), 200, np.uint8))
    assert load_image(tmp_path / "big.jpg").shape == (480, 640, 3)
    small = load_image(tmp_path / "big.jpg", at_least=100)
    assert small.shape[0] < 480 and min(small.shape[:2]) >= 100


def test_to_square_pads_with_white():
    wide = np.zeros((20, 40, 3), np.uint8)
    square = to_square(wide, size=32)
    assert square.shape == (32, 32, 3)
    assert square[0, 16].tolist() == [255, 255, 255] and square[16, 16].tolist() == [0, 0, 0]


def test_items_are_tensors_and_bad_files_are_skipped(image_roots):
    items, _ = find_images(image_roots)
    data = NamerDataset(items, train=False, size=32)
    for index in range(len(data)):                                    # includes bad.jpg
        x, y = data[index]
        assert x.shape == (3, 32, 32) and x.dtype == torch.float32
        assert -1.0 <= float(x.min()) and float(x.max()) <= 1.0 and isinstance(y, int)


def test_train_items_vary(image_roots):
    items, _ = find_images(image_roots)
    index = next(i for i, (path, _) in enumerate(items) if "person" in path.parts)
    data = NamerDataset(items, train=True, size=32)
    assert any(not torch.equal(data[index][0], data[index][0]) for _ in range(5))
```

- [ ] **Step 8: Run** `subject_model/.venv/bin/python -m pytest subject_model/tests/test_namer_data.py -q`. Expected: FAIL, no module `subject_model.namer_data`.

- [ ] **Step 9: Implement `namer_data.py`.**
  - `find_images` lists files ending `.jpg`, `.jpeg` or `.png` (any case) without opening them.
  - `split` shuffles with the seed; validation is `max(1, round(len(items) * val_fraction))` items.
  - `load_image` opens with Pillow. With `at_least`, call `image.draft("RGB", (at_least, at_least))` before loading, which makes a large JPEG decode at a half, a quarter or an eighth of its size. Any error while opening or decoding gives `None`.
  - `NamerDataset.__getitem__`: `load_image(path, at_least=2 * size)`; when it is `None`, return the item at `(index + 1) % len`. With `train=False`: `to_square` at `size`, `to_tensor`. With `train=True`: `to_square` at `size * 5 // 4` first, so training sees the same white padding as prediction; then, with `torchvision.transforms.v2` on the `uint8` tensor, a random resized crop to `size` covering 35% to 100% of the square with aspect ratio 3:4 to 4:3, horizontal flip with probability 0.5, colour jitter of 0.3 for brightness, contrast and saturation, greyscale with probability 0.1; then the same -1..1 scaling.

- [ ] **Step 10: Run the tests.** Expected: 8 passed.

- [ ] **Step 11: Commit.** `git add subject_model/__init__.py subject_model/requirements-train.txt subject_model/namer_data.py subject_model/tests subject_model/docs/plans/2026-11-14-subject-model.md && git commit -m "subject_model: namer examples"`, then pull, push and write the dev-log entry as Global Constraints says.

---

### Task 2: Lines of words, and the two extra classes

**Files:**
- Create: `subject_model/text_images.py`, `subject_model/tests/test_text_images.py`, `subject_model/classes.txt`

**Interfaces:**
- Consumes: `find_images` (Task 1).
- Produces: `FONT_DIRS`: the folders searched by default, `("/System/Library/Fonts/Supplemental", "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation")`.
- Produces: `find_fonts(dirs=FONT_DIRS) -> list[Path]`: the `.ttf` files in those folders whose name starts with one of `Arial`, `Georgia`, `Verdana`, `Trebuchet`, `Times New Roman`, `Comic Sans`, `Courier New`, `Tahoma`, `DejaVuSans`, `DejaVuSerif`, `LiberationSans`, `LiberationSerif`, sorted. A missing folder is skipped. (Most other system fonts draw symbols or boxes for Latin letters.)
- Produces: `draw_lines(image, rng, fonts) -> np.ndarray`: a copy of the RGB `uint8` image with 1 to 4 lines of 2 to 6 words drawn on it. `fonts` is a list of font files; when it is empty, Pillow's built-in font is used (`ImageFont.load_default(size)`, which scales). `rng` is a `np.random.Generator`.
- Produces: `text_page(rng, fonts, width=256, height=192) -> np.ndarray`: a plain light page, `uint8` `(height, width, 3)`, with 2 to 5 lines of words on it.
- Produces: `main(argv=None)`: `python -m subject_model.text_images OUT_DIR [--count 550] [--seed 0] [--fonts DIR ...]` writes `OUT_DIR/0000.png` and so on, and prints how many fonts it found.

- [ ] **Step 1: Write the failing tests:**

```python
import numpy as np
from subject_model import text_images
from subject_model.text_images import draw_lines, find_fonts, text_page


def changed(a, b):
    return float((a != b).any(axis=2).mean())


def test_text_page_is_a_light_page_with_marks_on_it():
    page = text_page(np.random.default_rng(0), [])
    assert page.shape == (192, 256, 3) and page.dtype == np.uint8
    assert int(page[0, 0].min()) >= 225                                # the corner is plain paper
    assert 0.01 < changed(page, np.broadcast_to(page[0, 0], page.shape)) < 0.6


def test_draw_lines_marks_a_copy_and_leaves_the_photo_alone():
    photo = np.full((240, 320, 3), 255, np.uint8)
    photo[:, 160:] = 0                                                 # half white, half black
    before = photo.copy()
    out = draw_lines(photo, np.random.default_rng(1), [])
    assert out.shape == photo.shape and np.array_equal(photo, before)
    assert 0.002 < changed(out, photo) < 0.5


def test_the_same_seed_gives_the_same_picture():
    a, b = (text_page(np.random.default_rng(3), []) for _ in range(2))
    assert np.array_equal(a, b)


def test_find_fonts_skips_missing_folders(tmp_path):
    assert find_fonts([tmp_path / "nowhere"]) == []


def test_main_writes_the_pictures(tmp_path):
    text_images.main([str(tmp_path / "text"), "--count", "5", "--fonts", str(tmp_path / "nowhere")])
    assert len(list((tmp_path / "text").glob("*.png"))) == 5
```

- [ ] **Step 2: Run** `subject_model/.venv/bin/python -m pytest subject_model/tests/test_text_images.py -q`. Expected: FAIL, no module `subject_model.text_images`.

- [ ] **Step 3: Implement `text_images.py`** with Pillow and NumPy only. Words come from a list of about 60 common story words kept in the module. One font and one size for all the lines of a picture.
  - `draw_lines`: letters 3% to 8% of the image's shorter side tall; the block starts at a random place where it fits (shrink the letters if it cannot); the ink is near-black where the image under the block is light on average and near-white where it is dark, so it reads like print.
  - `text_page`: the paper is one flat colour with every channel from 225 to 255; the lines start at least 8 px from the edges; letters are 8% to 16% of the page's height tall.

- [ ] **Step 4: Run the tests.** Expected: 5 passed.

- [ ] **Step 5: Build the two extra classes** once Task 1 Step 5 is done. If the anime archive is the one still downloading, wait for it up to 30 minutes rather than train without people.

```bash
subject_model/.venv/bin/python -m subject_model.text_images data/datasets/extra/text --count 550
subject_model/.venv/bin/python -c "
import pathlib, random, shutil
files = sorted(pathlib.Path('data/datasets/anime_seg/fg').glob('*.png'))
out = pathlib.Path('data/datasets/extra/person'); out.mkdir(parents=True, exist_ok=True)
for f in random.Random(0).sample(files, 550): shutil.copy(f, out / f.name)"
```

Expected: the first command reports at least 10 fonts on the laptop. Open five pictures from each folder: `text` shows lines of printed words on light paper; `person` shows drawn characters on transparent backgrounds.

- [ ] **Step 6: Write `classes.txt`:** `subject_model/.venv/bin/python -c "from subject_model.namer_data import find_images; print('\n'.join(find_images(['data/datasets/domainnet/clipart','data/datasets/domainnet/painting','data/datasets/domainnet/sketch','data/datasets/extra'])[1]))" > subject_model/classes.txt`. Expected: 347 lines, including `rabbit`, `sea turtle`, `teddy bear`, `t shirt`, `the mona lisa`, `person` and `text`. Every DomainNet archive has the same 345 classes, so a folder that has not arrived can be left out of this command.

- [ ] **Step 7: Commit.** `git add subject_model/text_images.py subject_model/tests/test_text_images.py subject_model/classes.txt && git commit -m "subject_model: lines of words, and the class list"`

---

### Task 3: Training loop and the namer's training command, then the run

**Files:**
- Create: `subject_model/fit.py`, `subject_model/namer_train.py`, `subject_model/tests/test_fit.py`, `subject_model/tests/test_namer_train.py`

**Interfaces:**
- Consumes: `find_images`, `split`, `NamerDataset`, `INPUT_SIZE` (Task 1).
- Produces: `pick_device() -> str` (`cuda`, else `mps`, else `cpu`), in `fit.py`.
- Produces: `fit(model, train_loader, val_loader, *, loss_fn, metric_fn, optimizer, scheduler, epochs, out_dir, save, device, amp=False) -> Path`. `loss_fn(output, target) -> Tensor`; `metric_fn(output, target) -> float`; `save(path, epoch, val_metric) -> None`, where `path` is a `pathlib.Path`. It steps `scheduler` after every batch. After every epoch, in this order, it: scores the validation set in eval mode (`metric_fn` averaged over the batches, weighted by batch size); appends a row to `{out_dir}/log.csv` with columns `epoch,train_loss,val_metric,seconds` and prints it with `flush=True`; calls `save` for `last.pt`; calls `save` for `best.pt` when `val_metric` is the best so far (always on the first epoch). Returns the path of `best.pt`.
- Produces: in `namer_train.py`, `build_model(num_classes) -> torch.nn.Module`, `top1(logits, target) -> float`, `save_namer(path, model, *, classes, input_size, epoch, val_top1) -> None`, `watch(model, batches, classes, device, names=("person", "text")) -> dict`, `main(argv=None) -> Path`. The checkpoint is a dict with keys `model`, `classes` (list of str), `input_size`, `epoch`, `val_top1`. `watch` gives, for each of `names` that is a class, `{"right": ..., "of": ..., "false_alarms": ..., "others": ...}`: how many of that class's examples were named right, and how many of the other examples were wrongly given its name. Arguments: `--roots` (one or more, required), `--out` (required), `--epochs 30`, `--batch 256`, `--size 160`, `--workers 12`, `--lr 0.2`, `--device` (default `pick_device()`).

- [ ] **Step 1: Write the failing tests.** `test_fit.py`:

```python
import csv
import torch
from torch.utils.data import DataLoader, TensorDataset
from subject_model.fit import fit


def test_fit_logs_every_epoch_saves_and_returns_best(tmp_path):
    torch.manual_seed(0)
    x = torch.randn(16, 3)
    loader = DataLoader(TensorDataset(x, (x.sum(1) > 0).long()), batch_size=4)
    model = torch.nn.Linear(3, 2)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(optimizer, max_lr=0.1, total_steps=4 * len(loader))
    saved = []

    def save(path, epoch, val_metric):
        saved.append((path.name, epoch))
        torch.save({"epoch": epoch}, path)

    best = fit(model, loader, loader, loss_fn=torch.nn.functional.cross_entropy,
               metric_fn=lambda output, target: float((output.argmax(1) == target).float().mean()),
               optimizer=optimizer, scheduler=scheduler, epochs=4, out_dir=tmp_path, save=save, device="cpu")
    assert best == tmp_path / "best.pt" and best.exists()
    assert saved[:2] == [("last.pt", 1), ("best.pt", 1)]              # the first epoch is always the best so far
    assert [name for name, _ in saved].count("last.pt") == 4
    rows = list(csv.DictReader(open(tmp_path / "log.csv")))
    assert [row["epoch"] for row in rows] == ["1", "2", "3", "4"]
    assert set(rows[0]) == {"epoch", "train_loss", "val_metric", "seconds"}
```

`test_namer_train.py`:

```python
import csv
import json
import math
import pytest
import torch
from subject_model import namer_train


def run(image_roots, out, *extra):
    return namer_train.main(["--roots", *map(str, image_roots), "--out", str(out), "--batch", "4",
                             "--size", "32", "--workers", "0", "--lr", "0.005", "--device", "cpu", *extra])


def test_top1():
    logits = torch.tensor([[2.0, 0.0, 0.0], [0.0, 3.0, 0.0], [0.0, 0.0, 1.0], [5.0, 0.0, 0.0]])
    assert namer_train.top1(logits, torch.tensor([0, 1, 2, 1])) == 0.75


def test_build_model_is_an_untrained_resnet18():
    model = namer_train.build_model(7)
    assert model.fc.out_features == 7
    assert 11_000_000 < sum(p.numel() for p in model.parameters()) < 12_000_000


def test_watch_counts_right_answers_and_false_alarms():
    class AlwaysPerson(torch.nn.Module):
        def forward(self, x):
            out = torch.zeros(len(x), 3)
            out[:, 2] = 1.0
            return out
    batches = [(torch.zeros(4, 3, 8, 8), torch.tensor([0, 1, 2, 2]))]
    assert namer_train.watch(AlwaysPerson(), batches, ["cat", "dog", "person"], "cpu") == {
        "person": {"right": 2, "of": 2, "false_alarms": 2, "others": 2}}


def test_main_trains_and_writes_checkpoint_log_and_watch(image_roots, tmp_path):
    torch.manual_seed(0)
    out = tmp_path / "run"
    best = run(image_roots, out, "--epochs", "4")
    assert best == out / "best.pt" and best.exists() and (out / "last.pt").exists()
    saved = torch.load(best, map_location="cpu", weights_only=True)
    assert set(saved) == {"model", "classes", "input_size", "epoch", "val_top1"}
    assert saved["classes"] == ["cat", "dog", "person", "sea turtle"] and saved["input_size"] == 32
    rows = list(csv.DictReader(open(out / "log.csv")))
    assert [row["epoch"] for row in rows] == ["1", "2", "3", "4"]
    assert all(math.isfinite(float(row["train_loss"])) for row in rows)
    assert set(json.load(open(out / "watch.json"))["person"]) == {"right", "of", "false_alarms", "others"}


def test_a_training_set_smaller_than_one_batch_is_refused(image_roots, tmp_path):
    with pytest.raises(ValueError, match="13"):                       # 13 training images, batch 64
        run(image_roots, tmp_path / "run", "--epochs", "1", "--batch", "64")
```

The training test does not assert that the loss went down. On 13 images in batches of 4 a ResNet-18 is not stable enough for that: in a 30-seed check at the test's old learning rate of 0.05, the loss fell in 3 runs. The real run's `log.csv` is where learning shows.

- [ ] **Step 2: Run** `subject_model/.venv/bin/python -m pytest subject_model/tests/test_fit.py subject_model/tests/test_namer_train.py -q`. Expected: FAIL, no module `subject_model.fit`.

- [ ] **Step 3: Implement `fit.py` and `namer_train.py`.**
  - `build_model` is `torchvision.models.resnet18(weights=None, num_classes=num_classes)`.
  - `main`: `find_images`, `split` with the defaults. The training loader has `shuffle=True` and `drop_last=True`: at 32 px a last batch of one image makes BatchNorm raise. When the training set is smaller than one batch, raise `ValueError` naming both counts. The validation loader keeps every image. Both loaders have `persistent_workers=True` when `--workers` is above 0.
  - Cross-entropy with label smoothing 0.1, SGD with momentum 0.9, Nesterov and weight decay `5e-5`, `OneCycleLR` with `max_lr=--lr` over all steps (`--epochs` times the training loader's length), then `fit` with `metric_fn=top1`. On `cuda` only: `torch.autocast("cuda", dtype=torch.bfloat16)` and `pin_memory=True`. No autocast on `mps`.
  - After `fit`, `main` runs `watch` on the validation loader, prints one line per watched class and writes the dict to `{out}/watch.json`.
  - End `namer_train.py` with `if __name__ == "__main__": main()`.

- [ ] **Step 4: Run the tests.** Expected: 6 passed.

- [ ] **Step 5: Commit.** `git add subject_model/fit.py subject_model/namer_train.py subject_model/tests/test_fit.py subject_model/tests/test_namer_train.py && git commit -m "subject_model: training loop and namer training"`

- [ ] **Step 6: Time one epoch** on the real data, at 128 px (see "Measured on this laptop"): `subject_model/.venv/bin/python -m subject_model.namer_train --roots data/datasets/domainnet/clipart data/datasets/domainnet/painting data/datasets/domainnet/sketch data/datasets/extra --out data/models/namer_timing --epochs 1 --size 128`. Read `seconds` from the printed row; about 210 is expected. If a DomainNet folder is still missing, leave it out of `--roots` here and in Step 7 and say so in the dev log and the README; do not wait for it.

- [ ] **Step 7: Start the namer run in the background,** detached so it outlives the shell and a closed lid. Choose `--epochs N` so that N times the measured seconds is at most 60 minutes, capped at 30.

```bash
mkdir -p data/models/namer_run
nohup caffeinate -is subject_model/.venv/bin/python -m subject_model.namer_train --roots data/datasets/domainnet/clipart data/datasets/domainnet/painting data/datasets/domainnet/sketch data/datasets/extra --out data/models/namer_run --epochs N --size 128 > data/models/namer_run/train.log 2>&1 &
echo $! > data/models/namer_run/pid
```

Continue with Tasks 4 to 7 while it trains. `last.pt` and `best.pt` are written every epoch, so a run killed late still leaves usable weights; a run killed early is started again. When it ends, record the device, seconds per epoch, final `val_metric` and the two `watch` lines in the dev log, and copy `data/models/namer_run/best.pt` to `data/models/namer.pt`. Then check the stop rules at the end of this plan.

---

### Task 4: Naming a crop

**Files:**
- Create: `subject_model/namer.py`, `subject_model/tests/test_namer.py`

**Interfaces:**
- Consumes: `build_model`, `save_namer` and the checkpoint format (Task 3); `to_square`, `to_tensor` (Task 1).
- Produces: `LOCK`: one `threading.Lock` for every local model. The finder (Task 7) uses the same one, so the two models never run at the same time.
- Produces: `weights_path() -> str`: the `NAMER_WEIGHTS` setting if set, else `os.path.join(DATA_DIR or "data", "models", "namer.pt")`.
- Produces: `WHITEN = True`: whether `name` whitens everything outside the mask. Task 9 measures both settings.
- Produces: `subject_crop(image, mask, pad=0.08, whiten=True) -> np.ndarray`: the rectangle around the mask, grown by `pad` of its longer side and clipped to the image; with `whiten`, every pixel outside the mask is set to white.
- Produces: `name(image, mask=None, top=5) -> list[tuple[str, float]]`: class names with probabilities, most likely first. `image` is RGB `uint8`; `mask` is a bool or 0/255 array of the same height and width, or `None`.
- Produces: `_loaded: dict[str, tuple]`, the per-path model cache.

- [ ] **Step 1: Write the failing tests.** Fixture `always_dog(tmp_path, monkeypatch)`: `build_model(3)` with `fc.weight` set to 0 and `fc.bias` to `[0.0, 5.0, 0.0]`, saved with `save_namer(path, model, classes=["cat", "dog", "person"], input_size=32, epoch=0, val_top1=0.0)`; sets `NAMER_WEIGHTS` to the path, clears `namer._loaded`.

```python
import threading
from pathlib import Path
import numpy as np
import pytest
from subject_model import namer


def page():
    return np.random.default_rng(0).integers(0, 255, (120, 200, 3), dtype=np.uint8)


def green_page_with_a_red_subject():
    image = np.zeros((100, 100, 3), np.uint8)
    image[..., 1] = 255                                   # green everywhere
    image[40:60, 40:60] = (255, 0, 0)                     # the subject is red
    mask = np.zeros((100, 100), bool)
    mask[40:60, 40:60] = True
    return image, mask


def test_name_returns_sorted_guesses(always_dog):
    guesses = namer.name(page())
    assert guesses[0][0] == "dog" and len(guesses) == 3
    assert abs(guesses[0][1] - 0.9867) < 0.001
    assert abs(sum(p for _, p in guesses) - 1.0) < 1e-4
    assert namer.name(page(), top=1) == guesses[:1]


def test_subject_crop_whitens_everything_outside_the_mask():
    crop = namer.subject_crop(*green_page_with_a_red_subject())
    assert crop.shape[0] > 20 and crop.shape[1] > 20      # padding was added
    assert not ((crop[..., 1] == 255) & (crop[..., 0] == 0)).any()      # no green left
    assert crop[0, 0].tolist() == [255, 255, 255]


def test_subject_crop_can_keep_the_surroundings():
    crop = namer.subject_crop(*green_page_with_a_red_subject(), whiten=False)
    assert crop[0, 0].tolist() == [0, 255, 0]


def test_empty_mask_falls_back_to_the_whole_image(always_dog):
    assert namer.name(page(), np.zeros((120, 200), bool)) == namer.name(page())


def test_missing_weights_raise_with_the_path(tmp_path, monkeypatch):
    monkeypatch.setenv("NAMER_WEIGHTS", str(tmp_path / "none.pt"))
    namer._loaded.clear()
    with pytest.raises(FileNotFoundError, match="none.pt"):
        namer.name(page())


def test_default_path_follows_data_dir(monkeypatch):
    monkeypatch.delenv("NAMER_WEIGHTS", raising=False)
    monkeypatch.setenv("DATA_DIR", "/srv/data")
    assert Path(namer.weights_path()) == Path("/srv/data/models/namer.pt")


def test_four_threads_load_once_and_agree(always_dog):
    image, results = page(), [None] * 4
    def work(i):
        results[i] = namer.name(image)
    threads = [threading.Thread(target=work, args=(i,)) for i in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(namer._loaded) == 1 and all(r == results[0] for r in results[1:])
```

- [ ] **Step 2: Run** `subject_model/.venv/bin/python -m pytest subject_model/tests/test_namer.py -q`. Expected: FAIL, no module `subject_model.namer`.

- [ ] **Step 3: Implement `namer.py`.** `LOCK` guards loading and the forward pass, as the lock in `pipeline/sam.py` does. Load with `torch.load(path, map_location=device, weights_only=True)`, `build_model(len(classes))`, `eval()`; the device is `cuda` when available, else `cpu`. `name`: when a non-empty mask is given use `subject_crop(image, mask, whiten=WHITEN)`, otherwise the image; then `to_square` at the checkpoint's `input_size`, `to_tensor`, forward under `torch.inference_mode()`, softmax, the `top` largest (all of them when there are fewer classes than `top`).

- [ ] **Step 4: Run the tests.** Expected: 7 passed.

- [ ] **Step 5: Commit.** `git add subject_model/namer.py subject_model/tests/test_namer.py && git commit -m "subject_model: name a crop"`

---

### Task 5: Synonyms, word lists and text matching

**Files:**
- Create: `subject_model/words.json`, `subject_model/words.py`, `subject_model/tests/test_words.py`

**Interfaces:**
- Consumes: `subject_model/classes.txt` (Task 2); `pipeline.gemini.SETTING_WORDS`.
- Produces: `SYNONYMS: dict[str, list[str]]`, and three `frozenset[str]`: `NEVER_A_LABEL` (a guess to skip; the blob stays), `NOT_A_SUBJECT` (classes that mean the blob is not a thing) and `GENERAL` (general-kind words such as `animal`). All are read from `words.json` (`{"synonyms": {...}, "never_a_label": [...], "not_a_subject": [...], "general": [...]}`).
- Produces: `forms(word) -> set[str]`: a lowercase word and its plurals.
- Produces: `match(text, names) -> str | None`: the first of `names`, in list order, that appears in `text` as whole words, in the form written or its plural; else `None`.

- [ ] **Step 1: Write the failing tests:**

```python
from pathlib import Path
from pipeline.gemini import SETTING_WORDS
from subject_model import words
from subject_model.words import GENERAL, NEVER_A_LABEL, NOT_A_SUBJECT, SYNONYMS, match

NOT_NAMES = {"saw", "can", "left", "light", "rose", "top", "watch", "back", "like", "will",
             "home", "water", "fly", "swing", "slide"}


def test_every_class_is_covered_and_no_synonym_is_a_trap():
    classes = [c for c in (Path(words.__file__).parent / "classes.txt").read_text().split("\n") if c]
    assert len(classes) == 347 and not NEVER_A_LABEL & NOT_A_SUBJECT
    for name in classes:
        if name in NEVER_A_LABEL or name in NOT_A_SUBJECT:
            continue
        names = SYNONYMS[name]
        assert 1 <= len(names) <= 5, name
        assert all(s == s.lower() and s != name for s in names), name
        assert not NOT_NAMES & set(names), name
        assert not SETTING_WORDS & {w for n in [name, *names] for w in n.split()}, name   # the pipeline drops these


def test_fixed_examples():
    assert "animal" in SYNONYMS["rabbit"] and "bird" in SYNONYMS["owl"] and "grape" in SYNONYMS["grapes"]
    assert {"child", "boy", "girl"} <= set(SYNONYMS["person"])
    assert {"text", "squiggle", "zigzag", "line", "ocean", "grass"} <= NOT_A_SUBJECT
    assert {"hand", "face", "eye", "saw", "circle", "the mona lisa"} <= NEVER_A_LABEL
    assert {"animal", "bird"} <= GENERAL
    assert not {"rabbit", "tree", "house", "person"} & (NEVER_A_LABEL | NOT_A_SUBJECT)


def test_match_uses_whole_words_and_plurals():
    assert match("The rabbits hid under the tree.", ["rabbit", "bunny"]) == "rabbit"
    assert match("Two children ran.", ["person", "child"]) == "child"
    assert match("The mice and the geese left.", ["mouse"]) == "mouse"
    assert match("A sea turtle swam.", ["sea turtle"]) == "sea turtle"
    assert match("FOXES!", ["fox"]) == "fox"
    assert match("The rabbit's ear.", ["rabbit"]) == "rabbit"


def test_match_handles_the_plurals_a_stemmer_gets_wrong():
    text = "The horses passed two houses, six cookies and three bunnies. Two snowmen waved."
    for name in ("horse", "house", "cookie", "bunny", "snowman"):
        assert match(text, [name]) == name
    assert match("She ate one grape.", ["grapes", "grape"]) == "grape"
    assert match("Her teddy bear fell.", ["teddy bear"]) == "teddy bear"


def test_match_reads_ligatures():
    text = "The ﬁsh saw a butterﬂy."                         # "fi" and "fl" stored as single characters
    assert match(text, ["fish"]) == "fish" and match(text, ["butterfly"]) == "butterfly"


def test_match_ignores_names_inside_other_words_and_shorter_words():
    assert match("He will catch the plant.", ["cat", "ant"]) is None
    assert match("A short walk.", ["shorts"]) is None
    assert match("The dog began to pant.", ["pants"]) is None
    assert match("", ["cat"]) is None


def test_match_prefers_list_order():
    assert match("a bunny and a rabbit", ["rabbit", "bunny"]) == "rabbit"
```

- [ ] **Step 2: Run** `subject_model/.venv/bin/python -m pytest subject_model/tests/test_words.py -q`. Expected: FAIL, no module `subject_model.words`.

- [ ] **Step 3: Write `words.json` by hand** from `classes.txt`.
  - `synonyms`: for each class give up to five other lowercase names a picture book might use, always including the general kind of thing (`owl`: `bird`, `animal`; `rabbit`: `bunny`, `hare`, `animal`). `person` gets `child`, `boy`, `girl`, `man`, `woman`. A class whose own name is a plural gets its singular (`grapes`: `grape`; also peas, drums, stairs, flip flops), except shorts, pants, scissors and pliers. No synonym may be a word that a story mostly uses as a verb or a describing word (the test's `NOT_NAMES`), and no class name or synonym may contain one of the pipeline's setting words (forest, sky, ground, woods and the like).
  - `never_a_label`: every part of a body (arm, beard, brain, ear, elbow, eye, face, finger, foot, goatee, hand, knee, leg, moustache, mouth, nose, skull, smiley face, toe, tooth); the plain shapes (circle, square, triangle, hexagon, octagon, diamond), so a red ball is not dropped as a circle; the three classes whose names start with "the" (the eiffel tower, the great wall of china, the mona lisa); and `saw`, `cooler` and `lighter`, whose names are common story words.
  - `not_a_subject`: `text`; marks (line, squiggle, zigzag, stitches, camouflage); settings and weather (grass, ocean, river, beach, mountain, pond, rain, hurricane, tornado, lightning and the like); and events with no single object (animal migration).
  - `general`: animal, bird, toy, food, fruit, vegetable, vehicle, tool, clothes, furniture, instrument, building, plant, insect, bug.
  - Things a story can be about, including tree and house, are in neither list.

- [ ] **Step 4: Implement `words.py`.**
  - `forms(word)`: the word itself, the word plus `s`, the word plus `es`, the word with a final consonant-plus-`y` turned into `ies`, and its irregular plural from a fixed table (`child`/`children`, `mouse`/`mice`, `goose`/`geese`, `man`/`men`, `woman`/`women`, `person`/`people`, `foot`/`feet`, `tooth`/`teeth`, `leaf`/`leaves`, `wolf`/`wolves`, `knife`/`knives`, `calf`/`calves`, `snowman`/`snowmen`).
  - `match`: first `unicodedata.normalize("NFKC", text)`, which turns ligature characters back into letters. Split the text and each name into lowercase words on anything that is not a letter. A name matches when its words appear as a consecutive run of the text's words, each text word being in `forms` of the name's word. The match goes one way only: "short" does not match `shorts`.

- [ ] **Step 5: Run the tests.** Expected: 7 passed.

- [ ] **Step 6: Commit.** `git add subject_model/words.json subject_model/words.py subject_model/tests/test_words.py && git commit -m "subject_model: word lists and text matching"`

---

### Task 6: The chooser, with a stand-in finder

**Files:**
- Create: `subject_model/local.py`, `subject_model/tests/test_local.py`

**Interfaces:**
- Consumes: `name` (Task 4); `SYNONYMS`, `NEVER_A_LABEL`, `NOT_A_SUBJECT`, `GENERAL`, `match` (Task 5); from `pipeline.gemini`: `SubjectAnswer`, `_drop_non_subjects`, `MAX_CANDIDATES`, `INSIDE_FRACTION`, `GROUP_HOLDS`, `DUPLICATE_IOU`. `find_blobs` (Task 7) is imported inside the function, so this task's tests pass before Task 7 exists.
- A *blob* is `tuple[tuple[float, float, float, float], np.ndarray]`: a rectangle `(x0, y0, x1, y1)` in pixels of the image, and a bool mask of the image's size.
- Produces: `choose_subjects(view_path, text, *, find=None, name=None) -> dict` in the JSON shape in the Design section. `find(image) -> list[blob]` and `name(image, mask) -> list[tuple[str, float]]` default to the real functions. Both are given the page as RGB.
- Produces: `local_answer(view_path, text) -> SubjectAnswer`: exactly what the pipeline's hook returns: `SubjectAnswer.model_validate(choose_subjects(view_path, text))` with `candidates` set to `_drop_non_subjects(candidates)[:MAX_CANDIDATES]`, both from `pipeline.gemini`.
- Produces: `label_crop(png_bytes, *, name=None) -> str`.
- Produces: `TEXT_BASE = 0.6`, `TEXT_GAIN = 0.4`, `NO_TEXT_SCALE = 0.8`, `MIN_TEXT_GUESS = 0.10`, `DROP_AT = 0.5`, `LABEL_MIN = 0.5`, `CONFIDENCE_CAP = 1.0`, `MAX_CANDIDATES = 5`.

- [ ] **Step 1: Write the failing tests.** Fixture `view(tmp_path)` writes a 1000 wide by 500 tall white PNG and returns its path. Fixture `small_words(monkeypatch)` sets, on `local`: `SYNONYMS` to `{"dog": ["puppy", "animal"], "rabbit": ["bunny", "animal"], "owl": ["bird", "animal"], "cat": ["kitten", "animal"], "tree": ["plant"]}`, `GENERAL` to `frozenset({"animal", "bird", "plant"})`, `NEVER_A_LABEL` to `frozenset({"hand"})` and `NOT_A_SUBJECT` to `frozenset({"squiggle", "text"})`. Helper `blob(x0, y0, x1, y1)` returns the rectangle with a 500 by 1000 bool mask that is true inside it. Helper `names(*answers)` returns a function of `(image, mask)` that gives the next list in `answers` on each call. Helper `pairs(answer)` returns `[(c["label"], c["confidence"]) for c in answer["candidates"]]`.

```python
import cv2
import numpy as np
from pipeline.gemini import SubjectAnswer, _drop_non_subjects
from pipeline.process import SELECT_MIN_CONFIDENCE, decide_state
from subject_model import local

SCENE = {"things_on_page": [], "page_kind": "scene", "candidates": []}


def two_blobs(image):
    return [blob(100, 50, 300, 250), blob(600, 100, 900, 400)]


def one_blob(image):
    return [blob(0, 0, 500, 500)]


def guesses():
    return names([("dog", 0.5), ("rabbit", 0.3), ("cat", 0.1)], [("owl", 0.9), ("cat", 0.05)])


def test_text_picks_the_name_and_orders_by_confidence(view, small_words):
    answer = local.choose_subjects(view, "The rabbit saw a bird.", find=two_blobs, name=guesses())
    SubjectAnswer.model_validate(answer)
    assert answer["page_kind"] == "several" and answer["things_on_page"] == ["dog", "owl"]
    first, second = answer["candidates"]
    assert first == {"label": "bird", "synonyms": ["owl", "animal"], "box_2d": [200, 600, 800, 900],
                     "confidence": 0.96, "reason": "Stands out on the page and the text names it."}
    assert second["label"] == "rabbit" and second["synonyms"] == ["bunny", "animal"]
    assert second["box_2d"] == [100, 100, 500, 300] and second["confidence"] == 0.72


def test_a_name_goes_to_one_blob_unless_it_is_their_first_guess(view, small_words):
    answer = local.choose_subjects(view, "The rabbit ran.", find=two_blobs,
                                   name=names([("cat", 0.5), ("rabbit", 0.15)], [("rabbit", 0.6), ("dog", 0.2)]))
    assert pairs(answer) == [("rabbit", 0.84), ("cat", 0.4)]
    assert answer["candidates"][1]["reason"] == "Stands out on the page."
    both = local.choose_subjects(view, "The rabbits ran.", find=two_blobs,
                                 name=names([("rabbit", 0.6)], [("rabbit", 0.5)]))
    assert pairs(both) == [("rabbit", 0.84), ("rabbit", 0.8)]


def test_a_general_word_or_an_unlikely_guess_is_not_confirmed(view, small_words):
    hungry = "The animals were hungry."
    assert pairs(local.choose_subjects(view, hungry, find=one_blob,
                                       name=names([("tree", 0.35), ("rabbit", 0.2)]))) == [("tree", 0.28)]
    assert pairs(local.choose_subjects(view, "The rabbit hid.", find=one_blob,
                                       name=names([("tree", 0.5), ("rabbit", 0.05)]))) == [("tree", 0.4)]
    first = local.choose_subjects(view, hungry, find=one_blob, name=names([("rabbit", 0.35), ("tree", 0.2)]))
    assert pairs(first) == [("animal", 0.74)] and first["candidates"][0]["synonyms"] == ["rabbit", "bunny"]


def test_no_text_uses_each_top_guess(view, small_words):
    answer = local.choose_subjects(view, "", find=two_blobs, name=guesses())
    assert pairs(answer) == [("owl", 0.72), ("dog", 0.4)]
    assert answer["candidates"][0]["reason"] == "Stands out on the page."


def test_nothing_found_is_a_scene(view, small_words):
    assert local.choose_subjects(view, "A quiet morning.", find=lambda image: [], name=names()) == SCENE


def test_one_subject_is_single(view, small_words):
    answer = local.choose_subjects(view, "", find=one_blob, name=names([("cat", 0.7)]))
    assert answer["page_kind"] == "single" and answer["candidates"][0]["box_2d"] == [0, 0, 1000, 500]


def test_a_guess_that_is_never_a_label_is_skipped_but_the_blob_stays(view, small_words):
    answer = local.choose_subjects(view, "", find=one_blob, name=names([("hand", 0.6), ("cat", 0.3)]))
    assert pairs(answer) == [("cat", 0.24)]
    assert local.choose_subjects(view, "", find=one_blob, name=names([("hand", 0.9)])) == SCENE


def test_a_blob_that_is_mostly_printed_words_or_marks_is_dropped(view, small_words):
    answer = local.choose_subjects(view, "The cat sat.", find=two_blobs,
                                   name=names([("text", 0.4), ("squiggle", 0.2), ("cat", 0.3)], [("cat", 0.7)]))
    assert pairs(answer) == [("cat", 0.88)] and answer["page_kind"] == "single"
    assert answer["candidates"][0]["box_2d"] == [200, 600, 800, 900] and answer["things_on_page"] == ["cat"]
    kept = local.choose_subjects(view, "", find=one_blob, name=names([("squiggle", 0.4), ("cat", 0.3)]))
    assert pairs(kept) == [("cat", 0.24)]                             # under DROP_AT the blob stays


def test_at_most_five_candidates(view, small_words):
    seven = lambda image: [blob(i * 100, 0, i * 100 + 90, 90) for i in range(7)]
    answer = local.choose_subjects(view, "", find=seven, name=names(*[[("cat", 0.9)]] * 7))
    assert len(answer["candidates"]) == 5


def test_the_pipeline_guard_leaves_the_answer_unchanged(view, small_words):
    nested = lambda image: [blob(100, 50, 900, 450), blob(200, 100, 300, 200), blob(600, 300, 700, 400)]
    answer = local.choose_subjects(view, "", find=nested,
                                   name=names([("cat", 0.7)], [("dog", 0.3)], [("owl", 0.2)]))
    assert pairs(answer) == [("cat", 0.56), ("dog", 0.24)]            # the big one stays; the least sure small one goes
    kept = _drop_non_subjects(SubjectAnswer.model_validate(answer).candidates)
    assert [c.label for c in kept] == ["cat", "dog"]


def test_what_the_pipeline_does_with_the_answers(view, small_words):
    def state(text, *guess_lists):
        find = lambda image: [blob(100 + 300 * i, 50, 300 + 300 * i, 250) for i in range(len(guess_lists))]
        answer = SubjectAnswer.model_validate(local.choose_subjects(view, text, find=find, name=names(*guess_lists)))
        return decide_state(answer.page_kind, answer.candidates)[:2]
    assert SELECT_MIN_CONFIDENCE == 0.5
    assert state("The rabbit ran.", [("rabbit", 0.3)]) == ("ready", [0])              # confirmed: 0.72
    assert state("", [("rabbit", 0.5)]) == ("needs_subject", [])                      # 0.4: the teacher is asked
    assert state("The rabbits ran.", [("rabbit", 0.6)], [("rabbit", 0.5)]) == ("ready", [0, 1])   # two: asked, with a combined cut-out


def test_the_cap_keeps_every_page_for_the_teacher(view, small_words, monkeypatch):
    monkeypatch.setattr(local, "CONFIDENCE_CAP", 0.49)
    answer = local.choose_subjects(view, "The rabbit saw a bird.", find=two_blobs, name=guesses())
    assert [c["confidence"] for c in answer["candidates"]] == [0.49, 0.49]


def test_find_and_name_get_rgb(tmp_path, small_words):
    cv2.imwrite(str(tmp_path / "red.png"), np.full((50, 100, 3), (0, 0, 255), np.uint8))     # OpenCV writes BGR
    seen = []
    def find(image):
        seen.append(image[0, 0].tolist())
        return []
    local.choose_subjects(tmp_path / "red.png", "", find=find, name=names())
    assert seen == [[255, 0, 0]]


def test_local_answer_is_what_the_hook_returns(view, monkeypatch):
    def candidate(label, box_2d, confidence):
        return {"label": label, "synonyms": [], "box_2d": box_2d, "confidence": confidence, "reason": ""}
    raw = {"things_on_page": ["cat"], "page_kind": "single",
           "candidates": [candidate("forest", [500, 500, 900, 900], 0.9), candidate("cat", [0, 0, 400, 400], 0.7)]}
    monkeypatch.setattr(local, "choose_subjects", lambda view_path, text: raw)
    answer = local.local_answer(view, "")
    assert isinstance(answer, SubjectAnswer) and [c.label for c in answer.candidates] == ["cat"]   # the guard ran


def test_label_crop_names_only_what_the_namer_is_sure_of(small_words, view):
    png = open(view, "rb").read()
    assert local.label_crop(png, name=lambda image, mask=None: [("dog", 0.6), ("hand", 0.2)]) == "dog"
    assert local.label_crop(png, name=lambda image, mask=None: [("hand", 0.5), ("dog", 0.3)]) == ""
    assert local.label_crop(png, name=lambda image, mask=None: []) == ""
```

- [ ] **Step 2: Run** `subject_model/.venv/bin/python -m pytest subject_model/tests/test_local.py -q`. Expected: FAIL, no module `subject_model.local`.

- [ ] **Step 3: Implement `local.py`.** A guess's *names* are `[class] + SYNONYMS.get(class, [])`.
  1. Read the page as RGB. For each blob from `find(image)`, in order: `guesses = name(image, mask)`. Drop the blob when there are no guesses, or when the probabilities of its guesses that are in `NOT_A_SUBJECT` add up to `DROP_AT` or more. Its *kept* guesses are the ones in neither `NOT_A_SUBJECT` nor `NEVER_A_LABEL`, in order; drop the blob when there are none. `things_on_page` is the first kept guess of each blob that stays, without repeats, at most 10.
  2. Find what the text confirms. Only a guess with probability `MIN_TEXT_GUESS` or more can be confirmed.
     - First guesses: for every blob, if `match(text, names)` of its first kept guess finds a name, the blob is confirmed with that guess and that name. Several blobs may be confirmed with the same name this way.
     - Other guesses, for blobs still unconfirmed: a guess can be confirmed only by a name that is not in `GENERAL`. Take these (blob, guess) matches highest probability first (the earlier blob on a tie). A match is used when its blob is still unconfirmed and its name has not been used by any blob yet.
  3. A confirmed blob: `label` is the matched name, `synonyms` are the class's other names in that order, `confidence` is `min(1.0, TEXT_BASE + TEXT_GAIN * p)`, `reason` is `"Stands out on the page and the text names it."`
  4. An unconfirmed blob: `label` is its first kept guess, `synonyms` is that class's table entry, `confidence` is `NO_TEXT_SCALE * p`, `reason` is `"Stands out on the page."`
  5. `box_2d` is the rectangle as `[ymin, xmin, ymax, xmax]`, each scaled to 0..1000 by the image's height or width and rounded to an integer.
  6. Cap every confidence at `CONFIDENCE_CAP`, round to 2 places, and sort most confident first (blob order on a tie).
  7. Settle the rectangles so the pipeline's guard has nothing to remove. While two rectangles overlap by `DUPLICATE_IOU` or more, remove the less confident. While some candidate's rectangle holds `GROUP_HOLDS` or more others (one rectangle *holds* another when `INSIDE_FRACTION` of the other's area is inside it), remove the least confident of that candidate and the ones it holds, and look again.
  8. Keep `MAX_CANDIDATES`. `page_kind` is `scene` for no candidates, `single` for one, `several` for more.

  `label_crop` decodes the PNG and takes the first guess from `name(image, None)` that is in neither list; it returns that name when its probability is `LABEL_MIN` or more, else `""` (the web app then shows "Unlabeled" and the teacher types it).

- [ ] **Step 4: Run the tests.** Expected: 15 passed.

- [ ] **Step 5: Commit.** `git add subject_model/local.py subject_model/tests/test_local.py && git commit -m "subject_model: Gemini-shaped answer from local models"`

---

### Task 7: The finder

**Needs:** `cutout_model/prompts.py`, `model.py`, `data.py` and `train.py` on branch `model` (the cut-out plan's Tasks 1 to 4; they arrived in commit `eed081f`). Check with `git pull --rebase origin model && ls cutout_model/prompts.py cutout_model/model.py cutout_model/data.py cutout_model/train.py`. If they are not there, see the stop rules; do not write them here.

**Files:**
- Create: `subject_model/finder.py`, `subject_model/tests/test_finder.py`

**Interfaces:**
- Consumes: `LOCK` (Task 4); `cutout_model.prompts.build_input(image, box, margin, size)`, which returns `(input, window)`; `cutout_model.model.UNet`; in tests, `cutout_model.train.save_checkpoint` and its checkpoint format (keys `model`, `widths`, `input_size`, `margin`, `epoch`, `val_iou`).
- Produces: `MAX_COVER = 0.60`, `MIN_BLOB = 0.005`, `MAX_BLOBS = 5`, `WIDE = 1.5`.
- Produces: `blobs_from_map(prob, width, height) -> list[blob]`: `prob` is a float array of any size with values 0 to 1; the result is for an image `width` by `height`, largest blob first.
- Produces: `weights_path() -> str`: the `FINDER_WEIGHTS` setting if set, else `os.path.join(DATA_DIR or "data", "models", "finder.pt")`.
- Produces: `_probability(image) -> np.ndarray`: the model's map for one RGB image, values 0 to 1, at the checkpoint's input size.
- Produces: `find_blobs(image) -> list[blob]`; `_loaded: dict[str, tuple]`.

- [ ] **Step 1: Write the failing tests.** Fixture `flat_finder(tmp_path, monkeypatch)` returns a function that takes a bias value, builds a `UNet` with `head.weight` 0 and `head.bias` set to it, saves it with `save_checkpoint(path, model, input_size=64, margin=0.25, epoch=0, val_iou=0.0)`, sets `FINDER_WEIGHTS`, and clears `finder._loaded`.

```python
import numpy as np
import pytest
from subject_model import finder


def two_rectangles():
    prob = np.zeros((100, 200), np.float32)
    prob[10:40, 10:60] = 1.0          # 1,500 px
    prob[60:90, 120:190] = 1.0        # 2,100 px
    prob[0:2, 198:200] = 1.0          # a speck
    return prob


def test_blobs_are_scaled_sorted_and_specks_dropped():
    blobs = finder.blobs_from_map(two_rectangles(), width=400, height=200)
    assert [box for box, _ in blobs] == [(240, 120, 380, 180), (20, 20, 120, 80)]
    assert all(mask.shape == (200, 400) and mask.dtype == bool for _, mask in blobs)
    assert int(blobs[0][1].sum()) == 8400


def test_a_map_that_covers_the_page_gives_nothing():
    assert finder.blobs_from_map(np.ones((50, 50), np.float32), 400, 200) == []
    assert finder.blobs_from_map(np.zeros((50, 50), np.float32), 400, 200) == []


def test_at_most_five_blobs():
    prob = np.zeros((100, 200), np.float32)
    for i in range(7):
        prob[10:30, i * 25 + 5: i * 25 + 20] = 1.0
    assert len(finder.blobs_from_map(prob, 400, 200)) == 5


@pytest.mark.parametrize("bias", [10.0, -10.0])
def test_find_blobs_on_all_or_nothing_weights_is_empty(flat_finder, bias):
    flat_finder(bias)
    page = np.random.default_rng(0).integers(0, 255, (300, 400, 3), dtype=np.uint8)
    assert finder.find_blobs(page) == []


def test_a_wide_page_is_searched_as_two_halves(monkeypatch):
    def one_square(image):                                 # the same blob in whatever it is shown
        prob = np.zeros((100, 100), np.float32)
        prob[40:60, 40:60] = 1.0
        return prob
    monkeypatch.setattr(finder, "_probability", one_square)
    blobs = finder.find_blobs(np.zeros((200, 600, 3), np.uint8))
    assert sorted(box for box, _ in blobs) == [(120, 80, 180, 120), (420, 80, 480, 120)]
    assert all(mask.shape == (200, 600) for _, mask in blobs)


def test_missing_weights_raise_with_the_path(tmp_path, monkeypatch):
    monkeypatch.setenv("FINDER_WEIGHTS", str(tmp_path / "none.pt"))
    finder._loaded.clear()
    with pytest.raises(FileNotFoundError, match="none.pt"):
        finder.find_blobs(np.zeros((300, 400, 3), np.uint8))
```

- [ ] **Step 2: Run** `subject_model/.venv/bin/python -m pytest subject_model/tests/test_finder.py -q`. Expected: FAIL, no module `subject_model.finder`.

- [ ] **Step 3: Implement `finder.py`.** It imports only `cutout_model.prompts` and `cutout_model.model` from the cut-out code, so the server does not load training code.
  - `blobs_from_map`: resize `prob` to `(height, width)` with `cv2.INTER_LINEAR`, mark pixels above 0.5; if more than `MAX_COVER` of the image is marked, return `[]`; take 8-connected regions, drop those under `MIN_BLOB` of the image's area, keep the `MAX_BLOBS` largest, and return each with its bounding rectangle as integers `(x0, y0, x1, y1)`, the right and bottom edges exclusive.
  - `_probability`: load once under `LOCK`, as `namer.py` does: `torch.load(path, map_location=device, weights_only=True)`, `UNet(widths=saved["widths"])`, `eval()`; `cuda` when available, else `cpu`. Call `build_input(image, (0, 0, width, height), margin=saved["margin"], size=saved["input_size"])`, which for a whole-image box gives the whole image; run the model under `torch.inference_mode()` and return `sigmoid` of the output.
  - `find_blobs`: for a page no wider than `WIDE` times its height, `blobs_from_map(_probability(image), width, height)`. A wider page (a two-page spread) is cut at its middle column; each half goes through the same two steps on its own, the right half's rectangles are moved back into page coordinates, every mask is page-sized, and the result is the `MAX_BLOBS` largest of both halves, largest first.

- [ ] **Step 4: Run the tests.** Expected: 7 passed.

- [ ] **Step 5: Commit.** `git add subject_model/finder.py subject_model/tests/test_finder.py && git commit -m "subject_model: find subjects on a whole page"`

---

### Task 8: Training the finder for whole pages, then the run

**Needs:** as Task 7, and `data/datasets/duts/DUTS-TR` from Task 1.

**Files:**
- Create: `subject_model/finder_train.py`, `subject_model/tests/test_finder_train.py`
- Modify: `subject_model/tests/conftest.py` (add `from cutout_model.tests.conftest import duts_root  # noqa: F401`)

**Interfaces:**
- Consumes: `fit`, `pick_device` (Task 3); `draw_lines`, `find_fonts` (Task 2); `cutout_model.data.find_pairs` and `split`; `cutout_model.prompts.build_input`; `cutout_model.model.UNet`; `cutout_model.train.bce_dice`, `mean_iou`, `save_checkpoint`; fixture `duts_root`.
- Produces: `PAGE_SHARE = 0.3`: the share of training photos turned into a page (put on paper, with words drawn).
- Produces: `on_paper(image, mask, rng) -> tuple[np.ndarray, np.ndarray]`: the photo shrunk onto a light plain canvas of its own size, leaving a margin of 10% to 35% of the canvas on one side, or on one side and one of the top and bottom; the mask moved the same way and empty in the margin.
- Produces: `class WholeImageDataset(torch.utils.data.Dataset)` with `__init__(self, pairs, train, size=320, fonts=())`; items are `(input (4, size, size), target (1, size, size))` float32 tensors.
- Produces: `main(argv=None) -> Path`. Arguments: `--duts` (required), `--out` (required), `--epochs 40`, `--batch 64`, `--size 320`, `--widths 32 64 128 256 512`, `--workers 8`, `--lr 0.001`, `--device` (default `pick_device()`). Checkpoints use the cut-out format with `margin=0.0`.

- [ ] **Step 1: Write the failing tests:**

```python
import cv2
import numpy as np
import torch
from cutout_model.data import find_pairs
from subject_model import finder_train
from subject_model.finder_train import WholeImageDataset, on_paper


def test_item_is_the_whole_picture_with_every_object(duts_root):
    pairs = find_pairs(duts_root)
    mask = cv2.imread(str(pairs[0][1]), 0)
    mask[5:15, 5:25] = 255                                 # a second object
    cv2.imwrite(str(pairs[0][1]), mask)
    x, y = WholeImageDataset(pairs, train=False, size=64)[0]
    assert x.shape == (4, 64, 64) and y.shape == (1, 64, 64)
    assert float(x[3].min()) == 1.0                        # the box is the whole image
    assert abs(float(y.mean()) - (mask > 127).mean()) < 0.02     # both objects are in the target


def test_on_paper_moves_the_mask_with_the_photo():
    photo = np.zeros((96, 128, 3), np.uint8)               # all black, all subject
    mask = np.ones((96, 128), bool)
    for seed in range(5):
        image, moved = on_paper(photo, mask, np.random.default_rng(seed))
        assert image.shape == photo.shape and moved.shape == mask.shape and moved.dtype == bool
        assert np.array_equal(moved, image.max(axis=2) < 128)    # the mask is exactly where the photo went
        assert 0.4 < moved.mean() < 0.95                         # the rest is light paper


def test_training_pages_get_words_that_are_not_in_the_target(duts_root, monkeypatch):
    calls = []

    def blackout(image, rng, fonts):
        calls.append(1)
        return np.zeros_like(image)

    monkeypatch.setattr(finder_train, "draw_lines", blackout)
    monkeypatch.setattr(finder_train, "PAGE_SHARE", 1.0)
    pairs = find_pairs(duts_root)
    x, y = WholeImageDataset(pairs, train=True, size=64)[0]
    assert calls and float(x[:3].abs().max()) == 0.0       # the picture was drawn on
    assert float(y.mean()) > 0.03                          # the target still marks the object
    WholeImageDataset(pairs, train=False, size=64)[0]
    assert len(calls) == 1                                 # never when scoring


def test_main_writes_a_cutout_format_checkpoint(duts_root, tmp_path):
    best = finder_train.main(["--duts", str(duts_root), "--out", str(tmp_path / "run"), "--epochs", "2",
                              "--batch", "4", "--size", "64", "--widths", "8", "16", "32", "64", "128",
                              "--workers", "0", "--device", "cpu"])
    saved = torch.load(best, map_location="cpu", weights_only=True)
    assert set(saved) == {"model", "widths", "input_size", "margin", "epoch", "val_iou"}
    assert saved["margin"] == 0.0 and saved["input_size"] == 64 and saved["widths"] == [8, 16, 32, 64, 128]
```

- [ ] **Step 2: Run** `subject_model/.venv/bin/python -m pytest subject_model/tests/test_finder_train.py -q`. Expected: FAIL, no module `subject_model.finder_train`.

- [ ] **Step 3: Implement `finder_train.py`.**
  - `on_paper`: the paper is one flat colour with every channel from 225 to 255. The photo and the mask are resized into the same rectangle of the canvas (the mask with nearest-neighbour).
  - `WholeImageDataset.__getitem__`: read the photo and its mask (resized to the photo with nearest-neighbour if the sizes differ). With `train=True`, in this order: a random crop covering 70% to 100% of each side, the same for photo and mask; a left-right flip with probability 0.5; brightness and contrast each scaled by 0.7 to 1.3; then, with probability `PAGE_SHARE`, `on_paper` followed by `draw_lines(image, rng, fonts)`, so the words land on the paper or on the photo. Build the input with `build_input(image, (0, 0, width, height), margin=0.0, size=size)`. The target is the whole mask above 127, resized with nearest-neighbour. A photo with an all-black mask is a valid example of "nothing stands out". Randomness comes from a `np.random.default_rng()` made on first use inside the dataset object.
  - `main`: `find_pairs`, `split` with the defaults, `fonts = find_fonts()`, `UNet(widths=tuple(args.widths))`. The training loader has `shuffle=True` and `drop_last=True`; both loaders have `persistent_workers=True` when `--workers` is above 0. `AdamW`, weight decay `1e-4`, a cosine learning rate from `--lr` to 0 over all steps, `bce_dice`, `mean_iou`, through `fit`, with `save` writing `save_checkpoint(path, model, input_size=size, margin=0.0, epoch=epoch, val_iou=val_metric)`. On `cuda` only: bf16 autocast and `pin_memory=True`. End with `if __name__ == "__main__": main()`.

- [ ] **Step 4: Run the tests.** Expected: 4 passed.

- [ ] **Step 5: Commit.** `git add subject_model/finder_train.py subject_model/tests/test_finder_train.py subject_model/tests/conftest.py && git commit -m "subject_model: train a whole-page finder"`

- [ ] **Step 6: Time one epoch,** once the namer run has ended, with the laptop settings (see "Measured on this laptop"): `subject_model/.venv/bin/python -m subject_model.finder_train --duts data/datasets/duts/DUTS-TR --out data/models/finder_timing --epochs 1 --size 256 --widths 16 32 64 128 256`. About 100 to 120 seconds is expected.

- [ ] **Step 7: Start the finder run in the background.** Choose `--epochs N` so that N times the measured seconds is at most 60 minutes, capped at 40.

```bash
mkdir -p data/models/finder_run
nohup caffeinate -is subject_model/.venv/bin/python -m subject_model.finder_train --duts data/datasets/duts/DUTS-TR --out data/models/finder_run --epochs N --size 256 --widths 16 32 64 128 256 > data/models/finder_run/train.log 2>&1 &
echo $! > data/models/finder_run/pid
```

Continue with Task 9's code while it trains. When it ends, record the device, seconds per epoch and final `val_metric` in the dev log, and copy `data/models/finder_run/best.pt` to `data/models/finder.pt`.

---

### Task 9: Scoring on the hand-labelled pages, then the verdict

**Needs:** `data/models/namer.pt` (Task 3) and `data/models/finder.pt` (Task 8); five picture-book PDFs from a person, turned into 15 test pages in Step 6 (`{name}.png` and `{name}_mask.png`).

**Files:**
- Create: `subject_model/evaluate.py`, `subject_model/try_book.py`, `subject_model/tests/test_evaluate.py`, `subject_model/tests/test_try_book.py`

**Interfaces:**
- Consumes: `local.local_answer` (Task 6); `words.match` (Task 5); `namer.WHITEN` (Task 4); `pipeline.gemini.choose_subjects` and `SubjectAnswer`; `pipeline.process.call_with_retry` and `decide_state`; `pipeline.masks.mask_box`; `pipeline.run_book.run_book(pdf_path, out_dir, concurrency)`.
- Produces: `load_labels(testset_dir) -> dict[str, tuple[str, str]]`: page name to (subject name, typed text), from `{testset_dir}/labels.csv` with the header `name,label,text`.
- Produces: `page_text(testset_dir, name, fallback="") -> str`: the words the pipeline would get for a page named `{book}_{n}`: page `n` of `{testset_dir}/books/{book}.pdf`, read with `page.get_text().strip()` as `pipeline/ingest.py` does; `fallback` when there is no such PDF.
- Produces: `box_iou(a, b) -> float` for `(x0, y0, x1, y1)` rectangles.
- Produces: `ask_gemini(view_path, text, cache=None) -> SubjectAnswer`: `call_with_retry(lambda: choose_subjects(view_path, text))`. With `cache` (a path), the answer is read from that JSON file when it exists, and written there after a call that worked.
- Produces: `judge(answer, hand_box, hand_label, width, height) -> tuple[bool, bool, bool]` (found, first, named), for a `SubjectAnswer`.
- Produces: `outcome(answer, hand_box, width, height) -> str`: what the teacher gets, from `decide_state`: `"ready_right"`, `"ready_wrong"`, `"asked"` or `"nothing"`.
- Produces: `score(testset_dir, modes=("local",)) -> dict` with keys `pages` (list of `{"name", "labels": {mode: [str]}, "found": {mode: bool}, "first": {mode: bool}, "named": {mode: bool}, "outcome": {mode: str}, "error": {mode: str}}`), `found`, `first`, `named` and `candidates` (`{mode: int}`), `outcomes` (`{mode: {outcome: int}}`), `total`, `plain_crops` (bool). It writes the dict to `{testset_dir}/results_subjects.json`.
- Produces: `main(argv=None)`: `python -m subject_model.evaluate TESTSET_DIR [--modes local gemini] [--plain-crops]`, printing one row per page (each mode's labels, most confident first, and its outcome) and lines such as `local: found 9 of 15, first 7, named 6, ready right 5, ready wrong 1, asked 6, nothing 3, 23 candidates`.
- Produces: in `try_book.py`, `run(pdf_path, out_dir, concurrency=4) -> dict`: `run_book`'s summary, with `local.local_answer` put in place of `pipeline.process.choose_subjects` for the call and put back afterwards; and `python -m subject_model.try_book PDF OUT_DIR`, printing each page's state, reason and seconds.

- [ ] **Step 1: Write the failing tests.** In `conftest.py` add helper `book(path, pages)`, which makes a PDF of that many 400 by 300 pages with `pymupdf`, page N carrying the words `Page N.`, and returns the path. Fixture `testset(tmp_path)` writes `ball.png` (400 by 300, white), `ball_mask.png` (255 inside rows 100 to 200, columns 100 to 300), `labels.csv` with one row `ball,ball,The ball rolled.`, and `books/tale.pdf` made with `book(..., pages=2)`.

`test_evaluate.py`:

```python
import json
import pytest
from pipeline.gemini import SubjectAnswer
from subject_model import evaluate
from subject_model.evaluate import box_iou, judge, load_labels, outcome, page_text, score

NOTHING = SubjectAnswer.model_validate({"page_kind": "scene"})
HAND = (100, 100, 300, 200)                               # on a 400 by 300 page
HERE, AWAY = [333, 250, 667, 750], [0, 0, 100, 100]       # the same rectangle as HAND, and a far corner


def answer(label, synonyms, box_2d, confidence=0.9):
    return SubjectAnswer.model_validate({"things_on_page": [label], "page_kind": "single", "candidates": [
        {"label": label, "synonyms": synonyms, "box_2d": box_2d, "confidence": confidence, "reason": ""}]})


def two(first, second):
    both = first.model_copy(deep=True)
    both.candidates.append(second.candidates[0])
    both.page_kind = "several"
    return both


def test_box_iou():
    assert box_iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert box_iou((0, 0, 10, 10), (5, 0, 15, 10)) == pytest.approx(1 / 3)
    assert box_iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_judge_found_first_and_named():
    right = answer("toy", ["ball", "thing"], HERE)
    assert judge(right, HAND, "ball", 400, 300) == (True, True, True)
    assert judge(answer("dog", ["animal"], HERE), HAND, "ball", 400, 300) == (True, True, False)
    assert judge(answer("ball", [], AWAY), HAND, "ball", 400, 300) == (False, False, False)
    assert judge(NOTHING, HAND, "ball", 400, 300) == (False, False, False)
    assert judge(two(answer("words", [], AWAY), right), HAND, "ball", 400, 300) == (True, False, True)


def test_outcome_is_what_the_teacher_gets():
    assert outcome(answer("ball", [], HERE), HAND, 400, 300) == "ready_right"
    assert outcome(answer("ball", [], AWAY), HAND, 400, 300) == "ready_wrong"
    assert outcome(answer("ball", [], HERE, confidence=0.4), HAND, 400, 300) == "asked"
    assert outcome(two(answer("ball", [], HERE), answer("dog", [], AWAY)), HAND, 400, 300) == "asked"
    assert outcome(NOTHING, HAND, 400, 300) == "nothing"


def test_score_counts_and_writes_results(testset, monkeypatch):
    monkeypatch.setattr(evaluate.local, "local_answer", lambda view_path, text: answer("ball", ["toy"], HERE))
    result = score(testset, modes=("local",))
    assert result["total"] == 1 and result["candidates"] == {"local": 1}
    assert result["found"] == result["first"] == result["named"] == {"local": 1}
    assert result["outcomes"] == {"local": {"ready_right": 1, "ready_wrong": 0, "asked": 0, "nothing": 0}}
    assert result["pages"][0]["labels"] == {"local": ["ball"]}
    assert json.load(open(testset / "results_subjects.json")) == result


def test_a_mode_that_fails_on_a_page_counts_as_nothing(testset, monkeypatch):
    def broken(view_path, text):
        raise RuntimeError("no service")
    monkeypatch.setattr(evaluate.local, "local_answer", broken)
    result = score(testset, modes=("local",))
    assert result["found"] == {"local": 0} and result["outcomes"]["local"]["nothing"] == 1
    assert "no service" in result["pages"][0]["error"]["local"]


def test_page_without_a_label_row_is_reported(testset):
    (testset / "labels.csv").write_text("name,label,text\n")
    with pytest.raises(ValueError, match="ball"):
        load_labels(testset)


def test_page_text_comes_from_the_pdf_when_it_is_there(testset):
    assert page_text(testset, "tale_2") == "Page 2."
    assert page_text(testset, "ball", fallback="typed") == "typed"


def test_gemini_is_asked_once_for_a_page(tmp_path, monkeypatch):
    calls = []
    def fake(view_path, text):
        calls.append(view_path)
        return answer("ball", [], HERE)
    monkeypatch.setattr(evaluate, "choose_subjects", fake)
    cache = tmp_path / "gemini" / "page.json"
    assert evaluate.ask_gemini("page.png", "", cache=cache) == evaluate.ask_gemini("page.png", "", cache=cache)
    assert len(calls) == 1
```

`test_try_book.py`:

```python
import pipeline.process
from pipeline.gemini import SubjectAnswer
from subject_model import local, try_book
from subject_model.tests.conftest import book


def test_a_book_goes_through_the_real_page_code(tmp_path, monkeypatch):
    monkeypatch.setenv("SEGMENTER", "stub")
    fixed = SubjectAnswer.model_validate({"page_kind": "single", "candidates": [
        {"label": "ball", "synonyms": [], "box_2d": [100, 100, 500, 500], "confidence": 0.9, "reason": ""}]})
    monkeypatch.setattr(local, "local_answer", lambda view_path, text: fixed)
    before = pipeline.process.choose_subjects
    summary = try_book.run(book(tmp_path / "book.pdf", pages=2), tmp_path / "out")
    assert sum(summary["counts"].values()) == 2 and "failed" not in summary["counts"]
    assert pipeline.process.choose_subjects is before          # put back afterwards
```

- [ ] **Step 2: Run** `subject_model/.venv/bin/python -m pytest subject_model/tests/test_evaluate.py subject_model/tests/test_try_book.py -q`. Expected: FAIL, no module `subject_model.evaluate`.

- [ ] **Step 3: Implement `evaluate.py` and `try_book.py`.**
  - A page is every `*.png` directly in the folder not ending `_mask.png`; `load_labels` raises `ValueError` naming every page with no row. The hand rectangle is `mask_box` of the hand mask. A page's text is `page_text(testset_dir, name, fallback=the typed text)`.
  - `judge`: convert each candidate's `box_2d` to pixels. *found* is true when some candidate's rectangle has `box_iou` of at least 0.5 with the hand rectangle. *first* is true when the first candidate's does. *named* is true when the best-overlapping such candidate's names (label, then synonyms), joined with spaces, contain the hand label by `words.match`.
  - `outcome`: no candidates is `nothing`. Otherwise `state, members, _ = decide_state(answer.page_kind, answer.candidates)`: one member is `ready_right` when that candidate's rectangle has `box_iou` of at least 0.5 with the hand rectangle and `ready_wrong` when not; anything else is `asked`.
  - `score`: for each page write a copy with its longer side at most 1,600 px (the pipeline's working size) to a temporary folder and pass that path and the page's text to the chooser. Mode `local` calls `local.local_answer`; mode `gemini` calls `ask_gemini` with `cache={testset_dir}/gemini/{name}.json`. A chooser that raises counts as nothing found on that page, outcome `nothing`, with the error's text under `error`. `candidates` is each mode's number of candidates over all pages.
  - `--plain-crops` sets `namer.WHITEN = False` for that run.
  - `evaluate.py` imports `choose_subjects` by name (`from pipeline.gemini import choose_subjects`) and `local` as a module, so the tests can replace `evaluate.choose_subjects` and `evaluate.local.local_answer`. `ask_gemini` makes the cache's folder when it writes.
  - `try_book.run` reaches `local.local_answer` through the `local` module at call time, and restores `pipeline.process.choose_subjects` in a `finally`.

- [ ] **Step 4: Run the tests.** Expected: 9 passed.

- [ ] **Step 5: Commit.** `git add subject_model/evaluate.py subject_model/try_book.py subject_model/tests/test_evaluate.py subject_model/tests/test_try_book.py subject_model/tests/conftest.py && git commit -m "subject_model: score what the teacher would get"`

- [ ] **Step 6 (a person and the agent, about 20 minutes of the person's time): the test pages.** The cut-out plan no longer hand-labels picture-book pages: it scores on pasted anime cut-outs, which have no page text and say nothing about naming. So this plan makes its own 15 pages. Only each subject's rectangle is needed, not a painted mask.
  1. (a person) Put five picture-book PDFs in `data/subject_testset/books/`, named with letters, digits and `-` only. They must have one page of the book per PDF page: Book Dash PDFs are two-page spreads, which the app marks Unsupported, so use another source (the demo book's publisher, Pratham Books on Free Kids Books, is one). Not the demo book, and not a book Kevin's evaluation pages come from. Note each book's licence for the credits.
  2. The agent makes page images for each PDF: `subject_model/.venv/bin/python -c "from pipeline.ingest import rasterize; rasterize('data/subject_testset/books/NAME.pdf', 'data/subject_testset/raw/NAME')"`. Pages appear in `raw/NAME/pages/{n}.png`.
  3. (a person) Pick 15 pages, 3 per book, each with one clear subject. For each, give the page number and the word you would use for its subject.
  4. The agent copies each page to `data/subject_testset/NAME_{n}.png`, looks at it and proposes a rectangle around the subject, writes `NAME_{n}_mask.png` (the same size, black, with that rectangle filled white), writes `labels.csv` (one row per page: the file name without `.png`, the person's word, and an empty third column, because the words come from the PDF), and saves a copy of each page with the rectangle drawn on it in `data/subject_testset/check/`.
  5. (a person) Look at the 15 pictures in `check/` and say which rectangles are wrong. The agent redraws those until all 15 are right.

- [ ] **Step 7: Score the local mode.** `subject_model/.venv/bin/python -m subject_model.evaluate data/subject_testset`. Record the printed line in the dev log. From the printed rows, also count the pages whose subject is not a person but whose first label is a person word, and record it. Then check the stop rule about `ready wrong`.

- [ ] **Step 8: Score with plain rectangle crops.** The same command with `--plain-crops`; copy `results_subjects.json` to `results_subjects_plain.json`. Record both `named` counts and keep both rows for the README. Ship the setting that names more pages; on a tie ship plain rectangles (`WHITEN = False` in `namer.py`, committed), because a teacher's click is always named from a plain rectangle. This one setting is chosen on the test pages; the README says so.

- [ ] **Step 9 (only if a cut-out checkpoint is on this laptop): try the cut-out weights as the finder.** `FINDER_WEIGHTS=data/models/run_a/best.pt subject_model/.venv/bin/python -m subject_model.evaluate data/subject_testset`, copy the result to `results_subjects_cutout_weights.json` and record the counts. Keep whichever finder weights found more pages as `data/models/finder.pt`. Nothing waits for this step.

- [ ] **Step 10: Score Gemini on the same pages.** This makes 15 real Gemini calls, once: answers are kept in `data/subject_testset/gemini/`. Get Andrew's go-ahead first (Task 10 Step 5 needs up to 20 more, so ask for both). Load the key without printing it: `set -a; . "$MAIN/.env"; set +a`. Then `subject_model/.venv/bin/python -m subject_model.evaluate data/subject_testset --modes local gemini`. A page listed with a Gemini error can be asked again by running the command again; if it still fails, report Gemini's row as "of 14".

- [ ] **Step 11: Report to Andrew** with both rows, the person count from Step 7 and the two `named` counts from Step 8.

- [ ] **Step 12: Rehearse on one whole book.** `subject_model/.venv/bin/python -m subject_model.try_book fixtures/animal-homes-pratham-FKB.pdf data/try_book/animal-homes`. This runs the demo book through the real `process_page`, four pages at once, with the local mode in Gemini's place and no Gemini call. Record each page's state and the seconds per page. It is a rehearsal: fix bugs it shows, and tune nothing on it.

---

### Task 10: Agreement with Gemini on pages nobody picked

**Files:**
- Modify: `subject_model/evaluate.py`, `subject_model/tests/test_evaluate.py`

**Interfaces:**
- Consumes: `ask_gemini`, `box_iou` (Task 9); `local.local_answer`; `words.match`; `pipeline.ingest.rasterize(pdf_path, out_dir)`, which returns one `PageAsset` per page with `page_number`, `view_path` and `text`.
- Produces: `agree(testset_dir, every=3, limit=20) -> dict` with keys `pages` (list of `{"name", "agree": bool, "named": bool}`), `agree`, `named`, `total`, and `failed` (names of pages where a chooser raised). It writes the dict to `{testset_dir}/results_agreement.json`.
- Produces: in `main`, `python -m subject_model.evaluate TESTSET_DIR --agree [--every 3] [--limit 20]`, printing one row per page and a line such as `agreement: 8 of 20 pages, names agree on 5`.

- [ ] **Step 1: Write the failing tests** (add to `test_evaluate.py`; `book` comes from `conftest.py`):

```python
from subject_model.evaluate import agree
from subject_model.tests.conftest import book


def test_agreement_takes_every_third_unlabelled_page(testset, monkeypatch):
    book(testset / "books" / "story.pdf", pages=10)
    (testset / "story_3.png").write_bytes((testset / "ball.png").read_bytes())      # page 3 is hand-labelled
    ball, dog = answer("ball", ["toy"], [100, 100, 500, 500]), answer("dog", [], [600, 600, 900, 900])
    local_answers = iter([ball, dog])
    monkeypatch.setattr(evaluate.local, "local_answer", lambda view_path, text: next(local_answers))
    monkeypatch.setattr(evaluate, "ask_gemini", lambda view_path, text, cache=None: ball)
    (testset / "books" / "tale.pdf").unlink()
    result = agree(testset)
    assert [page["name"] for page in result["pages"]] == ["story_6", "story_9"]
    assert result["total"] == 2 and result["agree"] == 1 and result["named"] == 1 and result["failed"] == []
    assert json.load(open(testset / "results_agreement.json")) == result


def test_two_empty_answers_agree(testset, monkeypatch):
    book(testset / "books" / "story.pdf", pages=3)
    (testset / "books" / "tale.pdf").unlink()
    monkeypatch.setattr(evaluate.local, "local_answer", lambda view_path, text: NOTHING)
    monkeypatch.setattr(evaluate, "ask_gemini", lambda view_path, text, cache=None: NOTHING)
    result = agree(testset)
    assert result["total"] == 1 and result["agree"] == 1 and result["named"] == 0
```

- [ ] **Step 2: Run** `subject_model/.venv/bin/python -m pytest subject_model/tests/test_evaluate.py -q`. Expected: FAIL, cannot import `agree`.

- [ ] **Step 3: Implement `agree`.** For each PDF in `{testset_dir}/books/`, in name order, `rasterize` it into `{testset_dir}/agreement/{book}`. Take pages 3, 6, 9 and so on (every `every`-th), leave out any page that has a hand-labelled PNG in `testset_dir`, and stop after `limit` pages in all. Spreads are not left out: the choosers are called directly. A page's name is `{book}_{page number}`. Give both choosers the page's `view_path` and `text`; Gemini's answers use `cache={testset_dir}/gemini/{name}.json`. A page *agrees* when both answers have no candidates, or when the local mode's first candidate has `box_iou` of at least 0.5 with one of Gemini's candidates. It is *named* when it agrees on a candidate and `match` finds the local label in that Gemini candidate's names (label, then synonyms) joined with spaces. A page where either chooser raises goes in `failed` and is left out of `pages` and `total`.

- [ ] **Step 4: Run the tests.** Expected: 10 passed.

- [ ] **Step 5: Run it** (with the go-ahead from Task 9 Step 10 and the key loaded the same way): `subject_model/.venv/bin/python -m subject_model.evaluate data/subject_testset --agree`. Record the line it prints. These are the pages left after the clearest ones were picked, so they lean hard; the README says so.

- [ ] **Step 6: Commit.** `git add subject_model/evaluate.py subject_model/tests/test_evaluate.py && git commit -m "subject_model: agreement with Gemini on unpicked pages"`

---

### Task 11: Results, credits and the hand-off to Bryan

**Files:**
- Create: `subject_model/README.md`

- [ ] **Step 1: Check the code against the server's Python.** `uv run --no-project --python 3.11 python -m compileall -q subject_model`. Expected: no output.

- [ ] **Step 2: Write `subject_model/README.md`:**
  - what the three parts are, one sentence each
  - the commands: laptop setup, the downloads, the two extra classes, train the namer, train the finder, score, rehearse a book, where the two weights files go
  - a results table of counts from the `results_subjects*.json` files: found, first choice, named, ready right, ready wrong, asked, nothing and candidates, of 15, for Gemini and for local, with both crop settings shown
  - the agreement line from `results_agreement.json`
  - how to read them: the 15 pages were picked to have one clear subject, the easy case for the local mode; their rectangles were proposed by an AI assistant and checked by a person; the agreement pages are the ones left over, taken by rule; agreement with Gemini is not accuracy; `WHITEN` was chosen on the 15 pages; any number changed after the first scoring run, with the counts before and after
  - the sizes the models were trained at, which DomainNet folders the namer saw, its validation accuracy and the two `watch` lines, with the note that validation images are whole pictures, so they understate how often a cut-out on white is called a person
  - the limits: about 345 fixed names; `person` learned from anime art only; parts of the body are never named; subjects that touch come out as one; small subjects are missed; prominence is not importance; a two-page spread is searched as two halves, and the app marks spreads Unsupported unless the teacher asks for them
  - the credits from Global Constraints

- [ ] **Step 3: Commit.** `git add subject_model/README.md && git commit -m "subject_model: results and credits"`

- [ ] **Step 4: Send Bryan this change for `pipeline/gemini.py`, by hour 17, with its evidence.** Do not make it yourself. The evidence is the results table, the `try_book` output for one book, and the Python 3.11 check. Later than hour 17, the mode is shown from the laptop only (Task 9 Step 12) and nothing is asked of Bryan before judging.

At the top of `choose_subjects`:

```python
    finder = (os.environ.get("SUBJECT_FINDER") or "gemini").strip().lower()
    if finder == "local":
        from subject_model.local import local_answer
        try:
            return local_answer(view_path, text)
        except FileNotFoundError:
            raise GeminiError("The local subject finder is not set up on this server") from None
    if finder != "gemini":
        raise GeminiError("SUBJECT_FINDER must be gemini or local")
```

At the top of `label_crop`:

```python
    if (os.environ.get("SUBJECT_FINDER") or "gemini").strip().lower() == "local":
        from subject_model.local import label_crop as local_label
        return local_label(png_bytes)
```

Also for Bryan:
  - One test for `pipeline/tests`: with `SUBJECT_FINDER=local` and `subject_model.local.local_answer` patched to return a fixed `SubjectAnswer`, `choose_subjects` returns that answer and never calls `_generate`.
  - One row for the settings table in `pipeline/README.md`: `SUBJECT_FINDER`, `gemini` (default) or `local`.
  - The code reaches `main` only when branch `model` is merged, which is his and the team's call. It adds no packages: torch and torchvision are already in the image. The local mode needs torchvision at run time, so its pin in `pipeline/requirements.txt` must stay.
  - The weights go to `/opt/mirai/data/models/namer.pt` and `finder.pt` on the server. Copying them and changing the server's settings need his go-ahead each time.
  - Our recommendation: the server stays on Gemini through judging, and the local mode is shown from the laptop. If it is switched on at the server: change the setting only when nothing is processing, because a restart marks pages in flight as failed; and use a fresh upload, because "Ask the AI again" adds new suggestions to a book's old ones.
  - `SUBJECT_FINDER=local` alone does not switch Gemini off. The second look (`checks/second_look.py`) still calls it while `GEMINI_API_KEY` is set. To show "no outside AI", also empty the key: a mistyped setting then fails loudly, and every page carries the warning "Second look skipped: no GEMINI_API_KEY is set."
  - A teacher's click is named locally too, and comes back unlabeled when the namer is unsure.
  - The plain sentence in the hook matters: the web app hides any failure reason that contains `Error:`.
  - Whether a failed Gemini call should fall back to the local mode on its own is his decision. We recommend no: it would mix two very different sources inside one book without the teacher knowing.

---

## Stop rules

- If the namer's validation `top1` is under 0.25 after its run, stop and tell Andrew before building further: names that wrong make the local mode a box finder only.
- If the namer's `watch` lines show `person` given to more than 1 in 50 of the other validation images, or fewer than 8 in 10 of the `text` images named `text`, tell Andrew before Task 9. The fix is another namer run with fewer `person` images or more `text` images, about an hour.
- If the local mode's `ready wrong` on the 15 pages is more than 2, set `CONFIDENCE_CAP = 0.49` in `local.py`, so no page is pre-selected and the teacher is always asked. Score again and report both rows.
- If the cut-out code on `model` has changed so that Task 7's check or tests fail (it matched this plan at commit `73ff4be`), tell Andrew. Tasks 1 to 6 and Task 9's code do not wait for it. He chooses between asking for the change to be undone and a private copy in `subject_model/` of the four pieces the finder uses (the U-Net, the 4-channel input, the loss and the overlap score, about 80 lines).
- If Tasks 1 to 6 are not done two hours before the feature freeze (checkpoint 3), stop. Nothing here is needed for the demo.
- If time is short, cut in this order: turning the mode on at the server (keep the note, show it from the laptop); Task 10; Task 9 Steps 8 and 9; `on_paper` in Task 8; the `watch` lines.
- `main` and the server are untouched by Tasks 1 to 10: the work is on `model`. Nothing here can break the demo until `model` is merged and Bryan makes Task 11's change.

## Not in this plan

- The second look (`checks/`, Kevin's). It still calls Gemini; a local version would reuse `namer.name` on the adapted page.
- Counting the namer's body-part guesses towards `person`, so a close-up of a child is named a person even when the text does not say so. It needs a look at real guesses first: an animal's ear or eye may also be called a body part.
- Continuing a training run that died from where it stopped. Runs are an hour at most and write usable weights every epoch.
- A command that starts the whole app on the laptop in local mode. `try_book` shows the page states; the app itself needs the hook.
- Running the finder on overlapping quarters of the page to catch small subjects.
- Adding DomainNet's photo images (`real`, 6.1 GB) to the namer's training. It is one more `--roots` argument if the drawn images alone score badly.
- Training the finder on drawn cut-outs pasted onto backgrounds (the cut-out plan's run B data), with every pasted cut-out in the target. It is the next step if the finder does well on photos and badly on drawings.
- Any change to the cut-out model or its training.
