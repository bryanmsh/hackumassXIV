# Mirai Product and Technical Spec

Nov 13, 2026 · @Andrew Choi

# Part 1: Product requirements

## Summary

Mirai adapts picture-book pages for children with cortical visual impairment (CVI) using the book's original artwork, and gives the teacher control over what each child is shown. The app finds the subject of each page once, then re-displays that same cut-out for each child's profile.

**What it guarantees**

- The subject always comes from the original page. Nothing is drawn or invented by AI.
- Every adapted page passes technical checks, and a teacher approves it before a child sees it.
- A child is never shown a version the teacher has not approved.

**What it does not guarantee**

- That a particular child can see or understand a page. Only a teacher and the child's own response can establish that.
- That the four levels match clinical CVI phases. That needs review by a teacher of students with visual impairments (TVI).

## Problem and users

Children with CVI recognize objects far better in simple pictures: one object, little clutter, strong contrast. Picture books are the opposite, so teachers rebuild pages by hand and each child gets only a few adapted books.

- **Primary user:** a teacher of students with visual impairments (TVI), who adapts materials today.
- **Secondary users:** parents reading at home, and early-intervention and special-education staff.
- **Buyers:** school district special-education budgets and CVI organizations.
- **The child** is the audience, never the operator.
- **Platform:** a web app used in a desktop or laptop browser, by teacher and child alike. Tablets and touch gestures are not a target.

## Priorities

**P0: must have**

- Upload a PDF picture book. Every page ends in a clear state, and one failed page never blocks the rest.
- Read each page's text and use it, with the picture, to choose the subject.
- Cut the subject out of the original page and save one reusable mask per page.
- Teacher subject review: confirm the subject, pick a different one, or leave the page out.
- Manual fallback: the teacher labels the subject and draws a rough outline, which is used as the cut-out exactly as drawn. It works even when the AI services are down.
- Child profiles with a name, one of four levels, preferred colors and a background color.
- Switch child or level in under a second, using saved cut-outs and no new AI work.
- Technical checks on every adapted page.
- Teacher approval tied to a specific child and level. Changing either never skips review.
- Full-screen reader that the teacher paces and that shows approved versions only.
- Credits screen for each book with author, illustrator, publisher and license.

**P1: should have**

- Subject size and position in the profile.
- Page text shown large below the picture, on or off per child.
- Click to refine a cut-out that missed a tail, ear or leg.
- Tidy the edge of a hand-drawn outline so it fits the object.
- Contrast warning based on the subject's real edge colors, not only the chosen swatch.
- Blank screen between pages, controlled by the teacher.
- Results page with measured counts from a hand-labeled page set.
- Profile presets, added only after a TVI reviews them.

**P2: nice additions**

- Keep a small group of objects on pages with no single subject. (Built: see the combined cut-out in "Choosing the subject.")
- Photo of a physical page, and scanned PDFs with no text layer.
- Print or export as PDF, with credits included.
- Read-aloud, teacher notes and custom colors.

## How it works

The slow AI work happens once per book; everything after that is fast, repeatable image display from saved parts.

1. **Upload.** The teacher uploads a PDF.
2. **Process once.** For each page the app saves an untouched copy, reads the text, chooses a subject and cuts a mask. This can take several seconds per page.
3. **Store.** Original page, mask, text and subject label are kept and reused for every child.
4. **Subject review.** The teacher confirms or corrects the subject, once per page.
5. **Display.** A child's profile and level decide how the saved cut-out is shown. No AI runs at this step, so every child sees the same approved subject.
6. **Approve and read.** The teacher approves the versions they plan to use, then reads with the child.

The one-second target applies to step 5 only, measured on the demo device.

**Supported books (P0)**

- PDF, up to 30 pages and 50 MB, one book page per PDF page.
- Rotated pages are turned upright automatically.
- A text layer is used when present. Without one, the app still works but is less sure of its choices and asks the teacher more often.
- Two-page spreads are detected and marked Unsupported, not processed badly. The teacher can leave them out or process them anyway.
- Pages whose artwork is very low resolution get a quality warning.

**Page states**

| State | Meaning | What the teacher can do |
| --- | --- | --- |
| Processing | Work in progress | Review other pages meanwhile |
| Ready | One subject is selected, and the app is reasonably sure of it | Confirm or change it |
| Needs subject | The app is unsure which object matters, or the page has several subjects | Pick one, or show several together |
| No clear subject | No subject was found, or none could be cut out | Click the object, outline it by hand, or leave the page out |
| Failed | A timeout, a bad cut-out or an unreadable page | Retry, label and outline it by hand, or leave the page out |
| Unsupported | A two-page spread or another layout the app does not handle | Leave the page out, or process it anyway |

## Choosing the subject

The subject is what the story is about on that page, not the largest thing in the picture. If the text says "The rabbit was hiding under the tree," the subject is the rabbit.

**How the app chooses**

- It reads the picture and the page text together.
- It decides what kind of page this is: one subject, several subjects, or a scene.
- It returns every main subject of the page, up to 5 candidates, each with a label and a confidence from 0 to 1, for example `rabbit, 0.84`. A candidate is one person, animal or object, or one tight group of the same kind. The setting (forest, sky, grass) is never a candidate.
- A candidate counts as sure at a confidence of 0.5 or more.
- On a one-subject page, the top candidate is pre-selected when it is sure, and the page is Ready.
- On a page with several subjects, or a scene, a lone sure candidate is pre-selected in the same way. When two or more are sure, nothing is pre-selected: the page becomes Needs subject, and the app adds one more suggestion, a combined cut-out of every sure candidate, so the teacher can show one of them or all of them together.
- A page where no candidate is sure becomes Needs subject. A page with no candidate, or none that could be cut out, becomes No clear subject.
- The same page gives the same answer each time it is processed, as far as the AI service allows.

The AI's confidence is self-reported and tends to run high, so 0.5 only screens out weak guesses. It never decides what a page is about when there is more than one answer; the teacher does. The 0.5 value is tuned on the test pages only, never on the evaluation pages.

A combined cut-out puts several objects in front of the child at once. Whether that suits a child is the teacher's decision at subject review and again at approval.

**Subject review (P0)**

The teacher sees every page in a grid, with the chosen subject highlighted on the original picture and its label and confidence beside it.

| Action | How |
| --- | --- |
| Confirm | One click per page, or "Confirm all" after scrolling the grid |
| Pick a different subject | Click another highlighted candidate, or click the object itself on the page |
| Show several subjects together | Click more than one suggestion, or pick the combined suggestion on a page with several subjects |
| Fix a cut-out (P1) | Click the missing part, such as a tail or ear, to add it |
| Leave the page out | Marks the page as omitted |
| Label and outline by hand | Type what the object is, then draw a rough outline around it on the page |

