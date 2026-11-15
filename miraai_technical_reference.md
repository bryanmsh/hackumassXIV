# Miraai: technical reference for judges' questions

HackUMass XIV · written 2026-11-15 · for teammates answering technical questions at the table

**What this is.** One document with every technical fact about Miraai, the numbers behind it, and an honest list of what is weak. Section 14 is a question-and-answer sheet. Section 13 lists what *not* to claim.

**Basis.** The code on `origin/main` (commit `912a7a0`), the two spec documents, the README files in each folder, and the team's dev log. Test results quoted here were measured earlier and are cited with their source; test counts in section 11 were counted from the files, not re-run for this document. **I could not check the live server's `.env`** (which segmenter and subject finder it runs). Confirm that before the demo (see 12.4).

---

## 1. The 60-second version

Miraai adapts picture-book pages for children with cortical visual impairment (CVI). A teacher uploads a PDF. The app finds the subject of each page **once**, cuts it out of the original artwork with a mask, and re-displays that same cut-out for each child's profile. A teacher approves every page before a child sees it.

Three guarantees, each enforced in code and not only in the interface:

| Guarantee | Where it is enforced |
| --- | --- |
| The subject is **copied from the original page** through a mask. Nothing is drawn or generated. | `render/core.py` crops the master page through the mask. A unit test checks every output pixel inside the mask core equals a resampled master pixel. |
| A child is **never shown an unapproved version**. | `api/routes/reader.py`: the image route recomputes the version token and checks the approval on every request, and answers 403 otherwise. |
| **Automatic checks are not approval.** | Checks only produce warnings. Only `POST /books/{id}/approve` (a teacher action) writes an approval. The UI never says "verified". |

Where AI is used, and where it is not:

| Step | Technology | AI? |
| --- | --- | --- |
| Choose the subject of a page | Gemini (`gemini-3.8-flash`), JSON output; optional own-model cascade | Yes |
| Cut the subject out | SAM 2.1 small on CPU; GrabCut fallback; own U-Net cascade (optional) | Yes (segmentation only, never generation) |
| Second look (names the subject from the adapted page) | Gemini | Yes, a warning only |
| Tint, fade, outline, place, size, checks | NumPy, OpenCV, Pillow | No. Deterministic |
| Manual outline fallback | OpenCV polygon fill | No. Works with all AI services down |

---

## 2. Architecture

```
 Browser (React SPA)                      One Vultr server, Docker Compose
 ───────────────────      HTTPS           ┌─────────────────────────────────────────────┐
  Library / Review /  ──────────────────▶ │ caddy   basic-auth on every path, TLS,      │
  Profiles / Sheet /      /api/*          │         serves built web app, /api → api    │
  Reader                                  │            │                                │
                                          │ api     FastAPI + Pydantic v2 (api/)        │
                                          │   │  owns every rule about state, hashes,   │
                                          │   │  approvals; the ONLY code touching DB   │
                                          │   ├─▶ pipeline/   rasterize, process_page,  │
                                          │   │               segment, outline, click   │
                                          │   ├─▶ render/     render, overlay (no AI)   │
                                          │   └─▶ checks/     run_checks (no AI),       │
                                          │                   second_look (1 AI call)   │
                                          │ mongo   (or MongoDB Atlas, see 12.3)        │
                                          │ ./data  page images, masks, source PDFs     │
                                          └─────────────────────────────────────────────┘
```

Four modules, three frozen contracts, one owner per folder:

| Lane | Owner | Folders |
| --- | --- | --- |
| A Pipeline and server | Bryan | `pipeline/`, `fixtures/`, `infra/`, `Dockerfile`, `compose.yaml`, `Caddyfile` |
| B Display, checks, pitch | Kevin | `render/`, `checks/`, `eval/`, `pitch/`, `tests/`, and `cutout_model/` (with Bryan, per the team table in `README.md`) |
| C API and data | Andrew | `api/`, `contracts/`, and `subject_model/` (the local subject finder) |
| D Web app | Thomas | `web/` |

(`cutout_model/` and `subject_model/` are our own trained models, see section 6.)

**The three contracts** (frozen; may only gain fields):

1. **HTTP API** between the web app and the API. Paths under `/api`, JSON, WebP images with `Cache-Control: no-store`.
2. **Python functions** between the API and pipeline/display/checks (`contracts/types.py`).
3. **Image files** between the pipeline and display (paths and formats in 3.3).

**Why this design.** It let four people build in parallel for 24 hours with no shared files. Each consumer wrote its own stand-in (`api/stubs.py`, `web/src/mocks/`, `render/samples/`) for what it needed, then swapped the real thing in. `PIPELINE=stub|real` and `RENDER=stub|real` bypass a broken module with one setting.

**Why one pipeline run per book.** The slow AI work (about 8 to 13 s per Gemini call, 4 to 5 s of SAM encoding per page) happens once. Everything a child sees afterwards is deterministic image compositing from saved parts, so switching child or look needs no AI and is fast.

---

## 3. Data flow, step by step

### 3.1 Upload (`POST /api/books`, `api/routes/books.py`)
Streams the file in 1 MB chunks and refuses over **50 MB** (413). Opens it with PyMuPDF (400 if unreadable), refuses over **30 pages** (413). Saves `source.pdf`, calls `read_credits` to fill empty credit fields from the PDF's own text (the teacher's typed value always wins; `pipeline/credits.py` copies what is printed and never guesses), inserts the book as `ingesting`, returns `book_id` at once, and starts a background task.

### 3.2 Ingest (`pipeline/ingest.py`, `rasterize`)
- Render each page at **300 DPI** with its rotation applied, cap the longer side at **3,000 px** (the **master**). Save a **1,600 px working copy** (`_view.png`).
- Read the text layer. Empty means `text_source = none`. Also stores each text block's box as fractions of the page (`text_boxes`) for the display.
- Flag `spread` if width > 1.9 × height (two-page spread, state Unsupported unless forced). Flag `low_quality` if the page is a single embedded image whose own longer side is under 1,000 px.
- PyMuPDF is not thread-safe, so a lock serialises it.

### 3.3 Files on disk (Contract 3)
```
data/books/{book_id}/source.pdf
data/books/{book_id}/pages/{n}.png          master, RGB
data/books/{book_id}/pages/{n}_view.png     working copy, long side 1,600 px
data/books/{book_id}/masks/{n}_{hash}.png   8-bit, 1 channel, master size, 255 = subject
```
Mask files are named by the hash of their bytes and **never overwritten**. A new cut-out is a new file. That is what lets approvals "come back" when a teacher switches back to an earlier subject.

