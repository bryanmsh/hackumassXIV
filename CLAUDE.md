# Mirai

Mirai is a web app that adapts picture-book pages for children with cortical
visual impairment (CVI). A teacher uploads a PDF, the app finds the subject of
each page and cuts it out of the original artwork, and each child sees the page
in a look set by their profile. A teacher approves every page before a child
sees it.

Built at HackUMass in 24 hours by four people.

## Read these first

Two documents in the repo root hold everything. Read the relevant part before
writing code; do not guess at behavior or interfaces.

| File                            | What it is                                                                                                                                                                                                                      | Read it when                                                                                |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `Product and technical spec.md` | Part 1: product requirements (priorities, page states, child profiles, checks, approval, reader). Part 2: technical requirements (architecture, tech stack, the three contracts, implementation per module, data model, setup). | You need to know what something should do, or the exact shape of a route, function or file. |
| `Mirai 24-Hour Build Plan.md`   | Who owns what, the hour-by-hour outline, each person's task list for the MVP and Phase 2, who works together when, checkpoints, and what to cut if behind.                                                                      | You need to know what to build next, who owns it, or whether it is in scope right now.      |

If the two disagree: the spec wins on behavior and interfaces, the build plan
wins on schedule, ownership and scope.

## Who owns what

Ask which person you are working with if it is not obvious, and only edit that
person's folders. Never edit another owner's folder; say what is needed and let
them change it.

| Person | Owns                      | Folders                                                                       |
| ------ | ------------------------- | ----------------------------------------------------------------------------- |
| Bryan  | Pipeline and server       | `pipeline/`, `fixtures/`, `infra/`, `Dockerfile`, `compose.yaml`, `Caddyfile` |
| Kevin  | Display, checks and pitch | `render/`, `checks/`, `eval/`, `pitch/`, `tests/`                             |
| Andrew | API and data              | `api/`, `contracts/`                                                          |
| Thomas | Web app                   | `web/`                                                                        |

The spec calls these lanes A, B, C and D in that order.

## Tech stack

- Web app: React 18, Vite, TypeScript, Tailwind CSS
- API: Python 3.11, FastAPI, Pydantic v2, PyMongo
- PDF: PyMuPDF
- Subject choosing: Gemini API with JSON output
- Cut-outs: EdgeSAM on CPU, or SAM 2 small
- Image display: NumPy, OpenCV, Pillow, WebP output
- Database: MongoDB Atlas. Images live on disk, not in the database
- Hosting: one Vultr instance, Docker Compose, Caddy

Each Python folder has its own `requirements.txt`. Add packages there, not in a
shared file.

## Rules that must hold

- **Contracts are frozen.** The HTTP API, the Python function signatures and
  the image file formats are defined in Part 2 of the spec. Changes need all
  four people and may only add fields.
- **Positions in the API are fractions from 0 to 1** of the page's width and
  height, from the top-left corner. The API converts to master pixels in one
  place before calling the pipeline. Masks are the size of the 3,000 px master.
- **Never generate or redraw artwork.** The subject is always copied from the
  original page through a mask. Tinting, resizing and outlines are display
  changes on top.
- **The reader shows approved versions only.** An approval is tied to one page,
  one cut-out, one set of profile settings and one look. If any of those
  change, the page needs approval again.
- **Automatic checks are not approval.** Never label a page "verified." Checks
  say the adaptation was built correctly; only the teacher approves it.
- **Make your own fakes.** If you need another module that is not ready, write
  a stand-in in your own folder and swap in the real thing later.
- **`main` must always start.** Commit small and often, inside your own folders.

## Scope right now

- MVP is every P0 feature in the spec, due by hour 15.
- Phase 2 (P1 "good" features, then P2 "extras") starts only after the MVP
  checkpoint passes. Do not start a Phase 2 feature early, and do not add
  features that are in neither document.
- Out of scope: diagnosing CVI or recommending a look, live camera mode,
  accounts, sharing between teachers, commercial books.

## Words used in this project

- **Subject:** the one object a page is about.
- **Cut-out / mask:** the shape that selects the subject on the page.
- **Look (level):** how a page is shown. 1 Tinted, 2 Cut-out, 3 Faded page,
  4 Outlined. The app shows names; the API sends numbers.
- **Profile:** a child's display settings (look, colors, background, size,
  position, text).
- **Contact sheet:** the grid a teacher uses to approve all pages for one child
  and look.
- **Second look:** an AI pass that names the subject from the adapted page
  alone. It is a warning only.
- **TVI:** teacher of students with visual impairments, the main user.
- **Demo profiles:** Maya and Leo. Both are fictional; no real child's data is
  stored.