Changing a page's subject or cut-out means that page needs approval again.

## Child profiles

A profile holds the display choices a teacher makes for one child. The teacher sets it; the app never assesses a child or recommends a level.

**Settings**

| Setting | Options | Default | Priority |
| --- | --- | --- | --- |
| Name | First name | None | P0 |
| Level | Tinted, Cut-out, Faded page, Outlined | None; the teacher chooses | P0 |
| Preferred colors | 1 to 3 of 8 swatches; the first is the main color | Red | P0 |
| Background color | Black, dark gray, navy, white | Black | P0 |
| Subject size | Small, medium, large (40%, 60%, 80% of the picture area) | Medium | P1 |
| Subject position | Center, left, right, upper, lower | Center | P1 |
| Text | Off, or large below the picture | Off | P1 |
| Extra outline | Off, thin, thick; applies at Cut-out and Faded page | Off | P1 |

Size and position apply at levels 1 and 2. Levels 3 and 4 keep the book's own layout. Position exists because some children see better in one part of their visual field.

**The four levels are presentation modes, not a ladder**

| Level | Name in the app | What the child sees |
| --- | --- | --- |
| 1 | Tinted | The subject alone, tinted in the child's main color, on a plain background |
| 2 | Cut-out | The subject alone, in its real colors, on a plain background |
| 3 | Faded page | The whole page, faded, with the subject kept vivid |
| 4 | Outlined | The original page, with the subject always outlined in the child's main color |

- The app shows the names, not the numbers, so the levels do not read as steps to climb. This document uses the numbers as shorthand.
- A child may recognize a real yellow duck at level 2 more easily than a red shape at level 1. Lower is not always easier.
- A teacher can use level 2 for one book and level 1 for another. The app does not treat that as going backward.
- The profile's level is the starting point. The teacher can switch level while reading, among approved versions.
- The app does not label levels with CVI phases until a TVI has reviewed the mapping.

**Color**

Swatches: red `#E53935`, yellow `#FDD835`, orange `#FB8C00`, green `#43A047`, blue `#1E88E5`, purple `#AB47BC`, pink `#EC407A`, white `#FFFFFF`.

- The main color tints the subject at level 1 and draws the outline at level 4.
- The extra outline at levels 2 and 3 uses the second preferred color, or the main color when only one is chosen.
- The app warns when the main color and background have a contrast ratio below 3 to 1. The teacher can override the warning with a short note, which is saved with the profile.
- At levels 2 and 3 the subject keeps its own colors, so the swatch check is not enough. P1 adds a warning based on the subject's actual edge colors against the background.
- When text is shown, it is checked separately at 4.5 to 1.
- These ratios come from web accessibility guidelines for text. They are an engineering starting point, not a clinical rule for CVI.

**Demo profiles**

| Child | Level | Colors | Background | Position | Text |
| --- | --- | --- | --- | --- | --- |
| Maya | Tinted | Red | Black | Center | Off |
| Leo | Cut-out | Yellow, blue | Black | Left | Below the picture |

Both children are fictional.

## Checks and approval

Automatic checks and teacher approval are two separate steps, and the app never calls a page "verified." The checks say the adaptation was built correctly; only the teacher says it is right for a child.

**Technical checks (automatic)**

| Check | What it confirms | Result if it fails |
| --- | --- | --- |
| Subject match | The subject is the one the teacher confirmed in subject review | Unconfirmed pages stay out of the reader |
| Source fidelity | The cut-out is taken from the untouched original through the saved mask, with no stray specks. A cut-out of several subjects may be in several pieces | Flagged, with the cut-out shown over the original |
| Page edge | The cut-out does not touch the edge of the page, where the artwork may cut the object off | Warning |
| Background detail | At levels 1 and 2 the area around the subject is plain. At level 3 background detail is no more than half that of the original | Flagged |
| Subject visibility | The subject stands out from the background, is not enlarged so far that it looks soft, and at levels 3 and 4 is at least 15% of the page's length so it can be found | Warning |
| Second look | A second AI pass, shown only the adapted page, names the subject. It uses the same AI service as subject choosing, so it is a weak signal and only ever a warning | Warning; shows what it saw instead |

- Each measurement is reported on its own. There is no single "clutter score," and none of these is a clinical measure of visual complexity.
- The 15% and one-half figures are engineering targets to tune, not CVI thresholds.

**What "original pixels" means**

The promise is source fidelity: no AI-drawn or invented detail, ever. Tinting, resizing, repositioning and outlines are display changes applied on top of the original cut-out. The app names them as such, and the untouched original is always kept.

**Teacher approval**

Approval is given to a specific version: this page, this subject and cut-out, this child's profile, this level.

1. The teacher picks the children and levels they plan to use for a book.
2. For each child and level, the app shows a contact sheet of every page with its check results.
3. The teacher approves the sheet, or rejects single pages on it.

- Subject review happens once per page. Approval happens once per child and level, a sheet at a time. A 20-page book for two children at one level each is two sheets, not 160 decisions.
- Approval covers exactly what the sheet showed. If anything changed while the sheet was open, the app asks the teacher to look again.
- Editing a profile's colors, size or position needs a fresh sheet for the new settings. Switching back to the earlier settings brings the earlier approvals back.
- Changing a page's subject or cut-out means that page needs approval again. Going back to the earlier subject brings its approvals back.

**Rejected and failed pages**

The teacher chooses one of three: retry the adaptation, pick or outline a different subject, or deliberately leave the page out. The app never swaps in the original page on its own. Omitted pages, and pages rejected for one child and level, are skipped in that version and listed before reading starts.

**Manual retry**

When the app cannot find or cut the subject, the teacher types what the object is and draws a rough outline around it with a finger or mouse. The app uses that outline as the cut-out, still taken from the original page, exactly as drawn. Tidying the edge to fit the object is P1. The same checks run, and the page is marked "outlined by teacher" on the contact sheet.

## Reader

The reader shows one approved page at a time, full screen, at the pace the teacher sets. Children with CVI can need extra time to process what they see, so nothing moves unless the teacher moves it.

- Pages never advance on their own.
- No animations, flashing transitions or visible buttons.
- A child's clicks do nothing. The teacher turns pages with the arrow keys or space and opens the teacher bar with the T key.
- Optional blank screen in the background color between pages, held until the teacher continues (P1).
- The teacher bar offers only the child and level versions that are fully approved for this book. An approved version appears in under a second.
- Versions that are not approved are shown greyed out. To approve one, the teacher leaves the reader and opens its contact sheet, so a child never sees a review screen.
- Omitted and rejected pages are skipped, and the teacher bar says which page was skipped.
- The last screen is the credits: title, author, illustrator, publisher, source, license, and a note that the pages were adapted.

