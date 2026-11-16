# Subject finder

Miraai's subject choosing, with no outside AI. Since 2026-11-15 it is the only subject finder:
`pipeline.subjects.choose_subjects` calls it on every page. Given a page picture and its words, it returns up
to five subjects, each with a name, synonyms, a rectangle and a confidence. Before that date Gemini was the
default and this was a fallback; it is clearly worse than Gemini, and the results below show by how much.
The pipeline's trust rule (`pipeline/README.md`, "How subjects are found") makes up for it: a guess is
pre-selected only when the page text backs it up, and otherwise the teacher picks.

Both models were trained by the team from random weights. No pretrained weights are used anywhere.

## The three parts

- **Namer** (`namer.py`): a ResNet-18 that names a crop with one of 347 names (DomainNet's 345 classes,
  plus `person` and `text`).
- **Finder** (`finder.py`): the cut-out model's U-Net, trained on whole photos with every labelled object
  marked, so it marks what stands out on a page; its separate blobs become rectangles.
- **Chooser** (`local.py`): names each blob, lets the page text confirm a name, and builds the
  answer `pipeline.subjects.SubjectAnswer` accepts, with confidences set so the pipeline's existing rules decide the page state.

## Commands

Run everything from the repo root.

```bash
# Laptop setup (Python 3.13 here; the code also runs on the server's 3.11)
uv venv --python 3.13 subject_model/.venv
uv pip install -p subject_model/.venv torch==2.15.0 torchvision==0.29.2
uv pip install -p subject_model/.venv -r subject_model/requirements-train.txt

# Downloads and unpacking: see Task 1 Steps 4 and 5 of docs/plans/2026-11-14-subject-model.md
# (DomainNet clipart, painting, sketch with the listed duplicates removed; anime-segmentation fg-05; DUTS-TR)

# The two extra classes
subject_model/.venv/bin/python -m subject_model.text_images data/datasets/extra/text --count 550
#   ...and 550 anime cut-outs copied to data/datasets/extra/person (Task 2 Step 5)

# Train the namer (laptop: 128 px, about 83 s an epoch on an M5 Max)
subject_model/.venv/bin/python -m subject_model.namer_train \
  --roots data/datasets/domainnet/clipart data/datasets/domainnet/painting data/datasets/domainnet/sketch data/datasets/extra \
  --out data/models/namer_run --epochs 30 --size 128
cp data/models/namer_run/best.pt data/models/namer.pt

# Train the finder (laptop: half width at 256 px, about 96 s an epoch)
subject_model/.venv/bin/python -m subject_model.finder_train --duts data/datasets/duts/DUTS-TR \
  --out data/models/finder_run --epochs 37 --size 256 --widths 16 32 64 128 256
cp data/models/finder_run/best.pt data/models/finder.pt

# Score on the hand-labelled pages (add --modes local gemini to compare with Gemini's answers saved in
# data/subject_testset/gemini/ before the app stopped calling it; the local score applies the trust rule)
subject_model/.venv/bin/python -m subject_model.evaluate data/subject_testset
subject_model/.venv/bin/python -m subject_model.evaluate data/subject_testset --plain-crops
subject_model/.venv/bin/python -m subject_model.evaluate data/subject_testset --agree

# Run a whole book through the real page code
subject_model/.venv/bin/python -m pipeline.run_book fixtures/animal-homes-pratham-FKB.pdf data/runs/animal-homes

# Tests
subject_model/.venv/bin/python -m pytest subject_model/tests -q
```

The weights are read from `NAMER_WEIGHTS` and `FINDER_WEIGHTS` when set, else from
`$DATA_DIR/models/namer.pt` and `finder.pt` (`data/models/` on the laptop, `/opt/mirai/data/models/` on the
server). A missing file raises `FileNotFoundError` naming the path.

## Results

Scored on 2026-11-14 on 38 team-labelled picture-book pages with 121 subjects. Counts, not percentages.

| Mode | Pages | Subjects found | Subjects named | First choice is a main subject | Ready, right | Ready, wrong | Teacher asked | Nothing | Candidates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gemini | 37 | 73 of 114 | 72 | 31 of 37 | 8 | 0 | 28 | 1 | 91 |
| Local, same 37 pages | 37 | 17 of 114 | 6 | 13 of 37 | 4 | 0 | 32 | 1 | 63 |
| Local, all 38 pages (ships: cut-out on white) | 38 | 17 of 121 | 6 | 13 of 38 | 4 | 0 | 33 | 1 | 66 |
| Local, all 38 pages, plain rectangle | 38 | 17 of 121 | 5 | 13 of 38 | 4 | 2 | 30 | 2 | 62 |

Gemini (`gemini-3.8-flash`, the pipeline's default) answered 37 of the 38 pages; one page timed out twice at the
pipeline's 20 second limit and is left out of its row, so the fair comparison is the first two rows.

In short: Gemini finds about two of every three labelled subjects and names nearly all it finds. The local mode
finds about one in seven and names about one in twenty. Where the local mode does well is a single large animal
on a plain background with its name in the page text (the elephant, the tiger). On busy pages its finder marks one
big blob or the wrong thing, and its names are mostly wrong (ants called a map, a girl called a mermaid). Neither
mode sent a wrong page through as Ready on these pages; the local mode asks the teacher on nearly every page.

**One whole book through the real page code** (2026-11-14, before the trust rule; Animal Homes, 16 pages, no Gemini call): 22 seconds in
all with four pages at a time, about 1 to 5 seconds a page; no page failed; 7 pages Ready and 9 asking the teacher.
Of the 7 Ready pages, 3 were confirmed by the page text and look right (bear, crocodile, tiger). The other 4 were
pre-selected on the namer's confidence alone, with names the text does not support (crocodile on the fish and frog
page, map twice, sword). Nothing was tuned on this book.