### 3.4 Process every page (`api/jobs.py`)
`process_pages` runs `process_page` in a `ThreadPoolExecutor`, `PAGE_CONCURRENCY` pages at a time (default 4). Each result is written as it lands. A failed page is marked Failed with a scrubbed reason (the data-folder path is removed) and does not stop the others. On server start, `recover_interrupted` marks any book still `ingesting` and any page still `processing` as Failed ("interrupted, retry"), because jobs run inside the server process and a restart would otherwise strand them. The web app polls `GET /books/{id}` every 2 s while anything is in progress.

### 3.5 Teacher reviews subjects, confirms
Confirming a page starts the **second look** in the background, once per page and subject hash.

### 3.6 Profiles, contact sheet, approval, reader
See sections 7 to 9.

---

## 4. Choosing the subject (`pipeline/gemini.py`, `pipeline/process.py`)

### 4.1 The Gemini call
- One call per page: the 1,600 px working copy plus the page text (capped at 8,000 characters), fixed prompt, **JSON schema** (Pydantic `SubjectAnswer`).
- Schema fields, in this order so the model looks at everything before it ranks: `things_on_page` (up to 10), `page_kind` (`single` / `several` / `scene`), `candidates` (up to 5, each with `label`, up to 5 `synonyms` including the general kind such as "bird", `box_2d`, `confidence`, `reason`).
- Boxes are `[ymin, xmin, ymax, xmax]` integers on a **0 to 1000** scale. Converted to master pixels in exactly one function, `gemini_box_to_pixels`.
- Determinism and cost control: `temperature=0`, fixed `seed=0`, `max_output_tokens=16384`, `thinking_budget=8192`, 20 s timeout per attempt, one SDK attempt (retry is decided in one place). An answer cut off at the token cap counts as a failed call.
- Retry policy: one retry; a 429 waits 10 s first. A second failure returns Failed. `process_page` **never raises**.
- The API key is read from the environment on each call, never logged, and scrubbed from any error text.
- Measured (live, `gemini-3.8-flash`, Animal Homes): **7.6 to 12.9 s** and about **1,500 input tokens** per call; median 10.9 s between answers over 37 pages.

### 4.2 Guards in code (hold even if the model ignores the prompt)
1. Drop a candidate whose label contains a setting word (forest, jungle, woods, sky, ground, grass, background, scene, scenery, landscape).
2. Merge two boxes on the same object (IoU ≥ **0.8**), keeping the more confident.
3. Drop a box that contains **two or more** other candidates (a group or the setting). One object inside another (a bird in its nest) is kept.

### 4.3 Page state rules (`decide_state`, `process_page`)
"Sure" means confidence ≥ **0.5** (`SELECT_MIN_CONFIDENCE`).

| Situation | State | Pre-selected |
| --- | --- | --- |
| Spread (unless `force`) | Unsupported | none |
| Exception, timeout, second failed attempt | Failed (with reason) | none |
| No candidates, or none could be cut out | No clear subject | none |
| Candidates, none sure | Needs subject | none |
| First choice had no usable cut-out | Needs subject | none (others are never picked silently) |
| `single` and top candidate sure | Ready | top candidate |
| `several` or `scene`, exactly one sure | Ready | that one |
| `several` or `scene`, two or more sure | Needs subject | none. A **combined cut-out** (union of the sure masks) is appended as one more candidate, label "rabbit and rat", confidence = the lowest member's |

The combined mask is **not** cleaned again, so a small subject beside a large one survives. Confidence is the model's own number and is **not calibrated**; it only screens out weak guesses and never decides between two sure subjects. The 0.5 value was tuned on the six test pages only.

### 4.4 Who answers: `SUBJECT_FINDER` (`gemini` default, `local`, `cascade`)
- `gemini`: Gemini only.
- `local`: our own models only (section 6.2). No outside call.
- `cascade`: our model first; its answer is kept **only if** (a) the page rules would pre-select exactly one subject, (b) the page text names that subject, and (c) the text is not about anything else (no "and", "&", "or", "with", and no other name our namer knows). Otherwise, or if the model/weights are missing or throw, Gemini answers.
  Why the strict gate: without the text check, our model was wrong on 4 of 7 Ready pages of Animal Homes. With it, on the 38-page test set it would answer 4 of 37 pages (about 1 in 10) with no API call, correct on all 4. On a second book set it would answer about 1 in 35.

---

## 5. Cut-outs (`pipeline/segment.py`, `sam.py`, `cascade.py`)

One internal function, `segment(image, box=None, points=None)`, chosen by `SEGMENTER`. Nothing outside `pipeline/` knows which is in use. It is read on every call.

| `SEGMENTER` | What it is |
| --- | --- |
| `stub` | Fills the box as a rectangle. No model. |
| `grabcut` (default) | OpenCV GrabCut seeded by the box, run on a 1,024 px copy, 5 iterations. No torch needed. |
| `sam2` (recommended on server) | **SAM 2.1 small** (`facebook/sam2.1-hiera-small`, Apache-2.0) on CPU via Hugging Face `transformers`. |
| `edgetam` | Faster SAM 2 variant, less accurate. |
| `mirai` | Our own U-Net alone (section 6.1). |
| `cascade` | Our U-Net first, `CASCADE_FALLBACK` (default `sam2`) when it is unsure. |
| `edgesam` | Named in the spec; **not built**. It has no installable package. It raises. |