## Acceptance criteria

The build is done when each row below can be shown at the table. Numeric targets are engineering goals, not CVI accessibility thresholds.

| Area | Acceptance test |
| --- | --- |
| Book processing | Every page of a supported PDF ends as Ready, Needs subject, No clear subject or Failed. No page is lost without a state. |
| Subject selection | On the 20-page evaluation set, report as a count how many pre-selected subjects match the hand label. Target: no more than 1 confidently wrong page. |
| Honest uncertainty | Pages the app flags as unsure are counted separately from pages it got confidently wrong. |
| Source fidelity | No adapted page contains content that is not in the original. Cut-out defects are flagged, not hidden. |
| Display speed | Switching child or level on a processed book takes under 1 second for 95% of page switches on the demo device. |
| Approval | In testing, no unapproved version ever appears in the reader, including after a profile edit or a subject change. |
| Background detail | Levels 1 and 2 show a plain background on every page; level 3 meets the one-half target. |
| Failure recovery | With one page forced to fail, the teacher can retry it or leave it out, and the rest of the book is usable. |
| Credits | Every book ends with a complete credits screen. |
| Manual fallback | With the AI services switched off, a teacher can label and outline a subject, approve the page and read it. |

**Evaluation (P1)**

- A hand-labeled set of 20 StoryWeaver pages, with the intended subject marked by a teammate before any AI output is seen.
- These 20 pages are never used for tuning. The demo book is tuned on, so it is left out of the reported numbers.
- Results are reported as counts, not percentages: pages, correct subjects, correctly flagged pages, confidently wrong pages, cut-out defects and processing time.
- The "second look" AI check is never used as the answer key.
- The ChatGPT comparison is run once by hand on a few pages for one slide. It is an illustration, not a measured result.

## Demo scope

The demo is six pages of one book, two children and four levels, built around one page the AI gets wrong.

1. Upload six pages of *Animal Homes*, including one deliberately hard page.
2. Show each page reaching a state.
3. Show the page where the app could not choose on its own: the one with a hornbill, a beehive and a nest of equal weight. It arrives as Needs subject, offering each of the three and all three together.
4. The teacher picks the hornbill with one click.
5. Checks rerun, and the teacher approves a contact sheet for Maya and one for Leo.
6. Read the book, switching between Maya and Leo with no regeneration.

The hard page is the point of the demo. It shows a tool that admits uncertainty and keeps a person in charge, not an image filter. Letting a judge pick any book is a stretch goal once this works.

## Privacy and attribution

- The demo uses fictional children only. No real child's name or settings are stored.
- Book pages are sent to an outside AI service to find the subject. The upload screen says so.
- Before any classroom use: sign-in, access controls, a retention and deletion policy, and a review against student privacy rules.
- StoryWeaver books are CC BY 4.0. Adapted copies must keep the original credits and license and say that changes were made. The credits screen does this, and any export must include it.

## Known limits

- **Hidden parts stay hidden.** A rabbit half behind a tree is cut out as half a rabbit at levels 1 and 2. The app never draws the missing part; the teacher can use level 3 or 4 for that page or leave it out.
- **Objects cut off by the page edge** get a warning, not a fix.
- **Small subjects enlarged a lot can look soft.** The app warns when a subject is enlarged more than 2.5 times.
- **The AI's confidence is not calibrated**, and the second look shares the same AI service, so neither is proof that a subject is right. The teacher's confirmation is.
- **No child with CVI has used the tool, and no TVI has reviewed it yet.**

## Out of scope

- Assessing or diagnosing CVI, or recommending a level.
- Any claim that the checks prove a child can see or understand a page.
- Live camera mode and whole-book video capture.
- Teacher accounts and sharing adapted books between teachers.
- Commercial books.

## Open questions

- [ ] Which TVI can review the levels, size, position and color choices? The email goes out tonight with mock-ups. With no reply by judging, the pitch says "not yet reviewed by a TVI."
- [ ] Is *Animal Homes* the right demo book? Most of its pages name two animals, such as "Spiders spin their homes. Tiny termites build tall, tall homes," so most pages would need the teacher to pick.
- [ ] Which six pages go in the demo, and which is the hard page?
- [ ] Should a teacher be able to approve several levels for one child on a single sheet?

**Next step:** test subject choosing and cut-outs on six deliberately varied StoryWeaver pages before building the rest of the interface.

# Part 2: Technical requirements

Mirai is four modules joined by three contracts, which are frozen as written in this part. Each of four owners can start now: everyone makes their own fake inputs, so nobody waits for anyone else's code, and the lanes meet at three scheduled checkpoints.

## Architecture

&#91;embedded content: architecture · four modules, their owners, three contracts\]

Arrows point from a caller to what it calls. The web app knows only the HTTP API. The API reaches the pipeline and the display code only through the Contract 2 functions. The pipeline hands the display code nothing but image files.

## Tech stack

One Python backend, one React frontend, one hosted database and one server; every choice has a fallback that keeps the demo alive.

| Part | Choice | Why | Fallback |
| --- | --- | --- | --- |
| Web app | React 18, Vite, TypeScript, Tailwind CSS | Fast to build; typed API client | None needed |
| API mocking | Mock Service Worker with JSON fixtures | Frontend runs with no backend | Static JSON files |
| API server | Python 3.11, FastAPI, Uvicorn, Pydantic v2 | Same language as the image code; typed request and response models | None needed |
| PDF | PyMuPDF | Renders pages at a chosen resolution and reads the text layer | Poppler (`pdftoppm`, `pdftotext`) |
| Subject choosing | Gemini API, Flash tier, JSON output | Reads picture and text together and returns boxes | Teacher picks or outlines every subject |
| Cut-outs | EdgeSAM on CPU first; SAM 2 small on a GPU if quality is poor | Box and point prompts; runs once per page | Teacher's rough outline as the mask (P0, needs no model) |
| Image display | NumPy, OpenCV, Pillow; WebP output | Plain compositing, no model, repeatable; small files for the reader | None needed |
| Text font | Atkinson Hyperlegible | Free font designed for low-vision readers | Any bundled sans-serif |
| Database | MongoDB Atlas free cluster, PyMongo | Sponsor prize; flexible documents | Local MongoDB in Docker |
| Image storage | Disk on the server | Keeps images out of the 512 MB database | Same |
| Hosting | One Vultr instance, Docker Compose, Caddy for HTTPS, the domain and a password on the whole site | Sponsor prize; one box to manage; keeps strangers off the Gemini key | Laptop with pre-processed books |
| Dependencies | One requirements file per Python folder | Owners add packages without touching a shared file | None needed |