With the trust rule (2026-11-15, `pipeline.run_book`, `SEGMENTER=cascade`, 93 s on a laptop CPU): 1 page Ready
and right (the crocodile), 15 asking the teacher, none failed. The 4 wrong Ready pages now ask, and so do the
bear and tiger pages, whose text names a second animal.

Agreement with Gemini on unpicked pages (`--agree`): not run. Two of the three books were labelled in full, so the
rule leaves 9 pages, 5 of them credits pages.

### How to read them

- **The pages.** 38 pages from 14 books, labelled by two teammates: 27 pages in a row from three books
  (Busy Ants 1 to 12 and Watch Out! The Tiger is Here! 1 to 8, which is every page with a picture, and the
  first seven pages of The Elephant Bird) and one page each from 11 more books. They are ordinary story
  pages, most with several subjects; nobody picked them to be easy. 121 subjects in all.
- **What counts as a subject.** The product's own rule (the Gemini prompt): each person, animal or object;
  same-kind things that touch or sit together (a line of ants) are one subject; things apart are separate;
  the setting (grass, water, background trees) never is. The labellers listed everything they saw, so the
  list includes small background animals that neither mode is asked to rank first.
- **Found** means a candidate's rectangle overlaps the labelled one by half or more (IoU 0.5). **Named**
  means that candidate's label or synonyms contain one of the accepted names for the subject (the
  labeller's word, or another name for the same thing: `police officer`, `officer` or `woman`; never a
  catch-all such as animal).
- **First choice** and the page outcomes are counted per page: the first choice is right when it is any main
  subject; Ready is right when the pre-selected subject is any main subject.
- The rectangles were drawn by an AI assistant from the labellers' words. A person has not yet checked them
  (the pictures are in `data/subject_testset/check/`), so the counts are provisional. Every change to a
  labeller's words is listed in `data/subject_testset/LABEL_NOTES.md`.
- `WHITEN` (whether the namer sees the cut-out on white or the plain rectangle) was chosen on these pages.
- The 11 single pages have no PDF, so the words printed on each page were typed in by hand.
- No number in `local.py` or `words.json` was changed after the first scoring run.

## Training

- **Namer:** ResNet-18 from random weights, 30 epochs at 128 px on a laptop GPU (Apple MPS), about 83 s an
  epoch, 42 minutes. Trained on DomainNet clipart, painting and sketch (189,523 images after removing the
  5,455 listed duplicates) plus 550 `person` cut-outs and 550 drawn `text` pictures: 347 classes, 181,092
  training and 9,531 validation images. Validation top-1 accuracy 0.590.
- Watch lines on the validation images: `person` 30 of 36 named right, and 5 of 9,495 other images wrongly
  named person; `text` 36 of 36 right, 0 of 9,495 wrongly named text. Validation images are whole pictures,
  so they understate how often a cut-out on white is called a person.
- **Finder:** the cut-out model's U-Net at half width (16 to 256 channels), 37 epochs at 256 px on the same
  laptop, about 35 s an epoch, 29 minutes. Trained on DUTS-TR (10,025 training and 528 validation photos);
  3 in 10 training photos are placed on paper with printed words that are not in the target. Validation
  IoU 0.827, on photos.

## Limits

- About 345 fixed names. A subject outside the list gets the nearest name, often wrong.
- `person` was learned from anime art only.
- Parts of the body are never used as names (a portrait's face is named by the text or as a person).
- Subjects that touch come out as one blob; small subjects are missed.
- What stands out is not always what the page is about: prominence is not importance.
- A two-page spread is searched as two halves; the app marks spreads Unsupported unless the teacher asks for them.

## Credits

- DomainNet: Peng et al., "Moment Matching for Multi-Source Domain Adaptation", ICCV 2019. No named licence;
  offered under a fair-use notice for non-commercial research and education.
- anime-segmentation (skytnt), CC0.
- DUTS: Wang et al., "Learning to Detect Salient Objects with Image-Level Supervision", CVPR 2017. Research use.
- Test books, all from Pratham Books' StoryWeaver (the three PDFs via Free Kids Books), CC BY 4.0 as stated in
  each PDF: *Busy Ants* (Kanchan Bannerjee, illustrated by Deepa Balsavar), *Watch Out! The Tiger is Here!*
  (Sejal Mehta, illustrated by Rohan Chakravarty), *The Elephant Bird* (Arefa Tehsin, illustrated by Sonal
  Goyal and Sumit Sakhuja).
- The 11 single test pages (*A Book for Puchku*, *Beauty is Missing*, *Catch That Cat!*, *Come Stay With Me*,
  *It's All the Cat's Fault!*, *Kilbe*, *Sniffles*, *Stage Fright*, *The Root Bridge*, *This Land is My School*,
  *Tra's Red Bean Plant*) are StoryWeaver-style pages collected by a teammate; each book's licence still has
  to be checked before a page is shown in slides. They are in `training_images_set_1/` and are used here as
  test pages only: training on them later would make these results meaningless. The test set folder
  (`data/subject_testset/`) is not in git.