**SAM 2.1 details.**
- Loaded once per process. The image encoder (the slow part) runs **once per page** and is cached by pixel hash for the last 8 pages, so the up-to-5 boxes on a page and later clicks only run the fast decoder.
- Measured on a laptop CPU with threads limited to 4: **3.9 to 4.1 s** encode per page, **0.13 to 0.16 s** per prompt. First call in a process also loads the model, about 10 s.
- One lock: pages run in parallel threads, but the model runs one call at a time (torch already uses all cores).
- A click is ambiguous (wing or whole bird?), so the model returns 3 masks and the largest that covers ≤ 60% of the page wins.
- **Fallback to GrabCut, per prompt**, if SAM scores its own mask under 0.5, or the mask fills more than half the box's edge band (it picked the background inside the box). A rough cut-out of the right object beats a clean one of the wrong one.
- Trial on two hand-masked pages (IoU against Kevin's masks): SAM 2.1 0.97 to 0.98 on tight boxes and clicks; GrabCut 0.81 and 0.87 on boxes but 0.25 to 0.38 on clicks.

**Mask cleanup (`clean_mask`)**: keep the largest connected region plus any region ≥ 5% of its size; fill holes smaller than 0.1% of the page (holes touching the page edge are not filled).

**Teacher routes that make a cut-out:**
- **Click** (`segment_at_point`): one positive point; Gemini names the crop (empty label if Gemini fails; the teacher types it). A click on flat background yields a rectangle around the click, not an error.
- **Refine** (`refine_mask`): reruns with the old mask's box grown just far enough to reach the click; result = old mask OR new piece, so a refine click can only add.
- **Manual outline** (`mask_from_outline`): the teacher's polygon (≥ 3 points) filled **exactly as drawn**, `source = manual`, confidence 1.0. **Calls no model**, so it works with Gemini and the segmenter both down. An optional `tidy` lets SAM snap the shape: used if it overlaps the drawing with IoU ≥ 0.3, clipped to the drawing's box grown 15%; otherwise the raw polygon is kept.

---

## 6. Models we trained ourselves

Both were trained from **random weights**. No pretrained weights are used in either shipped model.

### 6.1 Cut-out model (`cutout_model/`), box in, mask out
- **Architecture:** a 7.8 M-weight 5-level U-Net. Input is a 320 px crop around the box: RGB plus one channel marking the box (4 channels). Output is the subject's pixel mask. It outputs a mask only; it never draws.
- **Training:** loss = binary cross-entropy + Dice; AdamW, weight decay 1e-4, lr 0.001 cosine to 0; Google Colab NVIDIA L4, bf16, batch 32.
  - Run A: DUTS-TR salient-object photos, 27 epochs, best validation IoU 0.929.
  - Run B (shipped candidate): DUTS + an equal number of **pasted drawings** (4,000 anime cut-outs from `fg-00`, `fg-01` on 2,000 backgrounds), continued from run A, 16 epochs, best validation IoU 0.936.
- **Result** on 100 held-out synthetic pages (cut-outs from archives never used in training, pasted on scenes; every segmenter given the true box grown 5%):

| Segmenter | Mean IoU | Median IoU | Pages < 0.5 | Median s/page |
| --- | --- | --- | --- | --- |
| GrabCut | 0.776 | 0.831 | 11 | 2.545 (CPU) |
| SAM 2.1 small | **0.906** | 0.932 | 1 | 0.100 |
| Ours, run A (photos only) | 0.768 | 0.798 | 2 | 0.018 |
| **Ours, run B (photos + drawings)** | 0.897 | 0.921 | 1 | 0.020 |

  Run B beats GrabCut on 66 of 100 pages and SAM 2.1 on 27 of 100, about 5× faster on GPU.
- **Spot check on the real demo book** (Animal Homes, 45 Gemini boxes, never trained on): agreement with SAM 2.1 (not accuracy; no hand masks exist): **0.786 mean / 0.835 median** on 36 single-subject boxes, against 0.688 / 0.764 for GrabCut. GrabCut returned nothing on 5 small subjects; ours found all of them.
- **How to say it honestly:** "held-out *drawings*". The test pages are built the same way as run B's drawn training examples (different archives), which flatters it. The gap to SAM on real picture books is only measured as agreement, not accuracy.
- **Cascade (`pipeline/cascade.py`):** our model's mask is scored by five checks (edge sureness, fill, one-piece share, no background-in-box, agreement with the mirrored page); the score is the **lowest** of them, so a low score always names one check. Score ≥ **0.65** (calibrated on Animal Homes) keeps our mask, else the box goes to SAM 2. At 0.65 it kept **67% of boxes at 0.919 agreement** with SAM 2.1. Each routing decision is logged and counted.
- **Honest cost finding:** on a **CPU** server the cascade is **not meaningfully faster** than SAM alone (1.03× at 0.947 agreement), because SAM spends about 2.1 s once per page then 0.29 s per extra box, and one pass of ours is about 0.27 s a box. The speed-up needs a GPU (0.02 s vs 0.10 s a box on an L4). That is why the README says to leave `SEGMENTER=sam2` on the CPU server.

### 6.2 Local subject finder (`subject_model/`), page in, subjects out, no outside AI
Returns the same JSON Gemini returns: up to 5 subjects with name, synonyms, rectangle, confidence.

- **Finder** (`finder.py`): the cut-out U-Net at half width (16 to 256 channels, **2.0 M** weights, 7.5 MB), trained on DUTS-TR (10,025 train / 528 val photos; 3 in 10 pasted on paper with printed words that are *not* in the target). 37 epochs at 256 px, 29 min on a laptop GPU (Apple MPS). Validation IoU **0.827** (on photos). Its map is cut into separate blobs (≥ 0.5% of the page, a map covering > 60% of the page is treated as "found nothing"), each blob becomes a rectangle.
- **Namer** (`namer.py`): a ResNet-18 (**11.4 M** weights, 43 MB) naming a crop with one of **347** names (DomainNet's 345 classes plus `person` and `text`). Trained on DomainNet clipart, painting and sketch (189,523 images after removing 5,455 listed duplicates) plus 550 anime `person` cut-outs and 550 drawn `text` pictures. 30 epochs at 128 px, 42 min. Validation top-1 **0.590**. Watch lines: `text` 36 of 36 right with 0 false alarms; `person` 30 of 36 right, 5 of 9,495 false alarms.
- **Chooser** (`local.py`): names each blob; drops blobs that are printed words, marks or settings; lets the **page text confirm** a name (confidence 0.6 + 0.4 × namer probability if confirmed, 0.8 × probability if not), so confirmed names rank higher; builds the Gemini-shaped answer; runs the pipeline's own guards.
- **Speed and size:** 0.07 s a page warm on an M5 Max CPU, about 9 GFLOPs a page, about 740 MB of memory with both models loaded, 3.0 s cold start. Gemini median 10.9 s a page.

**Scores, 38 team-labelled pages (121 subjects), counts not percentages:**

| Mode | Subjects found | Named | First choice is a main subject | Ready right / wrong | Teacher asked |
| --- | --- | --- | --- | --- | --- |
| Gemini (37 pages answered) | **73 of 114** | **72** | **31 of 37** | 8 / 0 | 28 |
| Local, same 37 pages | 17 of 114 | 6 | 13 of 37 | 4 / 0 | 32 |

Read plainly: **Gemini is far better. The local mode is a fallback and a cost-saver for easy pages, not a replacement.** Where local does well: a single large animal on a plain page whose name is in the text. Where it fails: busy pages (it marks one big blob or the wrong thing), subjects outside its 345 names, and small subjects.

### 6.3 Experiments that did **not** make it into the product (say so if asked)
| Experiment | Outcome |
| --- | --- |
| Namer fine-tuned from ImageNet weights | Val top-1 0.613 vs 0.590, but no detectable gain on picture-book pages. Not adopted. |
| Zero-shot CLIP (MIT-licensed, 151 M weights) as the namer | Names 64 of 121 rectangles vs 21 for ours (so about 3× better naming) but its sharper probabilities pushed wrong guesses over the 0.5 line (6 wrong Ready pages). Needs recalibration before use. Not shipped. |
| Finder retrained on synthetic pasted-drawing pages | 17 to 21 of 121 on the first set; on a fresh set it was level with the shipped finder (24 vs 23). The earlier gain was partly noise. Not shipped. |
| Zoomed tiles + multi-threshold blob cuts | Roughly doubles subjects found (best 35 of 113 on fresh pages) but more candidates means more wrong Ready pages and the cascade gate stops firing. Recall and precision pull apart. |
| Fresh-page re-test (two unseen books, 35 pages, 113 subjects) | Some first-set gains did not hold. See the next list. |

**What this teaches, and a good answer to "how do you know it works":** we re-tested on **fresh unseen pages** and reported that part of our own earlier improvements did not hold. The shipped setup's "zero wrong Ready pages" held on the first set but not the fresh one (3 wrong of 5 Ready). What held across both sets: **text-confirmed pre-selections** were right (pooled 5 of 5 under the shipped gate), which is exactly why the cascade gate requires the text to name the subject.

**Caveats on every number in this section:** the test rectangles were drawn by an AI assistant from teammates' written labels and **have not been checked by a person yet** (pictures in `data/subject_testset/check/`), so counts are provisional. The test set folder is not in git. The 11 single test pages are StoryWeaver-style pages whose individual licences still need checking before use in slides.

---

## 7. Display and checks (`render/`, `checks/`)

Both are **pure functions**: images and settings in, image or results out. No network, no database, no stored state beyond an in-process decoded-file cache keyed by path, mtime and size. Same input gives the same pixels.

### 7.1 The four looks (levels 1 to 4)
Canvas 1,600 px on the longer side in the page's own proportions. Mask edge softened inward only (Gaussian sigma 1.0), so nothing outside the mask is shown. Output WebP quality 90.

| Level | Name | What happens |
| --- | --- | --- |
| 1 | Tinted | Crop the subject from the **master** through its mask. Convert to grey, stretch to the subject's own 2nd to 98th percentile range, multiply the main colour by `0.35 + 0.65 × value` so shading survives. Place on a plain background. |
| 2 | Cut-out | As 1 without the tint: real colours. |
| 3 | Faded page | On the working copy: saturation × 0.20, then 30% page / 70% background. Paste the subject back at its original place at full colour. |
| 4 | Outlined | Original working copy unchanged; the mask grown by the ring width minus the mask, filled with the main colour. Always drawn. |

- **Size** at levels 1 and 2: subject scaled to fit **50 / 70 / 90%** of the picture area (small / medium / large), by width *and* height.
- **Position:** subject centre to (0.5, 0.5), left (0.3, 0.5), right (0.7, 0.5), upper (0.5, 0.3) or lower (0.5, 0.7), kept 4% inside every edge.
- **Ring widths** on the 1,600 px canvas: thin 8 px, thick 20 px. Outlined defaults to thick unless the profile says thin. The extra ring at levels 2 and 3 uses the second preferred colour (or the main colour if only one).
- **Gathering:** a subject in far-apart pieces (two animals, a child and an ant) would stay tiny if its whole box were scaled, so at levels 1 and 2 the pieces are cut from the original, kept in left-to-right order at one common scale, and laid side by side (two rows above 4 pieces).
- **Page words:** on `main`, the page's words are **always drawn below the picture** at every look, in Atkinson Hyperlegible (free, designed for low vision), in the child's main colour when it reaches 4.5:1 on the background, else white or black. At Faded page and Outlined, the book's own printed letters are covered with the paper tone (found from the PDF's text-block boxes) so the words appear once, in one typeface. *This departs from the spec, where text was an optional P1 setting; the profile's text option is kept for compatibility and no longer changes anything.* If asked about source fidelity: covering printed letters is a display change, the original is always kept, and no drawn content is added.
- **`RENDER_VERSION` = `b3`.** Changed whenever output pixels would change. Part of every approval's identity, so a change voids all approvals. (The plan freezes it at hour 30; any later change voids every approval, including the backup books.)
- **Speed target:** 150 ms or less per page on the server. The API additionally keeps an in-memory cache of the last 256 renders keyed by page and version token.

### 7.2 The six automatic checks (`checks/core.py`)
Each returns `status` (pass / warn / fail), a measured `value`, and a plain-language `detail`. No check raises. There is **no combined score**, and none is a clinical measure.

| Check | Method | Fails or warns |
| --- | --- | --- |
| Source fidelity | Measure the mask: coverage and stray specks | Fail unless mask covers 0.1% to 60% of the page and specks (pieces under 0.1% of the page) hold ≤ 10% of it. Several whole pieces pass, with the count in the detail. |
| Page edge | Does the mask touch any page edge? | Warn: the artwork may cut the object off. |
| Background detail | Canny edges (100/200) counted outside the subject grown by 6 px, outside the text band | Levels 1/2: fail above **0.5%** of the area. Level 3: fail above **half** the original page's value. Level 4: not checked. |
| Contrast | Median luminance of a 6 px band inside the subject's edge vs the background next to it (or the outline vs background) | Warn below **3:1**. |
| Size | Levels 1/2: enlargement from the master. Levels 3/4: subject's longer side vs the page's | Warn above **2.5×** enlargement, or below **15%** of the page. |
| Text contrast | Text colour vs background | Fail below **4.5:1**. |

The 3:1, 4.5:1 (from web accessibility guidelines for text), 15% and one-half figures are **engineering starting points, not clinical CVI thresholds.** Say that out loud.

Subject match is a separate rule: only confirmed, non-omitted pages can have a version at all (`api/versions.py`).

### 7.3 Second look (`checks/second_look.py`)
Renders the subject at level 2 on black and asks Gemini to "name the main object in one to three words", with no label and no original. **Pass** if the answer shares a word (lowercased, singularised) with the label or any synonym. A miss is a **warning** that shows what the model saw; it never blocks approval. It uses the same Gemini model as subject choosing by default, so its errors can match the first pass. That is why it is a weak signal and is never used as an answer key. `SECOND_LOOK_MODEL` can point it at a different model.

---

## 8. Approval and versioning (the part to know cold)

**Hashes** (`contracts/hashing.py`, the only place they are computed):
- `settings_hash` = first 12 hex of SHA-256 of the profile's display settings as sorted compact JSON. Name, level and contrast note are **not** included. Hex colours are upper-cased first, so `#e53935` and `#E53935` hash the same.
- `subject_hash` = same hash of the selected mask file's bytes.
- A page **version** = (`subject_hash`, `settings_hash`, `level`, `render_version`). Its **token `v`** = 12-char hash of those four joined with `|`.

**Rules** (`api/versions.py`, `api/routes/approval.py`):
- A version is approved for a child when the **newest** approvals record matching the page, the profile and all four values says approve (ties broken by `_id`).
- Nothing is deleted when settings, subject or `RENDER_VERSION` change. Old approvals simply stop matching, and **match again if the teacher switches back**. That is why a changed colour and the same colour restored give the same hash.
- `POST /books/{id}/approve` compares each version sent with the current one. Pages that differ come back in a **409** with their current token and are **not recorded**, so a teacher only ever approves exactly what the sheet showed.
- The sheet route runs the checks for any page without a stored result for the current version. That is local image work of a few milliseconds a page, with no AI call, so a GET can never spend the Gemini key.
- A page can only have a version if it is **confirmed, has a subject, and is not omitted**.

**Reader enforcement** (`api/routes/reader.py`):
- `GET /reader/page/{id}?profile&level&v` recomputes the current token, compares with `v`, checks the approval, and answers an identical **403** for any failure (missing params, bad id, stale token, not approved). It renders only after those checks pass.
- Every image is `Cache-Control: no-store`, so a browser cannot keep showing a picture whose approval has lapsed.
- Tests cover three cases over real HTTP (`tests/test_reader_http.py`): approved is served; never approved is refused; approved then changed is refused; plus a stale approval gets "look again".
- Client side (`web/src/utils/readerCache.ts`): an in-memory image cache keyed by profile + level + page + token, max 16 entries, 120 s time-to-live, and failed (403) fetches never cached. After the TTL the image is refetched, which makes the server re-check approval. This is what keeps page turns fast on venue Wi-Fi despite `no-store`.

**Dev tool:** `python -m api.tools.reapprove <book_id> <old_render_version>` copies a book's newest decisions to the current `RENDER_VERSION`, marks each with `copied_from`, leaves alone any decision already made under the current version, and prints every record. It exists only for the backup books, to be run after a person re-checks their sheets.

---

## 9. API reference (Contract 1)

All under `/api`. Positions in requests and responses are **fractions 0 to 1** of page width/height from the top-left; the API converts to master pixels in one place (`api/coords.py`) and refuses out-of-range or non-finite values with 422.

| Method and path | Purpose |
| --- | --- |
| `GET /health` | Pings the database. 503 if unreachable. |
| `POST /books` | Upload PDF (+ optional title, credits). Returns `book_id`, state `ingesting`. |
| `GET /books`, `GET /books/{id}` | Book, credits, each page's state, reason, flags, kind, candidates, selection, `subject_hash`, confirmed, omitted, second look. |
| `PATCH /books/{id}` | Title and credits. |
| `DELETE /books/{id}` | 204. Removes pages, checks, approvals and files; profiles stay. |
| `POST /books/{id}/confirm-all` | Confirms every ready, non-omitted, unconfirmed page (a changed subject is skipped). |
| `POST /books/{id}/rerun` | Ask the pipeline again on pages that are not omitted or processing. New suggestions are **added** to old ones; a confirmed page keeps its subject. |
| `POST /pages/{id}/retry` | Failed page back to Processing. `force` also retries Unsupported. 409 otherwise. |
| `POST /pages/{id}/subject` | Exactly one shape (validated, `extra="forbid"`): `{candidate}`, `{candidates}` (≥ 2 shown together, masks unioned in the API with no pipeline call), `{point}`, `{label, outline[, tidy]}`, `{refine_point}`. Appends the new candidate and selects it. A changed subject needs re-confirming; the same one does not. |
| `POST /pages/{id}/confirm`, `/omit` | Confirm (409 if the subject changed while reading); omit/un-omit. |
| `GET /pages/{id}/overlay` | Cut-out tinted over the original. `?palette=1` tints every candidate in its own chip colour, selected one ringed. |
| `GET/POST /profiles`, `PATCH /profiles/{id}` | Profile with recomputed `settings_hash`. Validated by Pydantic (1 to 3 colours, hex, etc.). |
| `POST /preview` | Image for **unsaved** settings. Stores nothing. |
| `GET /render/{page_id}?profile&level&v` | Image for a saved profile (teacher screens only). 409 if `v` is stale. |
| `GET /books/{id}/sheet?profile&level` | Per page: version token, checks, second look, approval state, preview URL. |
| `POST /books/{id}/approve` | Record decisions on exactly the versions shown. 409 lists changed pages. |
| `GET /reader/{book_id}?profile&level` | Ordered **approved** pages with image URLs, skipped pages with reason (omitted / rejected / not_approved), credits, adaptation note, and which other child and level versions are fully approved. |
| `GET /reader/page/{page_id}?profile&level&v` | The image. 403 unless this exact version is approved. |

**Concurrency guards worth mentioning:** subject changes and confirmations use conditional updates (`state != processing`, `subject_hash` matches what the route read), so a click that lands mid-processing, or a subject that changes between read and write, returns 409 instead of silently overwriting. After a slow pipeline call the route re-reads the page before writing. `apply_result` merges against the page *as stored now*, never the caller's stale copy.

---

## 10. Data model (MongoDB, five collections)

| Collection | Key fields |
| --- | --- |
| `books` | `title`, `credits{author, illustrator, publisher, source, license}`, `state` (ingesting / ready / failed), `page_count`, `created_at` |
| `pages` | `book_id`, `number`, `image_path`, `view_path`, `width`, `height`, `text`, `text_boxes`, `flags`, `state`, `reason`, `page_kind`, `candidates[]`, `selected`, `subject_hash`, `confirmed`, `omitted`, `processing_started_at`, `second_look{subject_hash, status, answer, detail}`, plus `auto_state`, `auto_subject_hash`, `auto_reason` (what the pipeline originally decided, kept for the evaluation) |
| `profiles` | `name`, `level`, `settings`, `settings_hash`, `contrast_override_note` |
| `checks` | `page_id`, `subject_hash`, `settings_hash`, `level`, `render_version`, `result` (stored once per version, then read back) |
| `approvals` | `page_id`, `profile_id`, `subject_hash`, `settings_hash`, `level`, `render_version`, `decision`, `at`, optional `copied_from` |

Images are **never** in the database (they live on disk), which keeps it under the 512 MB free tier. Indexes: pages by (book, number); checks and approvals on their lookup keys. The database name comes from the path of `MONGODB_URI`.

---

## 11. Web app and testing

### 11.1 Web (`web/`)
- **Stack:** React 18.3, Vite 7, TypeScript 5.9, Tailwind 4, React Router 7, Atkinson Hyperlegible via Fontsource. Tests: Vitest, Testing Library, jsdom, MSW 2.
- **Routes:** Library `/`, subject review `/books/:id/subjects`, subject editor `/pages/:id`, profiles `/profiles`, contact sheet `/books/:id/approve`, reader `/read/:bookId` (full screen, no teacher chrome).
- **One typed client** (`web/src/api.ts`) matches Contract 1. `VITE_API_URL` empty means MSW mocks (`web/src/mocks/`, in-memory fake DB); set it to use the real API. Typed against the same shapes as `contracts/examples.json`, which a test checks.
- **Profiles:** live preview calls `POST /preview` at most once per 300 ms. Nothing is saved until Save, so trying colours never disturbs approvals. Contrast warning at 3:1 with a saved override note.
- **Contact sheet:** Approve sends back each page's version exactly as received; a 409 reloads the changed pages and says "look again".
- **Outline drawing:** records pointer positions, thins to at most 200 points, converts to 0 to 1 fractions, closes the shape.
- **Reader:** one approved page at a time. **Nothing moves on its own** (no timers, transitions or auto-advance). A child's clicks do nothing. Keys: arrows / space / PageDown turn the page, **T** toggles the teacher bar, **B** blanks the screen (held until the teacher continues), Esc closes the bar; a 1-second long-press in a corner also opens the bar. Held keys (repeat) are ignored. The bar lists only fully approved child-and-level versions; others are greyed "not approved". Prefetches the next page and the current page in every other approved version. Last screen is credits with an adaptation note.

### 11.2 Tests (counted from files on `origin/main`, not re-run for this document)
| Area | Test functions |
| --- | --- |
| `pipeline/` | 217 |
| `api/` | 158 |
| `subject_model/` | 73 (README says 74 pass on the model branch) |
| `cutout_model/` | 41 |
| `render/` | 27 |
| `contracts/` | 20 |
| `checks/` | 17 |
| `tests/` (reader over real HTTP) | 4 |
| `web/` (Vitest `it`/`test` calls) | about 191 |
| **Python total** | **557** |

Notable: `pipeline/tests/test_live.py` calls the real Gemini API only when `RUN_LIVE=1`; everything else is offline with Gemini mocked. `api/tests` run against `mongomock`. `contracts/tests` check the example JSON against the models and the hashing rules (including that colour case does not change a hash). To re-run: `.venv/bin/python -m pytest <folder>/tests -q` from the repo root; web: `npm test` in `web/`.

---

## 12. Infrastructure

### 12.1 Deploy
- **One Vultr instance** (planned 4 vCPU, 8 GB; confirm what is actually provisioned). Docker Compose runs `api` (Python 3.11-slim), `mongo` (mongo:7, no published ports) and `caddy` (built web app + reverse proxy).
- **Caddy:** HTTPS automatic for the domain; **basic auth on every path** (so a stranger with the URL cannot upload PDFs and spend the Gemini key); 55 MB request cap in front of the API's own 50 MB limit; `/api/*` to `api:8000`; everything else the SPA with `index.html` fallback. The password is hashed at start-up and Compose refuses to start without `SITE_USER` / `SITE_PASSWORD`. Only those and `SITE_ADDRESS` reach the Caddy container; **the Gemini key stays in the api container.**
- **Dockerfile:** a first stage collects every `*/requirements.txt`, so the pip layer rebuilds only when a requirements file changes. **One `pip install` for all folders**, so clashing versions fail at build time, not at integration. CPU-only PyTorch (`torch 2.15.0+cpu`, `transformers 5.22.1`, `timm 1.0.31`).
- **Auto-deploy:** a systemd timer runs `infra/autodeploy.sh` every minute; when `origin/main` moves it fast-forwards to the fetched commit (`git merge --ff-only`) and runs `docker compose up -d --build`. A failed build leaves the old containers serving. **Merging to `main` is deploying.** Rollback: stop the timer, check out the older commit, rebuild.
- `data/` is a mounted volume, so pre-processed books survive restarts and rebuilds.

### 12.2 Settings (`.env`, never committed; `.env.example` lists names)
`GEMINI_API_KEY`, `GEMINI_MODEL` (empty = `gemini-3.8-flash`), `SECOND_LOOK_MODEL`, `SEGMENTER`, `SUBJECT_FINDER`, `SUBJECT_MODEL`, `CUTOUT_MODEL`, `CASCADE_MIN_CONFIDENCE` (0.65), `CASCADE_FALLBACK` (`sam2`), `CASCADE_FLIP` (1), `MODEL_CACHE_DIR`, `TORCH_THREADS`, `PIPELINE`, `RENDER`, `PAGE_CONCURRENCY` (4), `MONGODB_URI`, `DATA_DIR`, `SITE_ADDRESS`, `SITE_USER`, `SITE_PASSWORD`, `VITE_API_URL`, `NAMER_WEIGHTS`, `FINDER_WEIGHTS`.

### 12.3 Database location (two sources disagree, so check)
The dev log (entry dated 2026-11-15 01:20) says the live API was moved to a **free MongoDB Atlas M0 cluster** (AWS us-east-1, 3-node replica set) by setting `MONGODB_URI`, with the demo data copied over (60 documents, counts matched). Compose supports this (`MONGODB_URI` from `.env`, falling back to the `mongo` container) and the API uses `pymongo[srv]` with a 5 s server-selection timeout. But `infra/DEPLOY.md` still describes the local container, and the dev log says docs were not updated. **Say "Atlas" only after confirming the server's `.env`.** Page images (about 269 MB) stay on the Vultr disk either way.

### 12.4 Pre-demo checklist for the facts I could not verify
1. On the server: `grep -E 'SEGMENTER|SUBJECT_FINDER|PIPELINE|RENDER|MONGODB_URI' /opt/mirai/.env` (do not paste the file; it holds secrets).
2. `docker compose ps` and `docker compose logs --tail 50 api`.
3. Confirm the deployed commit equals `origin/main` (`git -C /opt/mirai log -1`).
4. Confirm `NAMER_WEIGHTS`/`FINDER_WEIGHTS` resolve if `SUBJECT_FINDER` is not `gemini`.

---

## 13. Honest limits (and what not to claim)

**Product limits** (from the spec, all true):
- **No child with CVI has used it and no TVI has reviewed it.** Say "not yet reviewed by a TVI."
- Hidden parts stay hidden: a rabbit half behind a tree is cut out as half a rabbit. The app never draws the missing part.
- Objects cut off by the page edge get a warning, not a fix. Subjects enlarged more than 2.5× can look soft (warning).
- Two-page spreads are marked Unsupported, not processed badly.
- Gemini's confidence is not calibrated, and the second look uses the same AI service, so neither is proof. **The teacher's confirmation is.**
- The four levels are **presentation modes, not clinical CVI phases**; mapping them to phases needs a TVI. The app never recommends a level or assesses a child.
- Book pages are sent to Gemini to find the subject; the upload screen says so. Before classroom use: sign-in, access control, retention policy, student-privacy review. Demo children Maya and Leo are fictional.

**Technical limits:**
- Cut-outs of busy scenes (ants among leaves, deer among trees) are weaker; the teacher fixes with click, refine or outline.
- Our own models are **much weaker than Gemini** (section 6.2) and the cascade only fires on about 1 page in 10 on one set and 1 in 35 on another.
- Our cut-out model's real-book quality is measured only as **agreement with SAM**, not accuracy; its test is synthetic. On a CPU server it brings no speed-up.
- The **20-page StoryWeaver evaluation set from the spec has not been run.** What exists instead is the 38-page team-labelled set (plus 35 fresh pages), with provisional AI-drawn rectangles. Do not call these "the evaluation".
- Performance claims: "about 30 s for a 5-page book on a laptop with real Gemini calls, 4 pages at a time, GrabCut cut-outs." Do **not** extrapolate to "any book in minutes".

**Do not say:**
- "Verified" about any page.
- "N× cheaper" for the local models. There are no token counts, no price, and Gemini's FLOPs are unpublished. The defensible line is "about 1 in 10 pages answered with no API call on our test set, 0.07 s on a CPU, correct on all 4 it took, Gemini handles the rest."
- "No AI changes the picture" without "display changes on top". We tint, fade, resize, outline, and cover printed letters; we never generate content.
- That our models match SAM or Gemini.

---

## 14. Likely judge questions and short answers

**Q: What stops the AI from inventing or distorting the picture?**
A: The AI never produces pixels. Gemini returns text and rectangles; SAM returns a mask. The display crops the *original* master page through the mask. A unit test asserts every output pixel inside the mask core equals a resampled master pixel. Tint, fade, size and outlines are labelled display changes on top, and the untouched original is always kept.

**Q: How do you guarantee a child never sees an unapproved page?**
A: Approval is per (page, subject hash, settings hash, level, render version). The reader image route recomputes that token on every request and returns 403 if it does not match an approved record, so editing a profile, changing a subject, or a renderer change all invalidate it. Images are `no-store`. Over-HTTP tests cover approved, never approved, and approved-then-changed.

**Q: What if Gemini is down or wrong?**
A: Wrong: confidence is uncalibrated so it never decides between two sure subjects; the teacher confirms every page and a second AI look only ever warns. Down: a failed page becomes Failed with a reason (never raises, never blocks other pages), and the manual outline path calls **no model at all**, so a teacher can label, outline, approve and read with every AI service off. That is an acceptance test in the spec.

**Q: Why Gemini and not your own model?**
A: We measured both on 38 labelled pages. Gemini found 73 of 114 subjects and named 72; our local mode found 17 and named 6. So Gemini is the default. We built the local path as a no-API fallback and a cost-saver: a strict gate (page rules select exactly one subject, the page text names it, and the text is about nothing else) lets it answer about 1 in 10 pages on our first set, right on all 4, and Gemini takes the rest.

**Q: Why did you train models from scratch? Isn't that worse?**
A: Yes, and we measured it. We trained the namer from random weights (val top-1 0.590) and also tried an ImageNet-pretrained start (0.613 on clip art, no detectable gain on picture books), and zero-shot CLIP (names about 3× more but over-confident). We shipped what we trained and documented that it is a fallback. We did it to have an option with no outside call and to learn where the limit actually is: subject *finding* and a fixed 345-name vocabulary, not model size.

**Q: How accurate is subject selection?**
A: On 38 labelled pages Gemini's first choice was a main subject on 31 of 37 pages and it pre-selected 8 pages, all 8 right, 0 wrong; it asked the teacher on 28. Honest caveats: the labels were AI-drawn from teammates' words and are not yet human-checked, and the spec's 20-page evaluation set has not been run. We report counts, not percentages.

**Q: Why does the app ask the teacher so often?**
A: By design. Pages with several equal subjects (a hornbill, a beehive and a nest) become Needs subject with every subject offered plus a combined option. The subject is "what the story is about", which is the teacher's judgment. The demo is built around the one page the AI cannot decide.

**Q: How do you cut the subject out?**
A: SAM 2.1 small on CPU, prompted with Gemini's box. The slow image encoding (about 4 s) runs once per page and is cached, so each extra box or click costs about 0.15 s. If SAM scores its own mask under 0.5 or picks the background inside the box, that prompt falls back to GrabCut. Then a cleanup pass keeps the largest region plus any at least 5% of it and fills small holes.

**Q: Why SAM 2.1 and not EdgeSAM (which your spec names)?**
A: EdgeSAM has no installable package, only research-repo code, so `SEGMENTER=edgesam` raises. We used SAM 2.1 small, and EdgeTAM (its successor) as a faster, less accurate option. On a two-page trial SAM 2.1 scored 0.97 to 0.98 IoU against hand masks vs 0.81 to 0.87 for GrabCut on boxes.

**Q: Is your own cut-out model good?**
A: It is a 7.8 M-weight U-Net trained from scratch. On 100 held-out synthetic pages it reaches mean IoU 0.897 vs SAM 2.1's 0.906 and GrabCut's 0.776, about 5× faster on a GPU. But those pages are drawn the same way as part of its training data, so we call it "held-out drawings". On the real demo book we only measured *agreement* with SAM (0.786 mean). On the CPU server it is not faster, so we recommend SAM there.

**Q: How do you know a cut-out is good enough?**
A: Not a single score. Six separate checks (source fidelity, page edge, background detail, contrast, size, text contrast) each report a value and a plain sentence, plus the second look. The teacher sees them on the contact sheet. They say the adaptation was *built* correctly, not that it suits a child.

**Q: Where do the thresholds (3:1, 15%, 2.5×, 0.5%) come from?**
A: Engineering starting points. 3:1 and 4.5:1 come from web accessibility guidance for text, not CVI research. 15% and one-half are targets we chose to tune. None is a clinical threshold and the app says so.

**Q: How does switching child or look stay under a second?**
A: No AI runs at display time. The render is NumPy/OpenCV compositing of a saved mask, targeted at 150 ms or less per page, with a 256-entry server cache and a client-side prefetch of the next page and the current page in every other approved version. (The spec's target is under 1 s for 95% of page switches on the demo device; we do not have a measured percentile to quote.)

**Q: What happens if two teachers edit at once, or a click lands while a page is processing?**
A: Writes are conditional. A subject change on a page that went back into processing returns 409. Confirming only succeeds if the subject is still the one the route read. Approval returns 409 listing pages whose version changed since the sheet loaded, and records none of them.

**Q: Why FastAPI, MongoDB and one server?**
A: Python for one language across API, PyMuPDF, OpenCV and the models; typed Pydantic models double as the contract. Documents fit pages with variable candidate lists; images stay on disk to keep the database tiny. One Vultr box with Docker Compose and Caddy keeps deployment to "merge to main"; the whole site sits behind a password so strangers cannot spend the Gemini key.

**Q: How did four people build this in 24 hours?**
A: Three frozen contracts and one owner per folder. Everyone wrote their own stand-in for whatever they consumed (`api/stubs.py`, web mocks, hand-painted masks), then swapped in the real module with one setting. `main` always had to start, and a broken module could be bypassed by setting `PIPELINE` or `RENDER` to `stub`.

**Q: What about privacy?**
A: The demo uses fictional children only. Book pages go to Gemini to find the subject, and the upload screen says so. The API key never leaves the api container and is scrubbed from errors. Before real classroom use it needs sign-in, access control, a retention and deletion policy, and a student-privacy review. We have not done those.

**Q: What are the licences?**
A: Demo book *Animal Homes*, Pratham Books on StoryWeaver, CC BY 4.0. The credits screen keeps author, illustrator, publisher, source and licence and states that pages were adapted. Atkinson Hyperlegible is SIL OFL. SAM 2.1 is Apache-2.0. Training data: DUTS (research use), DomainNet (non-commercial research and education), anime-segmentation (CC0). Our weights derive from those, so they are a research artefact, not a commercial one.

**Q: What would you do next?**
A: Get a TVI to review the looks; run the 20-page evaluation with human-checked labels; have a person verify the test rectangles; add sign-in and retention for real use; recalibrate CLIP as a namer on data that is not the test pages; and measure a real cost per page from token usage rather than claiming a ratio.

---

## 15. Numbers cheat-sheet

| Fact | Value | Source |
| --- | --- | --- |
| Upload limits | 30 pages, 50 MB | `api/settings.py` |
| Master / working copy | 300 DPI, ≤ 3,000 px / 1,600 px long side | `pipeline/ingest.py` |
| Gemini model | `gemini-3.8-flash` | `pipeline/gemini.py` |
| Gemini call | 7.6 to 12.9 s, about 1,500 input tokens | `pipeline/README.md` |
| Candidates per page / sure threshold | ≤ 5 / ≥ 0.5 | `process.py` |
| Hash length | 12 hex chars of SHA-256 | `contracts/hashing.py` |
| `RENDER_VERSION` | `b3` | `render/core.py` |
| Canvas / WebP quality | 1,600 px / 90 | `render/core.py` |
| Look 3 fade | saturation × 0.2, 30% page / 70% background | `render/core.py` |
| Checks | 6; contrast 3:1, text 4.5:1, size 2.5× and 15%, background 0.5% / ½ | `checks/core.py` |
| SAM 2.1 small | encode about 4 s/page, about 0.15 s/prompt (CPU, 4 threads) | `pipeline/README.md` |
| Own U-Net | 7.8 M weights; mean IoU 0.897 vs SAM 0.906 (synthetic held-out) | `cutout_model/README.md` |
| Cascade threshold | 0.65; keeps 67% of boxes at 0.919 agreement | `pipeline/cascade.py` |
| Namer | ResNet-18, 11.4 M weights, 347 names, val top-1 0.590 | `subject_model/README.md` |
| Finder | U-Net half width, 2.0 M weights, val IoU 0.827 | `subject_model/README.md` |
| Local vs Gemini (38 pages) | found 17 vs 73 of 114; named 6 vs 72 | `subject_model/README.md` |
| Local speed | 0.07 s/page warm, about 740 MB; Gemini median 10.9 s | dev log |
| Cascade savings | about 1 in 10 pages (first set), about 1 in 35 (fresh set) | dev log |
| Python tests | 557 test functions (counted) | this document |
| Web reader image cache | 16 entries, 120 s TTL | `readerCache.ts` |
| Server render cache | 256 entries | `api/images.py` |

---

## 16. Where to find things

| Looking for | Read |
| --- | --- |
| Behaviour and exact interfaces | `Product and technical spec.md` (spec wins on behaviour and interfaces) |
| Schedule, ownership | `Mirai 24-Hour Build Plan.md` |
| Pipeline details, Gemini findings, SAM trial | `pipeline/README.md` |
| Own cut-out model | `cutout_model/README.md` |
| Own subject finder, results, limits, credits | `subject_model/README.md`, `subject_model/weights/README.md` |
| Deploy, rollback | `infra/DEPLOY.md` |
| Everything we measured and decided, in order | `CLAUDE_NOTES.md` (local, gitignored) |
| Product guardrails and wording rules | `PRODUCT.md` |

Where documents disagree: the spec wins on behaviour and interfaces; the build plan wins on schedule, ownership and scope; **the code wins on what is actually running.** Known departures from the spec: SAM 2.1 instead of EdgeSAM; page words always shown at every look; larger subject sizes and ring widths (`RENDER_VERSION b3`); outline tidy uses IoU 0.3 and a 15% box growth (spec says 0.6 and 12 px); the database may be Atlas instead of a local container.