To confirm in the first hours: the current Gemini model name, and that it returns boxes as `[ymin, xmin, ymax, xmax]` on a 0 to 1000 scale.

## Contracts

The three contracts below are frozen as written, so there is no kickoff meeting to wait for. Everyone reads this section before their first task and raises objections within the first hour. After that, a contract changes only if all four owners agree, and only by adding fields, never by renaming or removing them.

**Hashes, not version numbers**

Approvals are matched on hashes of what was actually shown, so switching back to earlier settings brings earlier approvals back.

- `settings_hash`: first 12 hex characters of the SHA-256 of a profile's display settings as sorted JSON. Name, level and the contrast note are not part of it.
- `subject_hash`: the same hash of the selected mask file's bytes.
- A page **version** is the four values `subject_hash`, `settings_hash`, `level`, `render_version`. Its **token** `v` is the 12-character hash of those four joined.
- One shared helper in `contracts/hashing.py` computes all three, so no two modules can disagree.

**Contract 1: HTTP API (web app to API)**

All paths start with `/api` and return JSON unless marked image. Images are WebP at quality 90 and are sent with `Cache-Control: no-store`.

| Method and path | Body | Returns |
| --- | --- | --- |
| `POST /books` | PDF file, optional `credits` | `book_id` at once, with book state `ingesting`. Refuses files over 30 pages or 50 MB |
| `GET /books`, `GET /books/{id}` | None | Title, credits, book state, and each page's state, reason, flags, page kind, candidates, selected subject, `subject_hash`, confirmed, omitted, second-look result |
| `PATCH /books/{id}` | `title`, `credits` | Book |
| `POST /pages/{id}/retry` | Optional `{force}` | Page back in Processing. `force` processes an Unsupported page anyway |
| `POST /pages/{id}/subject` | One of `{candidate}`, `{candidates}` (two or more shown together), `{point}`, `{label, outline}` with optional `tidy` (P1), or `{refine_point}` (P1) | Page with its new `subject_hash` |
| `POST /pages/{id}/confirm`, `POST /books/{id}/confirm-all` | None | Updated pages; the second look starts in the background |
| `POST /pages/{id}/omit` | `{omitted}` | Updated page |
| `GET /pages/{id}/overlay` | None | Image: cut-out tinted over the original |
| `GET /profiles`, `POST /profiles`, `PATCH /profiles/{id}` | `name`, `level`, `settings`, `contrast_override_note` | Profile with `settings_hash` |
| `POST /preview` | `{page_id, settings, level}` | Image for unsaved settings. Stores nothing |
| `GET /render/{page_id}?profile=&level=&v=` | None | Image for a saved profile, used by the contact sheet. Teacher screens only; the reader never calls it |
| `GET /books/{id}/sheet?profile=&level=` | None | Per page: its version, check results, second-look result, approval state, preview URL |
| `POST /books/{id}/approve` | `{profile_id, level, pages: [{page_id, version, decision}]}` | Approval records. 409 with the list of pages whose current version differs from the one sent; those are not recorded |
| `GET /reader/{book_id}?profile=&level=` | None | Ordered approved pages with image URLs, skipped pages, credits, and which other child and level versions are fully approved |
| `GET /reader/page/{page_id}?profile=&level=&v=` | None | Image. 403 unless `v` is the current token and that version is approved |
| `GET /eval/summary` (P1) | None | Evaluation counts |

**Contract 2: Python functions (API to pipeline, display and checks)**

```python
# contracts/types.py  (Pydantic models)
PageAsset   = page_number, image_path, view_path, width, height, text,
              text_source: "layer" | "none", flags: list[str]     # spread, low_quality
Candidate   = label, synonyms: list[str], box: [x0, y0, x1, y1], confidence: float,
              mask_path, mask_hash, source: "auto" | "click" | "manual"
PageResult  = state: "ready" | "needs_subject" | "no_clear_subject" | "unsupported" | "failed",
              page_kind: "single" | "several" | "scene" | None,
              candidates: list[Candidate], selected: int | None, reason: str | None
Settings    = colors: list[hex], background: hex,
              size: "small" | "medium" | "large",
              position: "center" | "left" | "right" | "upper" | "lower",
              text_mode: "off" | "below", outline: "off" | "thin" | "thick"
Profile     = id, name, level: 1..4, settings: Settings, settings_hash,
              contrast_override_note: str | None
CheckResult = fidelity, page_edge, background, contrast, size, text_contrast
              # each: status "pass" | "warn" | "fail", value, detail
SecondLook  = status: "pass" | "warn" | "pending", answer, detail

# pipeline/  (Owner A)
rasterize(pdf_path, out_dir) -> list[PageAsset]
process_page(asset, out_dir, force=False) -> PageResult
segment_at_point(image_path, x, y, out_dir) -> Candidate
mask_from_outline(image_path, label, points, out_dir, tidy=False) -> Candidate   # tidy=True is P1
refine_mask(image_path, mask_path, x, y, out_dir) -> Candidate                   # P1

# render/ and checks/  (Owner B)
render(image_path, view_path, mask_path, settings, level, text, fmt="webp") -> bytes
overlay(view_path, mask_path) -> bytes
run_checks(image_path, view_path, mask_path, settings, level, text) -> CheckResult   # no network, no stored state
second_look(image_path, mask_path, label, synonyms) -> SecondLook                 # one AI call
RENDER_VERSION: str
```

**Contract 3: image files (pipeline to display)**

```text
data/books/{book_id}/source.pdf
data/books/{book_id}/pages/{n}.png          master: RGB, rendered at 300 DPI, longer side capped at 3,000 px
data/books/{book_id}/pages/{n}_view.png     working copy: longer side 1,600 px
data/books/{book_id}/masks/{n}_{hash}.png   8-bit, one channel, same size as the master, 255 = subject
```

Positions are measured from the top-left corner of the page. In Contract 1 (boxes, clicks, outlines and refine points, in requests and responses) they are fractions from 0 to 1 of the page's width and height. In Contracts 2 and 3 they are pixels of the master page image. The API converts between the two in one place, `api/coords.py`, and refuses a position outside 0 to 1. Mask files are never overwritten; a new cut-out is a new file.

## Implementation: pipeline (Owner A)

The pipeline turns a PDF into page images, text, subject candidates and masks. It has no database and no web code; it reads and writes files and returns the contract types.

**Ingest: `rasterize`**

