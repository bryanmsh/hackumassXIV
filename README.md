# Miraai

**Picture books, adapted for children with cortical visual impairment (CVI), using only the book's own artwork, with a teacher approving every page.**

Built at HackUMass XIV in 24 hours by four people.

## Problem

Children with CVI recognize an object far better when it is shown alone, on a plain background, with strong contrast. Picture-book pages are the opposite. Today a teacher of students with visual impairments (TVI) rebuilds pages by hand, often with scissors and black card, so each child gets only a few adapted books.

## What Miraai does

1. **Upload.** The teacher uploads a PDF picture book.
2. **Find the subject, once.** For each page, an AI model reads the picture and the text together and suggests what the page is about. A segmentation model then traces each suggestion on the original page and saves it as a cut-out.
3. **Subject review.** The teacher confirms the subject, picks a different one, shows several together, clicks the object, or draws an outline by hand. The hand-drawn outline calls no AI, so it works when the AI services are down.
4. **Show it the child's way.** Each child has a profile: a look, preferred colors, background, size, position and text. The same saved cut-out is re-displayed for every child with no new AI work.
5. **Approve, then read.** The teacher approves a contact sheet per child and look. The full-screen reader shows approved pages only, at the teacher's pace.

The four looks:

| Look | What the child sees |
| --- | --- |
| Tinted | The subject alone, tinted in the child's main color, on a plain background |
| Cut-out | The subject alone, in its real colors, on a plain background |
| Faded page | The whole page, faded, with the subject kept vivid |
| Outlined | The original page, with the subject outlined in the child's main color |

## What it promises, and what it does not

- **The subject is always copied from the original page.** Nothing is drawn or invented by AI. Tinting, resizing and outlines are display changes on top.
- **A child never sees a version the teacher has not approved.** An approval is tied to one page, one cut-out, one set of profile settings and one look. Change any of them and the reader refuses the page until it is approved again. Change it back and the earlier approval returns.
- **Automatic checks are not approval.** They measure whether the adaptation was built correctly: the cut-out has no stray specks, the background is plain, the subject stands out. Only the teacher decides whether a page is right for a child.
- Miraai does not assess or diagnose CVI, and does not recommend a look.
- No child with CVI has used Miraai yet, and no TVI has reviewed it yet.

## Where AI is used

| Step | Model | Notes |
| --- | --- | --- |
| Choosing the subject | Gemini (Flash), JSON output | Up to 5 suggestions per page with a self-reported confidence. Confidence only screens out weak guesses; when a page has several subjects, the teacher chooses |
| Tracing the cut-out | SAM 2.1 small on CPU | Runs once per suggestion. OpenCV GrabCut is the fallback when PyTorch is not installed |
| Second look | Gemini | Shown only the adapted page, it names the subject. A warning only; it never blocks or grants approval |
| Display and checks | None | NumPy, OpenCV and Pillow. The same input always gives the same picture |

## Tech stack

- **Web app:** React 18, Vite, TypeScript, Tailwind CSS (`web/`)
- **API:** Python 3.11, FastAPI, Pydantic v2, PyMongo (`api/`, shared types in `contracts/`)
- **Pipeline:** PyMuPDF, Gemini API, SAM 2.1 small (`pipeline/`)
- **Display and checks:** NumPy, OpenCV, Pillow, WebP output (`render/`, `checks/`)
- **Data:** MongoDB for records; page images and masks on disk
- **Hosting:** one Vultr instance, Docker Compose, Caddy for HTTPS and the site password

The four parts meet at three contracts (the HTTP API, a handful of Python functions and the image file formats), all written down in [Product and technical spec.md](Product%20and%20technical%20spec.md).

## Run it locally

Run every command from the repo root.

```bash
# 1. Python packages: one requirements file per folder, as the Dockerfile installs them
python3.11 -m venv .venv
for f in */requirements.txt; do .venv/bin/pip install -r "$f"; done

# 2. A local database
docker run -d --name mirai-mongo -p 127.0.0.1:27017:27017 mongo:7

# 3. Settings
cp .env.example .env
#    In .env set:  MONGODB_URI=mongodb://localhost:27017/mirai
#    For the real pipeline also set:  GEMINI_API_KEY=...  PIPELINE=real  RENDER=real
#    Leave PIPELINE=stub and RENDER=stub to run with stand-ins and no AI calls.

# 4. The API, on port 8000
.venv/bin/uvicorn api.main:app --env-file .env

# 5. The web app, in a second terminal
cd web && npm install
npm run dev                                                           # mock data, no API needed
VITE_API_URL=/ API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev     # against the local API
```

Run only one API process per database. On startup the API marks every page still processing as failed ("interrupted, retry"), so a second server pointed at the same database interrupts the first one's work.

To process a book with no API and no database: `.venv/bin/python -m pipeline.run_book fixtures/animal-homes-pratham-FKB.pdf data/books/animal-homes`. This calls Gemini once per page.

Deploying to the server is covered in [infra/DEPLOY.md](infra/DEPLOY.md).

## Tests

```bash
.venv/bin/python -m pytest api contracts tests -q    # API, contracts, reader over HTTP; needs MongoDB running
.venv/bin/python -m pytest pipeline render checks -q # offline; Gemini is mocked
cd web && npm test
```

On Nov 14, 2026 these ran 212, 219 and 178 tests, all passing. The reader tests cover the promise above: an approved page is served, a never-approved page is refused, and a page approved and then changed (profile, subject, left out, rejected or a new render version) is refused until it is approved again.

## Measured so far

- A 5-page book (*Animal Homes*) processes in about 30 seconds on a laptop with the real Gemini calls, 4 pages at a time, using GrabCut cut-outs.
- One Gemini subject call takes 7.6 to 12.9 seconds and about 1,500 input tokens.
- Switching child or look needs no AI call; it re-displays the saved cut-out.

**Evaluation is not run yet.** The plan is a set of 20 StoryWeaver pages, hand-labeled before any AI output is seen and never used for tuning, reported as counts: correct subjects, correctly flagged pages, confidently wrong pages and cut-out defects.

## Data and attribution

- Demo book: *Animal Homes*, published by Pratham Books on StoryWeaver, CC BY 4.0. Miraai keeps each book's credits and license on a credits screen at the end of the reader, with a note that the pages were adapted.
- Text font: Atkinson Hyperlegible, SIL Open Font License (`render/fonts/OFL.txt`).
- The demo children, Maya and Leo, are fictional. No real child's data is stored.
- Book pages are sent to an outside AI service (Gemini) to find the subject. The upload screen says so.

## Team

| Person | Part | Folders |
| --- | --- | --- |
| Bryan | Pipeline and server | `pipeline/`, `fixtures/`, `infra/`, `Dockerfile`, `compose.yaml`, `Caddyfile` |
| Kevin | Display, checks and pitch | `render/`, `checks/`, `eval/`, `pitch/`, `tests/` |
| Andrew | API and data | `api/`, `contracts/` |
| Thomas | Web app | `web/` |