- Render each PDF page with PyMuPDF at 300 DPI, with the page's rotation applied, and cap the longer side at 3,000 px. This is the master, and every cut-out is taken from it.
- Save a 1,600 px working copy for display at levels 3 and 4 and for overlays.
- Read the page's text layer. Empty text sets `text_source` to `none`.
- Flag `spread` when width is more than 1.9 times height.
- Flag `low_quality` when the page is a single embedded image whose own longer side is under 1,000 px. This measures the artwork, not the paper size.

**Subject choosing: `process_page`**

1. A page flagged `spread` returns Unsupported, unless `force` is set.
2. Send the working copy and the page text to Gemini with a fixed prompt and a JSON schema.
3. The schema returns `things_on_page` (everything the model can see, listed before it ranks), `page_kind` (single, several, scene) and up to 5 candidates, most important first: `label`, up to 5 `synonyms` that include the general kind of thing (hornbill: bird), `box`, `confidence`, and a one-line `reason`. The prompt asks for every main subject, one person, animal or object per candidate.
4. Three guards in code hold even when the model ignores the prompt: drop a candidate whose label is the setting (forest, sky, ground, background), drop a box that holds two or more other candidates, and merge two boxes on the same object (IoU of 0.8 or more).
5. Convert boxes from Gemini's 0 to 1000 scale to master pixels, and cut a mask for each candidate. A candidate with an empty mask is dropped.
6. Set the state in this order, where "sure" means a confidence of 0.5 or more:
   - No clear subject when there are no candidates, or none gave a usable cut-out.
   - Needs subject when no candidate is sure, or when the model's first choice gave no usable cut-out. The others are never picked silently.
   - Ready, with the top candidate selected, when `page_kind` is single and that candidate is sure.
   - When `page_kind` is several or scene: Ready with the one sure candidate selected if there is exactly one. With two or more, append a combined candidate and return Needs subject with nothing selected.
7. The combined candidate is an ordinary `Candidate`, so no contract changes: its mask is the union of the sure candidates' masks, its label joins their labels ("rabbit and rat"), its synonyms are all of theirs, its confidence is the lowest of theirs, its box surrounds them all, and its `source` is `auto`. It comes after the single candidates.
8. Any exception, a 20-second timeout, or a second failed attempt returns Failed with a `reason`. A rate-limit reply waits and retries once. The function never raises.

Every Gemini call uses a fixed seed, so the same page is likelier to get the same answer. Each call is capped at 16,384 output tokens, 8,192 thinking tokens and 8,000 characters of page text; an answer cut off by a cap counts as a failed call.

Confidence is the model's own estimate and is not calibrated, so it only screens out weak guesses and never chooses between two sure subjects. The 0.5 value is tuned on the six test pages, never on the 20 evaluation pages.

**Cut-outs**

- Run the segmenter on the master with the candidate's box as the prompt.
- Clean the mask: keep the largest connected region plus any region at least 5% of its size, and fill holes smaller than 0.1% of the page. A combined cut-out is not cleaned again, so a small subject beside a large one is kept.
- Save the mask under its own hash and return the hash in the candidate.
- `segment_at_point` runs the segmenter with one positive point where the teacher clicked, and asks Gemini to label that crop. If Gemini fails, the label is empty and the teacher types it.
- `refine_mask` (P1) reruns with the original prompt plus the new point.

**Manual label and outline: `mask_from_outline`**

- **P0, `tidy=False`:** fill the teacher's polygon (at least 3 points) and use it as the mask, exactly as drawn. This calls no model, so it works when Gemini and the segmenter are both down.
- **P1, `tidy=True`:** run the segmenter with the polygon's bounding box as the prompt. If its mask overlaps the polygon with an IoU of 0.6 or more, use it, clipped to the polygon grown by 12 px. Otherwise keep the raw polygon.
- Either way the candidate has `source` set to `manual`, confidence 1.0, and the teacher's label.

**Segmenter choice**

Both models sit behind one internal function, `segment(image, box=None, points=None)`, selected by the `SEGMENTER` setting. Nothing outside `pipeline/` knows which one is in use.

## Implementation: display and checks (Owner B)

`render` and `run_checks` are pure functions: images and settings in, image or results out, with no network, no database and no stored state. The one AI call, `second_look`, is a separate function that the API runs in the background.

**Display: `render`**

The output canvas is 1,600 px on its longer side, in the page's own proportions. When text is shown, the bottom 16% is the text band and the rest is the picture area. The mask edge is softened with a 2 px blur.

| Level | Steps |
| --- | --- |
| 1 Tinted | Crop the subject from the master through its mask. Convert to light and dark values, stretched to the subject's own range. Multiply the main color by `0.35 + 0.65 x value` so shading survives. Scale, place, and fill the rest with the background color. |
| 2 Cut-out | As level 1 without the tint: the subject keeps its own colors. |
| 3 Faded page | On the working copy, cut saturation to 20%, then blend 30% page with 70% background color. Paste the subject back at its original place and full color. |
| 4 Outlined | Leave the working copy unchanged. Grow the mask by the outline width, subtract the mask, and fill that ring with the main color. |

- **Size (levels 1 and 2):** the subject's longer side becomes 40%, 60% or 80% of the picture area's shorter side, so a large subject always fits above the text band.
- **Position (levels 1 and 2):** the subject's center goes to (0.5, 0.5), left (0.3, 0.5), right (0.7, 0.5), upper (0.5, 0.3) or lower (0.5, 0.7) of the picture area, kept 4% inside every edge.
- **Outline at level 4:** always drawn, in the main color. Thick (8 px) unless the profile's outline is set to thin (4 px). The profile's Off does not apply here.
- **Extra outline at levels 2 and 3:** drawn only when the profile's outline is thin or thick, in the second preferred color, or the main color when there is only one.
- **Text below:** the page text centered in the text band at 6% of canvas height, in white or black, whichever contrasts more with the background.
- **Output:** WebP at quality 90 by default; PNG on request for tests.
- **Speed:** 150 ms or less per page on the server.
- **`RENDER_VERSION`:** a string that Owner B changes whenever output pixels would change. It is frozen at hour 30.

**Checks: `run_checks`**

| Check | Method | Result |
| --- | --- | --- |
| `fidelity` | Measure the mask | Fail unless the mask covers 0.1% to 60% of the page, and stray specks (pieces smaller than 0.1% of the page) hold no more than 10% of it. Several whole pieces pass, and the detail says how many |
| `page_edge` | Does the mask touch any edge of the page? | Warn if it does: the artwork may cut the object off |
| `background` | Canny edge detection on the render, counted outside the subject grown by 6 px, and outside the text band | Levels 1 and 2: fail above 0.5% of that area. Level 3: fail above half the original page's value. Level 4: not checked |
| `contrast` | Contrast ratio between a 6 px band inside the subject's edge and the background next to it | Warn below 3 to 1 |
| `size` | Levels 1 and 2: how far the subject is enlarged from the master. Levels 3 and 4: the subject's longer side against the page's | Warn above 2.5 times enlargement, or below 15% of the page |
| `text_contrast` | Text color against the background, when text is shown | Fail below 4.5 to 1 |

- Each check returns `status`, a measured `value` and a plain-language `detail`. No check raises an error.
- A unit test proves source fidelity by construction: at level 2, every output pixel inside the mask core equals a resampled master pixel.

**Second look: `second_look`**

- Renders the subject at level 2 on black and asks the model to name the object in one to three words, with no label and no original.
- Passes when the answer shares a word with the label or any synonym, after lowercasing and making words singular. So "bird" passes for a hornbill whose synonyms include "bird."
- A miss is a warning that shows the model's answer. It never blocks approval.
- By default it uses the same Gemini model as subject choosing, so its errors can match the first pass. `SECOND_LOOK_MODEL` can point it at another model if the team has a second key.

**Evaluation (P1)**

`make eval` runs the hand-labeled 20-page set through the pipeline and checks, and writes counts, not percentages, to `eval/summary.json`. The test pages and the demo book are not in that set. The ChatGPT comparison is not automated: Owner B runs it once by hand for a slide.

## Implementation: API and data (Owner C)

The API is the only part that touches the database, and it owns every rule about state: page states, hashes, approvals, and what the reader may show. It calls the pipeline and display functions exactly as Contract 2 defines them.

**Collections**

| Collection | Key fields |
| --- | --- |
| `books` | `title`, `credits` {author, illustrator, publisher, source, license}, `state` (ingesting, ready, failed), `page_count`, `created_at` |
| `pages` | `book_id`, `number`, `image_path`, `view_path`, `text`, `flags`, `state`, `reason`, `page_kind`, `candidates[]`, `selected`, `subject_hash`, `confirmed`, `omitted`, `processing_started_at`, `second_look` {subject\_hash, status, answer} |
| `profiles` | `name`, `level`, `settings`, `settings_hash`, `contrast_override_note` |
| `checks` | `page_id`, `subject_hash`, `settings_hash`, `level`, `render_version`, `result` |
| `approvals` | `page_id`, `profile_id`, `subject_hash`, `settings_hash`, `level`, `render_version`, `decision` (approve, reject), `at`, and `copied_from` on records the re-approve tool wrote |
| `eval_runs` (P1) | `dataset`, `n`, `counts`, `ran_at` |

**Approval rules**

- A version is approved for a child when the newest `approvals` record matching the page, the profile and all four version values says approve.
- `settings_hash` is recomputed on every profile save. Changing the name, the level or the contrast note leaves it unchanged. Level is its own key.
- `subject_hash` is set whenever the selected candidate changes. Candidates are only ever added, so reselecting an earlier one restores its hash.
- Nothing is deleted when settings, subject or `RENDER_VERSION` change. Old approvals simply stop matching, and match again if the teacher switches back.
- `POST /books/{id}/approve` compares each version sent with the current one. Pages that differ are returned in a 409 and not recorded, so the teacher only ever approves what the sheet showed.

**Reader enforcement**

- `GET /reader/page/...` recomputes the current token, compares it with `v`, checks the approval, and returns 403 on any mismatch.
- Every image response carries `Cache-Control: no-store`, so a browser can never show a picture whose approval has since lapsed.
- A test covers three cases: approved, never approved, and approved then changed.

**Processing jobs**

1. `POST /books` checks the page count and file size, saves the PDF, creates the book as `ingesting`, and returns.
2. A background task runs `rasterize`, creates page records in Processing with `processing_started_at`, and marks the book ready.
3. It then runs `process_page` in a thread pool, `PAGE_CONCURRENCY` pages at a time (default 4, lowered if Gemini rate limits appear).
4. Each result is written to its page as it lands. A failed page is marked Failed with its reason and does not stop the others.
5. On startup, any book still `ingesting` and any page still Processing is marked Failed with the reason "interrupted, retry." Jobs run inside the server process, so this is what stops a restart from stranding them.
6. `POST /pages/{id}/retry` puts one page back in the queue.
7. The web app polls `GET /books/{id}` every 2 seconds while anything is in progress.

**Checks and second look**

- Confirming a subject starts `second_look` in the background, once per page and `subject_hash`. The result is stored on the page; until it lands, the sheet shows it as pending.
- The sheet route runs `run_checks` for any page without a stored result for the current version. It is local image work of a few milliseconds per page, with no AI call, so a GET never spends the Gemini key.

**Other rules**

- `POST /pages/{id}/subject` routes to `segment_at_point`, `mask_from_outline` or `refine_mask` by the shape of the body, appends the new candidate and selects it. `tidy` is passed to `mask_from_outline` and is off unless the body sets it, so an outline is used exactly as drawn by default. `{candidates}` joins the chosen masks into one new mask file in the API, with no pipeline call.
- Renders are cached in memory, up to 256 images, keyed by page and version token.
- `python -m api.tools.reapprove <book_id> <old_render_version>` copies a named book's approvals to the current `RENDER_VERSION`. For each page, child and level it copies the newest decision, leaves alone any decision already made under the current version, and marks each copy with `copied_from`. It is a developer tool for the backup books only, run after someone has looked at the sheets again, and it prints every record it writes.

## Implementation: web app (Owner D)

The web app is a React single-page app that talks only to Contract 1. Until the first checkpoint it runs entirely on mocked responses, so no screen waits on the backend.

| Screen | Route | What it does | Priority |
| --- | --- | --- | --- |
| Library | `/` | Upload a PDF with its credits, list books, show per-page states with a progress count | P0 |
| Subject review | `/books/:id/subjects` | Grid of pages with the overlay image, label and confidence; Confirm, Confirm all, Leave out, Retry, Process anyway | P0 |
| Subject editor | `/pages/:id` | Click a candidate, or click the object, to pick it | P0 |
| Subject editor: outline | Same | Type a label, draw a freehand outline on a canvas over the page, send the points | P0 |
| Subject editor: refine | Same | Click a missing part to add it | P1 |
| Profiles | `/profiles` | Create and edit a child; live preview of one sample page; contrast warning with override note | P0 |
| Contact sheet | `/books/:id/approve` | Pick child and level; grid of previews with check results; Approve sheet, reject single pages | P0 |
| Reader | `/read/:bookId` | Full screen, one approved page, no visible controls | P0 |
| Credits | End of reader | Title, author, illustrator, publisher, source, license, adaptation note | P0 |
| Results | `/results` | Evaluation counts | P1 |

**Rules**

- All server calls go through one typed client, `web/src/api.ts`, written to match the Contract 1 table. Swapping mocks for the real API is one setting, `VITE_API_URL`.
- Mock data lives in `web/src/mocks/` and starts with placeholder images, switching to the real test pages when they land.
- The app shows level names (Tinted, Cut-out, Faded page, Outlined) and sends the numbers 1 to 4.
- **Profiles:** the live preview calls `POST /preview` with the unsaved settings, at most once every 300 ms. Nothing is saved until the teacher presses Save, so trying colors never disturbs approvals.
- **Contact sheet:** Approve sends back the version of every page exactly as the sheet received it. On a 409, the sheet reloads the changed pages and tells the teacher to look again.
- **Outline drawing:** record pointer positions, thin them to at most 200 points, convert from screen positions to 0 to 1 fractions of the page, and close the shape.
- Platform is a web app in a desktop or laptop browser only. There is no tablet or touch target, so no touch-gesture handling is needed.

**Reader**

- Images come only from `/reader/page/...` with the token from `GET /reader/...`.
- The reader prefetches the next page, and the current page in every other approved version, and holds them in memory. That is what keeps a switch under a second on venue Wi-Fi.
- Single clicks on the page do nothing, so a child cannot operate it.
- Keyboard: arrow keys or space turn the page; T opens the teacher bar; B shows the blank screen (P1).
- The teacher bar lists only fully approved child and level versions. Others are greyed out with "not approved." Approving one means leaving the reader.
- No timers, no transitions, no auto-advance.

## Work split

All four owners can start now. The rule that makes this possible: **you make your own fakes.** Whoever consumes something writes the stand-in for it, and swaps in the real thing whenever it lands. Nobody waits for a kickoff, for test pages, or for another owner's stub.

| Owner | Folders | Fake inputs they make for themselves |
| --- | --- | --- |
| A: Pipeline and infrastructure | `pipeline/`, `fixtures/`, `infra/`, root `Dockerfile`, `compose.yaml`, `Caddyfile` | None needed: works from the real PDF and the Gemini key |
| B: Display, checks and pitch | `render/`, `checks/`, `eval/`, `pitch/` | Two page screenshots and two masks painted by hand in any image editor |
| C: API and data | `api/`, `contracts/` setup | Stubs for A's and B's functions: fixed candidates, a rectangle mask, a render that returns the page unchanged |
| D: Web app | `web/` | Mock API responses typed from the Contract 1 table, with placeholder images |

In each list below, "Needs" names the only thing a task waits for. Tasks marked Nothing can start this minute.

**Owner A: pipeline and infrastructure**

| # | Task | Needs | Done when |
| --- | --- | --- | --- |
| A1 | Rasterize the book to master and working-copy PNGs; commit six test pages to `fixtures/` | Nothing | Six pages are on `main` |
| A2 | One Gemini call per page that returns page kind and candidates as JSON. Note the model name, box format, and whether four calls at once hit a rate limit | Nothing | JSON for three pages is saved |
| A3 | Segmenter trial: EdgeSAM on CPU with hand-typed boxes on three pages. Choose EdgeSAM or SAM 2 | Nothing | Three mask PNGs and a decision |
| A4 | Request GPU access. Bring up the Vultr server with Caddy, HTTPS and the site password, serving a placeholder page | Nothing | The URL asks for a password |
| A5 | `process_page`: join A2 and A3, apply the state rules, never raise | A2, A3 | Six test pages each return a state |
| A6 | `segment_at_point` and raw `mask_from_outline` | A3 | A click returns a mask; a polygon returns a mask with the segmenter switched off |
| A7 | `Dockerfile` and Compose that build and run the API | C1; until then, keep the placeholder page | `main` deploys with one command |
| A8 | Failure handling; tune state rules on test pages; process five backup books | C6; until then, run the pipeline from a script | Five books are ready on the server |

**Owner B: display, checks and pitch**

| # | Task | Needs | Done when |
| --- | --- | --- | --- |
| B1 | Make your own inputs: screenshot two book pages and paint a white-on-black mask for each | Nothing | Two pages and two masks in `render/samples/` |
| B2 | `render` at levels 2 and 1, run as a script on B1's files | B1 | Two images that look right |
| B3 | Levels 3 and 4, `overlay`, WebP output | B2 | All four levels for both sample pages |
| B4 | Send the TVI email with the four level images from B3 | B3 | Sent |
| B5 | `run_checks`: fidelity, page edge, background, contrast, size | B1 | Checks pass on good masks and fail on a deliberately bad one |
| B6 | `second_look` | A Gemini key | Names the subject on both sample pages |
| B7 | Swap in A's real pages and masks; fix what breaks | A1, A3; until then, B1's files | All six test pages render at all four levels |
| B8 | Demo script and slides | Nothing | A first run-through at checkpoint 2 |

**Owner C: API and data**

| # | Task | Needs | Done when |
| --- | --- | --- | --- |
| C1 | Create the repo and folder layout. Copy `contracts/types.py` and `hashing.py` from this document. Add one requirements file per Python folder | Nothing | Pushed. The others move their folders in when it exists; until then they work in a local folder of the same name |
| C2 | Write stubs for A's and B's functions | C1 | The stubs return valid contract types |
| C3 | Database cluster. Upload, background job, page states, book and page routes, running on the stubs | C2 | Uploading a PDF shows pages moving to Ready |
| C4 | Subject routes for candidate, point and outline; confirm, omit, retry; startup recovery | C3 | A killed server restarts with no page stuck in Processing |
| C5 | Profiles, settings hash, preview and render routes | C3 | Changing a color and changing it back gives the same hash |
| C6 | Sheet, approve with versions and the 409, reader routes with token and 403 | C5 | Tests pass for approved, never approved, and approved then changed |
| C7 | Switch the stubs to the real pipeline and render, one setting each | A5, A6, B3; until then, the stubs | A real book flows end to end |

**Owner D: web app**

| # | Task | Needs | Done when |
| --- | --- | --- | --- |
| D1 | Scaffold the app, routes and typed client. Type your own mock responses from Contract 1, with placeholder images | Nothing | Every route in Contract 1 has a mock |
| D2 | Library and Subject review | D1 | Works on mocks |
| D3 | Subject editor: click to pick, and the outline canvas sending points as 0 to 1 fractions | D1 | An outline drawn on screen posts the right coordinates |
| D4 | Profiles with live preview and contrast warning | D1 | Works on mocks |
| D5 | Contact sheet that sends versions back and handles the 409 | D1 | Works on mocks, including a forced 409 |
| D6 | Reader: gestures, keys, teacher bar, prefetch, credits | D1 | A single click does nothing; arrow keys turn the page |
| D7 | Point each screen at the real API as C's routes land | C3 to C6; until then, the mocks | No screen uses a mock |

**When fakes get swapped for real**

These are two-person handoffs, not meetings. Each happens whenever the real piece lands, and nobody is idle before it.

| When this lands | Who swaps | What changes |
| --- | --- | --- |
| C1, the repo | A, B, D | Move local folders into the repo and import the shared types |
| A1, test pages | B, D | Replace screenshots and placeholder images |
| A3, real masks | B | Replace hand-painted masks (B7) |
| C3 to C6, real routes | D | Turn off mocks screen by screen (D7) |
| A5, A6, B3, real functions | C | Turn off stubs (C7) |

**Pick-up queue for whoever finishes early**

People work at different speeds, so P1 is not pre-assigned by time. When your numbered tasks are done, take the next item below that touches your own folders. If none does, pair with whichever owner is furthest behind.

| P1 feature | A | B | C | D |
| --- | --- | --- | --- | --- |
| Tidy hand-drawn outlines | `tidy=True` path | None | Pass the flag | None |
| Click to refine | `refine_mask` | None | `{refine_point}` body | Click handling in the editor |
| Size and position | None | Scaling and placement in `render` | None; fields already stored | Two controls in Profiles |
| Text below the picture | None | Text band, `text_contrast` | None | One control in Profiles |
| Edge contrast warning | None | `contrast` check | None; note already stored | Warning and override note |
| Blank screen between pages | None | None | None | Reader option |
| Results | None | Hand labels for 20 pages, `make eval` | `/eval/summary` | Results screen |

**Rules that keep the lanes apart**

1. One owner per folder. Nobody edits another owner's folder; ask the owner.
2. The contracts in this document are frozen now. A change needs all four to agree and may only add fields.
3. You make your own fakes. The person who needs a stub, a mock or a sample file writes it, and never waits for the person who will supply the real one.
4. Each Python folder has its own `requirements.txt`. Adding a package means editing your own file; A's `Dockerfile` installs all of them.
5. Everyone commits to `main` in small steps, inside their own folders only. With no shared files to edit there are no merge conflicts.
6. `main` must always start. A broken module falls back to its stub by one setting, so one lane's bug never blocks another.
7. Each folder has its own tests. A task is done when its "Done when" is true, not when it looks finished.
8. `RENDER_VERSION` is frozen at hour 30. A change after that voids every approval, including the backup books.
9. Part 1 settles questions about behavior. The contracts settle questions about interfaces.

```text
mirai/
  contracts/    types.py, hashing.py                       set up by C, frozen
  Dockerfile  compose.yaml  Caddyfile  infra/              Owner A
  fixtures/   pipeline/                                    Owner A
  render/  checks/  eval/  pitch/                          Owner B
  api/          including api/stubs.py                     Owner C
  web/          including web/src/mocks/                   Owner D
```

## Checkpoints

There is no kickoff gate. The whole team meets only to run the demo script together, three times.

| Hours | Checkpoint | A | B | C | D |
| --- | --- | --- | --- | --- | --- |
| Now | Start, each alone | A1 to A4 | B1 to B4 | C1 to C3 | D1 to D3 |
| 12 | 1: one book flows, including a one-click fix and a hand-drawn outline | A5, A6, A7 done | B3, B7 done | C4 done; C7 for the pipeline | D2, D3 on the real API |
| 22 | 2: all of P0 | A8 done | B5, B6 done; first run of the demo script | C5, C6 done; C7 complete | D4, D5, D6, D7 done |
| 30 | 3: P1 freeze; `RENDER_VERSION` frozen | Queue items | Queue items; slides drafted | Queue items | Queue items |
| 30 to 36 | Freeze | Backup books approved and checked on the live server | Three rehearsals, backup video | Bug fixes only | Bug fixes only |

- At each checkpoint the team runs the demo script from Part 1 together and writes down what broke.
- If a lane is more than about three hours behind at a checkpoint, the owner who is furthest ahead pairs with that owner until the next one.
- At checkpoint 3, any P1 feature that does not work end to end is cut, not carried.

## Setup, deploy and early decisions

One server runs everything, behind a password, and a few settings switch each module between its stub and its real code.

**Settings**

| Setting | Used by | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | A, B | Subject choosing and the second look |
| `SECOND_LOOK_MODEL` | B | Optional different model for the second look |
| `SEGMENTER` | A | `edgesam`, `sam2` or `stub` |
| `PIPELINE`, `RENDER` | C | `real` or `stub`, so a broken module can be bypassed |
| `PAGE_CONCURRENCY` | C | Pages processed at once; default 4 |
| `MONGODB_URI`, `DATA_DIR` | C | Database and image folder |
| `SITE_USER`, `SITE_PASSWORD` | A | Caddy basic auth for the whole site |
| `VITE_API_URL` | D | Empty for mocks, or the server address |

Secrets live in `.env`, which is never committed; `.env.example` lists the names.

**Deploy (Owner A)**

- Start on a Vultr CPU instance with 4 vCPUs and 8 GB of memory.
- Docker Compose runs two containers: the API, and Caddy, which serves the built web app, forwards `/api` to the API, and handles HTTPS for the domain.
- Caddy asks for a username and password on every path. Without it, anyone with the URL could upload PDFs and spend the Gemini key.
- The API enforces the 30-page and 50 MB upload limits itself.
- `data/` is a mounted folder, so pre-processed books survive a restart.
- A redeploys from `main` at every checkpoint.

**Decisions to make early**

| Decision | Owner | By | How to decide |
| --- | --- | --- | --- |
| TVI review | B | Tonight | Send mock-ups of the four levels. With no reply by judging, the pitch says "not yet reviewed by a TVI" |
| Gemini model name, box format and rate limit | A | Hour 2 | One test call on a page, then four pages at once to see whether the limit holds |
| GPU access on Vultr | A | Hour 0 | Request it at the start even if CPU turns out to be enough; approval can take time |
| Segmenter | A | Hour 4 | Run EdgeSAM on CPU on three test pages. If it loses legs, thin lines or small animals, move to SAM 2 small on the GPU |
| Demo book and its hard page | B | Checkpoint 1 | *Animal Homes* names two animals on most pages, so most would need a pick. Confirm it still works for the demo or choose a book with one subject per page |
| State rules and thresholds | A | Checkpoint 2 | Tune on the six test pages only |

**Demo safety**

- Five books are processed, confirmed and approved in advance. They load with no model calls.
- If Gemini or the segmenter is down, the hand-drawn outline still produces a page. It is P0 and calls no model.
- `RENDER_VERSION` is frozen at hour 30. If it must change, A runs the re-approve tool on the backup books after checking their sheets.
- A screen recording of the full demo is ready before judging starts.
