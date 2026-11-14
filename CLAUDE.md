# Mirai — Claude Code Repository Instructions (Person D / Frontend)

> **Mission:** Build and integrate Mirai's complete teacher-facing React application within a 24-hour hackathon. You are Thomas's frontend coding partner, not the backend, AI-pipeline, or rendering owner. **Deliver working code in `web/`, not plans or nonfunctional mockups.**
>
> **Current plan:** `Mirai 24-Hour Build Plan-FINAL.md` (November 14, 2026). Ignore older build plans when they disagree.

## 1. Read these sources first

Before making changes, read the project documents, if available in the workspace:

1. **`Mirai 24-Hour Build Plan-FINAL.md`** — authoritative for who owns what, time blocks, checkpoints, integration order, MVP/P1/P2 scope, and the **normalized HTTP coordinate decision**.
2. **`Product and technical spec.md`** — authoritative for product behavior, P0 requirements, frozen API routes, Python contracts, rendering semantics, approvals, reader guarantees, and acceptance criteria.
3. Existing implementation and **the example API request/response file agreed by Andrew and Thomas** — authoritative for actual JSON field names, nesting, error bodies, and image URL access, provided they comply with the contracts.

**Conflict resolution:** The FINAL plan supersedes the spec's outdated 36-hour timeline, previous coordinate assumption for the *HTTP boundary*, and earlier integration order. The spec remains authoritative for all other technical requirements. In particular, **the browser exchanges coordinates normalized to 0–1; Andrew's API converts them once to master-image pixels before calling Bryan's pipeline**. The Python function and stored-mask contracts remain in master pixels. Do not conflate these layers.

If a document is missing, use what is available, identify the missing authority, and do not invent absent contract fields. If a live agreed fixture conflicts with the frozen API, flag it for Andrew and the team rather than silently changing a route or contract. Only additive changes, agreed by all four owners, are allowed.

## 2. What we're building

Mirai adapts PDF picture-book pages for children with cortical visual impairment (CVI). The AI suggests the principal object, the subject is cut out **from the book's original artwork**, and a teacher confirms/corrects it. The teacher creates child-specific display profiles, reviews technical checks, approves *specific versions*, and uses a distraction-free, teacher-controlled reader.

The product **never** promises that a particular child can see or understand an image, never diagnoses CVI, never recommends a CVI phase, and never treats AI confidence or automated checks as clinical verification. The four display looks are presentation modes, **not clinical stages or an easier-to-harder ladder**.

### Four promises that can never be cut

1. Preserve original artwork; do not invent/repaint missing content.
2. Support two child profiles on the same processed book with no new inference for display changes.
3. Require teacher subject review and explicit version-specific approval before reading.
4. **Never display an unapproved version in the reader**; the server enforces this, including on subsequent profile, subject, or render changes.

**MVP = all P0 requirements, done by hour 15.** No Phase 2 work starts until checkpoint 2 has passed. The final four hours are for reliability and submission, not features.

## 3. Team boundaries — stay inside `web/`

| Person | Lane | Owns |
|---|---|---|
| Bryan (A) | PDF ingestion, subject selection, masks, server/deployment | `pipeline/`, `fixtures/`, `infra/`, `Dockerfile`, `compose.yaml`, `Caddyfile` |
| Kevin (B) | Rendered looks, checks, evaluation, slides and API-level reader tests | `render/`, `checks/`, `eval/`, `pitch/`, `tests/` |
| Andrew (C) | FastAPI, MongoDB, state, profiles, approvals, reader authorization, shared contracts, demo reset | `api/`, `contracts/` |
| **Thomas (D)** | **Every teacher-facing screen, interactions, React app, frontend mocks/tests** | **`web/`** |

- Only modify files under `web/` unless Thomas explicitly authorizes an exception. This root `CLAUDE.md` is an instruction file, not permission to edit other owners' code.
- All web-to-server calls go through **Contract 1** and the typed **`web/src/api.ts`** client. No direct database, Gemini, mask manipulation, image compositing, backend hash generation, or bypasses.
- Need a backend field/route change? Supply an exact, short message to **Andrew**, with request/response examples, and continue with a clearly marked mock while waiting. Need renderer functionality? Coordinate with **Kevin**. Need segmentation or outline fixes? Coordinate with **Bryan**.
- Contracts are frozen; only additive changes unanimously agreed by the team. Do not rename paths, remove fields, or change semantics on your own.
- Commit small changes to `main` within owned paths; check `git status` and diff before committing. Never force-push or overwrite another person's changes. `main` must remain runnable.

## 4. First ten minutes and first 30 minutes

**First ten minutes — team decisions (do not skip):**

1. Andrew creates and shares the repository in the first five minutes.
2. Everyone agrees that **HTTP positions (boxes, points, outline vertices) use fractions 0–1**, measured from the original page's top-left, with `x` across width and `y` down height. Andrew converts to master pixels in exactly one backend location.
3. Kevin confirms the actual hacking deadline, submission closing time, and judging format; if hour 24 is presentation rather than hacking end, the schedule moves earlier.
4. Kevin selects a *named* teacher to receive the TVI feedback email.

**Hour 0 collaboration:** Thomas and Andrew spend 30 minutes agreeing **one request/response example per Contract 1 route** in a shared file; include error responses and normalized coordinate shapes. Find the actual demo tablet now. If Andrew has not yet supplied samples, create **proposed mock fixtures** inside `web/`, explicitly marked provisional; do not claim they are an agreed backend contract.

Resolve in the samples, before building interactions:

- Book IDs/page IDs; nested book/page/candidate/profile/sheet/reader objects and state enums.
- `candidate` selection semantics (index versus ID) and its exact JSON representation.
- Normalized box ordering (`x0,y0,x1,y1`), point encoding, polygon encoding, and any refine-point body.
- The server-supplied **original-page image URL**, overlay URL, and image dimensions/aspect ratio needed by the editor (these are not all fully specified by Contract 1).
- Image auth and fetch behavior on the live, password-protected site.
- Upload `credits` serialization, optional book-title behavior, status polling shapes.
- Approval sheet's page/version token fields and the exact 409 changed-page payload.
- Reader manifest's approved page URLs, skipped pages, available versions, and credits.

Do not expose server filesystem paths as public image URLs or silently create new endpoints. Propose additive fields through Andrew when the frozen table is insufficient.

## 5. Operating mode for Claude

**Execute, don't just advise.** When you have repository access, inspect actual files, implement code, run available checks, and correct failures. Do not stop after a plan or generate giant unintegrated code samples.

At the beginning of each coding session:

1. Inspect current repository status, `web/` structure, package scripts, tests, environment configuration, and already implemented components. Preserve working code.
2. Read the two governing documents and any agreed API examples in the repo.
3. Determine the **current completed milestone and actual elapsed hackathon hour** from user/context. Do not assume a time or mark a checkpoint passed without evidence. If the time is unknown, advance the earliest incomplete P0 milestone; never silently start Phase 2.
4. Identify the next **smallest end-to-end vertical slice** that meets a milestone's “done when.”
5. Implement it within `web/`, verify what can actually be verified, and report results accurately.

While coding:

- Prefer a complete working slice over perfect architecture or superficial styling.
- Keep loading, empty, failure, retry, and success states functional; no dead buttons.
- Do not replace working implementations just for neatness. No sweeping rewrites.
- No fabricated API data in the **real** mode; mock mode must be unmistakable in development.
- Do not change dependencies, install packages, run destructive commands, or commit outside owned paths without need and clear understanding.
- If a tool is unavailable, say exactly what was not tested. Never claim success without execution or direct verification.
- Do not block progress on another lane: use your own deterministic mocks, then swap to real endpoints as they land.
- Keep progress explanations short: **implemented / files changed / checks run / blockers / next milestone**.

## 6. Stack and frontend architecture

Use the product spec's stack:

- React 18, Vite, TypeScript (strict), Tailwind CSS.
- React Router for SPA navigation.
- Mock Service Worker (MSW) + realistic stateful JSON fixtures for independent frontend development.
- One typed API client: **`web/src/api.ts`**. Native `fetch` is sufficient; avoid unnecessary framework dependencies.
- Atkinson Hyperlegible when available, with a readable bundled/system sans-serif fallback.
- For frontend tests, prefer Vitest + React Testing Library; add lightweight browser-level tests for gestures/coordinates if the setup supports them.

Suggested structure (adapt to existing files; don't reorganize for its own sake):

```text
web/
  package.json
  .env.example
  src/
    main.tsx
    App.tsx
    api.ts
    types/
    pages/
      LibraryPage.tsx
      SubjectReviewPage.tsx
      SubjectEditorPage.tsx
      ProfilesPage.tsx
      ContactSheetPage.tsx
      ReaderPage.tsx
    components/
      ui/
      books/
      subjects/
      profiles/
      approval/
      reader/
    hooks/
    utils/
      coordinates.ts
      contrast.ts
    mocks/
      browser.ts
      handlers.ts
      fixtures/
    tests/
    styles/
```

### API mode, staging, and deployment

- The single central API base setting is **`VITE_API_URL`**. During local mock-first development, its empty value can enable MSW; a configured server URL selects the real stand-in/live API. **Never enable MSW in a production build.** For Caddy deployment, use the same-origin `/api` proxy; an empty base URL in production means same-origin API, not mock mode.
- Route construction happens in `api.ts` only, with exactly one `/api` prefix. Support deployment base URLs without producing `/api/api`.
- Real mode should be in place by **hour 3**, while Andrew's live backend still uses stand-in pipeline/display data. Keep mocks available as a development fallback, but remove every **active** fake from the live demo by hour 14.
- Never put API keys, database credentials, site passwords, or secrets in `VITE_` variables or browser code. `.env` must not be committed; provide non-secret names in `web/.env.example`.
- Respect Caddy's site-wide Basic Auth. Handle 401/403/errors as actual server responses, not by inventing bypasses. Preserve `Cache-Control: no-store` semantics on image fetches.

### UI quality

Teacher-facing dashboard: clear, calm, professional, spacious and tablet-friendly, with large hit targets, readable labels, consistent spacing, status indicators, and accessible form semantics. Avoid flashy animations and unrelated features. The original picture-book art is the focus. Support landscape tablet and laptop without horizontal overflow.

**Reader UI is different:** deliberately minimal, full-screen, no visible controls, no flashing/transitions/auto-advance; single taps do nothing. Don't turn teacher review screens into child-facing screens.

## 7. Frozen API routes — use these exact methods and paths

All paths below are relative to the `/api` prefix; consult the technical spec and **agreed example JSON** for exact bodies and response shapes.

| Method | Route | Purpose |
|---|---|---|
| POST | `/books` | Multipart PDF upload + optional credits, returns new book immediately |
| GET | `/books` | Library listing |
| GET | `/books/{id}` | Book, credits, page states, candidates, confirmations, omissions |
| PATCH | `/books/{id}` | Edit title/credits |
| POST | `/pages/{id}/retry` | Retry; `{force}` permits Unsupported page processing |
| POST | `/pages/{id}/subject` | `{candidate}`, `{point}`, `{label,outline}`; `{refine_point}` only Phase 2 |
| POST | `/pages/{id}/confirm` | Confirm subject; second-look may run asynchronously |
| POST | `/books/{id}/confirm-all` | Bulk confirm subjects |
| POST | `/pages/{id}/omit` | `{omitted}` |
| GET | `/pages/{id}/overlay` | Original-page subject highlight image |
| GET | `/profiles` | List profiles |
| POST | `/profiles` | Create profile |
| PATCH | `/profiles/{id}` | Edit profile |
| POST | `/preview` | WebP preview of **unsaved** settings; no persistence |
| GET | `/render/{page_id}?profile=&level=&v=` | Teacher-only saved version preview; NEVER reader |
| GET | `/books/{id}/sheet?profile=&level=` | Per-page contact-sheet preview/checks/approval/version |
| POST | `/books/{id}/approve` | Exact version approval/rejection; 409 on changed pages |
| GET | `/reader/{book_id}?profile=&level=` | Authorized reading manifest, skipped pages, credits, approved versions |
| GET | `/reader/page/{page_id}?profile=&level=&v=` | Authorized image; 403 on missing/stale approval |
| GET | `/eval/summary` | P1 evaluation counts; not a P0 blocker |

API requirements:

- Full typing for published request/response shapes and fixture-derived JSON, without arbitrary `any`.
- Centralized JSON, `FormData`, query parameters, image blob handling, request cancellation, error normalization, and 403/409 handling.
- PDF enforcement: 50 MB and 30 pages on backend; frontend can prevalidate file type/size, but cannot pretend page count is verified unless actually parsed.
- Images: WebP quality 90 from server; responses have `Cache-Control: no-store`. Release object URLs when no longer needed.
- Do not generate hashes/tokens client-side. `settings_hash`, `subject_hash`, approval version `v` are produced by Andrew's backend.
- Important: status strings and settings/approval shapes must use the **actual documented/agreed representation**, never guessed labels or case changes.

## 8. Coordinates — critical FINAL-plan change

**This overrides the previous spec's HTTP-side master-pixel assumption.**

**Frontend ⇄ HTTP API:** Candidate boxes, subject click positions, freehand outline vertices, and any refine clicks are **normalized fractions in `[0, 1]`**, relative to the original page's actual image rectangle. Origin = top-left. `x` increases right; `y` increases down. Use the JSON field names and shapes agreed with Andrew.

**Andrew ⇄ Bryan Python functions:** Andrew converts normalized coordinates to pixels of the actual master page exactly once, before calling Bryan. Python's `Candidate.box`, segmenter point inputs, manual-outline points, and masks remain **master-pixel** data. Do **not** convert to master pixels in React and do **not** divide coordinates a second time.

**Editor implementation:**

1. Display the original page using a fixed-aspect-ratio image/container; know the **actual drawn image rectangle**, not just the containing card/canvas.
2. For a pointer at `(clientX, clientY)`, use the displayed image's bounding rectangle (account for `object-fit: contain`, letterboxing, responsive size and CSS transforms) to get local image coordinates.
3. Compute normalized `x = (clientX - imageLeft) / imageWidth` and `y = (clientY - imageTop) / imageHeight` from that actual image rectangle.
4. Accept points only when inside the image; clamp to `[0,1]` as defensive validation, not to hide bad rectangle math.
5. For candidate overlays, map normalized boxes back to CSS percentages within the **same actual image rectangle**; do not draw over letterboxing.
6. For freehand outline, use Pointer Events for mouse/pen/finger, capture pointers appropriately, prevent default scrolling **only on the active drawing surface**, collect points, reduce to at most 200 vertices, close the polygon, and reject degenerate outlines with fewer than three distinct points.
7. Send only normalized numbers in the agreed request shape. Wait for the backend's new candidate/overlay and visually verify alignment.

**Mandatory alignment check at hour 6:** Thomas + Andrew, Bryan on call, draw an outline on **both demo tablet and laptop**. The returned mask must be aligned with the on-screen shape. If it is not, stop and fix before proceeding. Check letterboxing, scale, page rotation, box order, and accidental double-conversion. Unit-test the mapping at different aspect ratios and window sizes.

Do not confuse Gemini's model-native `[ymin,xmin,ymax,xmax]` on a 0–1000 scale with HTTP's normalized `x/y` fractions; Bryan/Andrew handle the Gemini conversion upstream.

## 9. Required P0 screens and behaviors

### A. Library — `/`

- PDF upload, file picker (drag/drop optional), book title and credits: author, illustrator, publisher, source, license.
- Explain that uploaded pages are sent to an external AI service to identify the subject.
- Clearly state 30-page / 50-MB support; validate type/size where practical; surface backend rejection accurately.
- List books with processing progress, page counts, and per-page states: **Processing, Ready, Needs subject, No clear subject, Failed, Unsupported**. Book-level `ingesting`, `ready`, `failed` are separate.
- Poll `GET /books/{id}` **every two seconds** while processing and stop/clean up when terminal/unmounted; don't let one failed page block the other pages or freeze the UI.
- Provide useful empty/loading/error/retry states and navigation to Subject Review.

### B. Subject Review — `/books/:id/subjects`

- Grid of original-page overlays, page numbers, selected subject label, AI confidence where available, uncertainty/state, and explicit confirmed/omitted status.
- Confirm; **Confirm all** after review; choose alternate candidate; leave out/un-omit; retry failed; process Unsupported pages with `force`; enter Subject Editor.
- Do not auto-confirm AI selections or imply self-reported confidence equals correctness. Pages with multiple equally weighted candidates or scenes require teacher choice or omission.
- Refresh data after every mutation. Subject or mask changes mean dependent approved versions need re-review, as enforced by backend.

### C. Subject Editor — `/pages/:id`

- Large original page, candidate boxes/selection, selected-overlay preview, loading and failure states.
- **Choose an existing candidate** via the agreed `{candidate}` body.
- **Click object:** submit normalized `[0,1]` point via the agreed `{point}` body.
- **Manual fallback:** teacher enters a label and traces a freehand polygon with finger/mouse; normalize vertices; at most 200 points; close and validate shape; submit `{label,outline}`. This remains available when both AI and segmenter are down (backend uses the drawn shape as-is, cut from original artwork).
- Clear/redraw, cancel, and updated overlay after submission. Do not generate masks in the browser.
- **No P1 refine UI until checkpoint 2 passes**; implement separately when Bryan's and Andrew's P1 route support actually works.

### D. Child Profiles — `/profiles`

- Create/edit a child's **first name**, selected display look, **1–3 of the exact eight swatches**, and background color.
- Levels presented by **name**, with numeric API values: `1 Tinted`, `2 Cut-out`, `3 Faded page`, `4 Outlined`. Do not present them as a clinical hierarchy.
- Swatches: red `#E53935`; yellow `#FDD835`; orange `#FB8C00`; green `#43A047`; blue `#1E88E5`; purple `#AB47BC`; pink `#EC407A`; white `#FFFFFF`.
- Background choices: black, dark gray, navy, white. Obtain exact dark gray/navy hex values from the agreed API samples before persisting; the spec does not freeze those hex codes.
- Use `POST /preview` for **unsaved** settings; debounce/throttle so requests do not fire more than once in a 300 ms interval; cancel/ignore stale responses. Preview does not save or affect approvals. Save explicitly with profile endpoint.
- Contrast warning if main swatch vs background is below **3:1**; override requires a short `contrast_override_note`. Frame this as an engineering aid, not clinical assurance.
- Demo profiles are fictional: **Maya** = Tinted/red/black; **Leo** = Cut-out/yellow+blue/black. Until Phase 2 size/text land, Leo is **centered and text off**.
- The settings object must remain schema-compatible with Contract 2. If `size`, `position`, `text_mode`, or `outline` are required by the backend before UI controls exist, send **agreed defaults** without revealing Phase 2 controls prematurely.

### E. Contact Sheet / Approval — `/books/:id/approve`

- Teacher selects **child/profile and look/level**. Grid of exact adapted previews, technical checks, second-look status (`pending/pass/warn` if available), omission/rejection state, and current approval state.
- Approve a sheet or reject individual pages; allow return to Subject Review and correction.
- **Never derive a new version token on the client.** Preserve each exact `version` received from the sheet. Send `POST /books/{id}/approve` with `{profile_id, level, pages:[{page_id, version, decision}]}` where `decision` is `approve` or `reject`.
- **409 conflict:** Show **“Look again”** with affected pages, fetch updated sheet, require new human review; do not auto-approve changed versions or show false success. Handle potentially partial successful/unchanged decisions exactly as Andrew's agreed response specifies.
- Technical checks do not replace teacher approval. Display warnings honestly; don't hide failed checks.

### F. Reader — `/read/:bookId`

- Full-screen, one approved page at a time, no visible buttons, no auto-advance/transition/flash. Teacher controls pace.
- Manifest from `GET /reader/{book_id}?profile=&level=` only; image bytes **only** from `GET /reader/page/{page_id}?profile=&level=&v=` using the manifest's token. **NEVER use `/preview` or `/render` inside Reader.**
- Missing, revoked or changed approvals return **403**; do not display an image, substitute the original, reuse an unauthorized old image, or silently bypass. Show a safe teacher-directed failure/return-to-approval path.
- Omitted/rejected pages are skipped and listed to teacher; credits (title, author, illustrator, publisher, source, license, adaptation notice) are the last page.
- Single touch/click **does nothing**. On laptop: Right Arrow or Space = next; Left Arrow = previous; `T` = teacher bar. Ignore repeated/distracting inputs as necessary; clean up listeners.
- Tablet gesture choice **must be tested at hour 4 on the actual demo device** before implementing Reader: test two-finger swipe for turns and two-finger tap for teacher bar; test full-screen and ensure the browser doesn't zoom/navigate. Limit `touch-action` restrictions to Reader gesture surface. **If unreliable**, document and use the FINAL plan's fallback: **long-press in a corner** for teacher bar, and a **keyboard/clicker** for page turns. Do not ship unreliable gestures or visible child-facing buttons.
- Teacher bar: choose only **fully approved** profile+level versions; unavailable versions greyed “not approved,” with a path to exit and approve outside the Reader. Switching must never force an unapproved render.
- Fetch next approved page and current page in other approved versions ahead of time as **Blob** responses; hold in bounded in-memory cache for target **under one-second** switching on demo tablet with throttled Wi-Fi. Server says `no-store`, so do not rely on browser HTTP caching. Scope cache by profile+level+page+version; release object URLs, invalidate on version/manifest changes, revalidate authorization through backend before display where needed.
- A blank screen between pages is **P1**, not allowed before checkpoint 2 passes; `B` may be assigned for it only when shipped.

## 10. Stateful mocks — early fallback, not the demo

Use MSW in `web/src/mocks/` with TypeScript fixtures matching the **Andrew–Thomas agreed API examples**. Every Contract 1 route gets a representative response/handler in D1. Images can be clearly labeled placeholders at first. Mock actions must mutate mock state, not just trigger toast messages.

Include scenarios for: ingesting/processing books; all page states; several candidates; candidate confirmation; click/outline-generated subjects; omission/retry; profile creation/update; all four looks; preview and contrast warnings; sheet checks; approved/rejected pages; forced **409 stale approval**; forced **403 unapproved reader image**; network errors; and credits.

**Milestones:** all mocks available by hour 1, live stand-in API powering Library + Subject Review by end of hour 3, and **no active mocks anywhere in live application by hour 14**. Keep mocks for isolated tests and offline development, not as a fallback that lies about real demo success.

## 11. Hour-by-hour task order — FINAL plan, not older plans

| Hour | Thomas's work | Done when |
|---|---|---|
| **0** | Find demo tablet. Pair with Andrew for 30 min to agree example request/response for every route, including normalized coordinates. Confirm repo link. | Examples agreed; tablet in hand. |
| **1** | **D1** Scaffold app, routes, typed `api.ts`, MSW handlers, placeholder images and basic layout. | Every Contract 1 route has a mock; app starts. |
| **2** | **D2** Library: upload+credits, list, states and 2-second polling. | Works against mocks. |
| **3** | **D2** Subject Review: grid, overlay, confirm/all, omit, retry. Then pair with Andrew for 15 min and set API base to the **live stand-in server**. | Library and Subject Review work against the actual live API. |
| **4** | Spend first 10 min proving tablet gesture method/fallback. Then **D3** candidate and click-to-pick using **normalized positions**. | Device control choice documented; correct 0–1 point sent. |
| **5** | **D3** manual label + freehand outline, <=200 points, closed polygon, normalized. | Outline request is correct. |
| **6** | Pair with Andrew; Bryan on call. Check returned cut-out/outline alignment on **tablet and laptop**; fix offsets. | Polygon and mask line up on both devices. |
| **7** | Exercise real page states/candidates as Bryan's real pipeline joins Andrew's API. | Checkpoint 1 workflow runs on screen. |
| **8** | **Checkpoint 1:** demonstrate upload, state progression, click correction, outline correction, all four looks on live site; then begin profiles only after checkpoint. | One book flows end to end. |
| **8–9** | **D4** Profiles, explicit Save, named looks, swatches, backgrounds, unsaved preview, 3:1 warning+override. | Exploring colors never changes saved approvals. |
| **10–11** | **D5** Contact Sheet; exact version echo, approve/reject, warning results, forced 409 “look again.” | Correct approvals; conflict handled. |
| **12** | **D6** Full-screen Reader: actual chosen tablet controls and arrow keys; single touch does nothing. | One approved page at a time; input behaves safely. |
| **13** | **D6** teacher bar, fully-approved-version switching, Blob prefetch and in-memory cache, skipped-page notices, credits. | Fast switch on throttled network; only approved images shown. |
| **14** | **D7** last Andrew integration and errors; remove all active mocks. Coordinate demo-reset readiness (Andrew owns reset script). | Complete MVP works end-to-end with real API, no live fakes. |
| **15** | **Checkpoint 2:** Andrew resets demo book; full run on tablet: create Maya and Leo, approve both sheets, read, switch child, attempt unapproved version. | MVP passes; unauthorized image is refused. Only then Phase 2 may begin. |
| **15–16** | **P1**, if gate passed: size+position profile controls with Kevin; text below controls with Kevin. Refine click only if Bryan and Andrew's real P1 path works. | Changes reflected in real preview/live site. |
| **17** | Final plan allocates blank-screen reader control, **but global P1 order takes priority**: do it only if earlier P1 work is complete/approved. Otherwise test, help integration, and fix bugs. | No lower-priority feature displaces unfinished higher-priority work. |
| **18** | Full demo reset and tablet+laptop walkthrough. Maintain written issue list. | All screens tested on both devices. |
| **19** | Close issues. Verify final render version integration/approval behavior; don't modify Kevin's `RENDER_VERSION`. | Critical issue list closed; final live site stable. |
| **20** | **Checkpoint 3:** feature freeze. Anything flaky/unfinished is cut; Kevin creates submission draft. | Demo works twice in a row after resets. |
| **20–21** | Bug fixes only. At hour 21 drive app while Kevin records backup video, after reset. | Usable recording captured. |
| **22** | Screenshot every screen and deliver to Kevin for submission. | Screenshots are ready. |
| **23** | Stand by for critical fixes; last deployment by 23:00; no post-deploy feature edits. | Submission check by 23:30; stable demo. |
| **24** | Present. | Ready. |

**Other dependencies:** Bryan + Andrew deploy stand-in API at hour 2; Andrew + Kevin integrate real display at hour 4; Andrew + Bryan integrate real pipeline at hour 7; Kevin gives reader/approval API tests to Andrew at hour 11; Andrew's **demo reset script** is due hour 14. Andrew's reader authorization test is never-cut work; if it needs hour 13, **second look is cut first**. Never let a “second look” enhancement delay reader approval enforcement.

If a lane is more than two hours behind at a checkpoint, pair until the next checkpoint. If the book isn't flowing by hour 8, assume **no Phase 2**. If approval/reader is unfinished at hour 15, Phase 2 becomes MVP repair; Kevin helps Thomas and Bryan helps Andrew. If Contact Sheet is late, a **simple approval list without previews** is an approved schedule fallback, but still must echo exact versions and handle 409.

## 12. Phase 2 — strict feature queue and ownership

**Phase 2 starts only after checkpoint 2 passes.** Globally finish good features (P1) in priority order; **no P2 extras until every P1 is done**. The final plan realistically expects only the first few within five hours:

1. Subject size & position — **Kevin renders; Thomas adds profile controls**. Sizes 40/60/80% of picture area; positions center/left/right/upper/lower; apply to Tinted/Cut-out; do not expose until working end-to-end.
2. Text below picture — **Kevin renders bottom 16% band and checks contrast; Thomas adds on/off control**. No overlap with subject.
3. Evaluation counts on Kevin's slide — Bryan/Kevin, not a reason for Thomas to build a Results screen early.
4. Click to refine missed part — Bryan `refine_mask`, Andrew request support, **Thomas adds explicit refine mode**; saved subject hash changes, requiring fresh approval.
5. Edge contrast warning — Kevin check, Thomas display/override.
6. Tidy teacher outlines — Bryan/Andrew (not Thomas's task).
7. Blank screen between reader pages — Thomas, held until teacher continues, if higher-priority work permits.
8. P2 custom colors — Thomas, only if **all P1** complete.
9. P2 photo of physical page — Bryan/Thomas, only after P1.
10. P2 PDF export with credits — Kevin/Andrew/Thomas, only after P1.
11. P2 teacher notes/read-aloud — Andrew/Thomas, only after P1.

**Important conflict:** Thomas's hour-17 assignment suggests blank-screen P1 while the global queue ranks it seventh. Follow the **global Phase 2 ordering and team checkpoint decision**; treat the hour-17 slot as conditional, not an exception that allows jumping ahead.

No new features after **hour 20**. If the actual submission deadline is earlier, follow Kevin's confirmed earlier shifted schedule.

## 13. Approval safety and demo reset

### Server-enforced versioning

Andrew owns `settings_hash`, `subject_hash`, render version and 12-character approval token `v`. Backend approval matches the profile, page, exact subject mask, settings, level and render version. Changed settings/subject/render make old approval inapplicable; reverting exactly to an earlier state can restore a matching historic approval. The frontend always treats the **server's current sheet and reader manifest** as authority.

- Never display a teacher preview as an authorized reader image.
- Never generate/guess approval tokens.
- Never auto-reapprove a stale sheet after HTTP 409.
- Never replace rejected, failed, or missing pages with their original images.
- Don't hide second-look warnings; they are a weak AI signal, never a truth source and not an approval blocker.

### Reset for every checkpoint rehearsal/judge

**Andrew owns the demo-reset script**. It restores the chosen demo book to a “just processed” state: clears confirmations, teacher-created subjects, and approvals while retaining page images and original AI candidates. The hard page must be unfixed at the start of every demonstration. **Thomas must not implement a parallel frontend reset or silently call a destructive reset endpoint**, because none is in Contract 1.

Before each rehearsal/judge, coordinate that Andrew's script has run; verify the hard page shows uncertainty/error again and the following approval flow can be demonstrated. Do not reset the five backup books. Kevin's demo script owns when reset occurs.

## 14. Tests and acceptance — a task isn't done because it looks good

Build appropriate unit/component tests in `web/`. At minimum:

**API and state**
- App boots and all P0 routes render.
- Upload validates file/type/size and displays backend errors.
- Polling every 2 seconds updates state and cleans up on unmount/terminal status.
- Mocks can be disabled; real requests go to the agreed server without duplicate `/api` prefixes.
- Confirm/retry/omit and candidate selection use exactly agreed request shapes.

**Coordinates — highest risk**
- Candidate boxes, clicks, and outline vertices stay in `[0,1]` in outgoing HTTP.
- Correct mapping under landscape, portrait, letterboxed `object-fit: contain`, CSS scaling, resize, and different device pixel ratios.
- Off-image touches aren't accepted; drawn outlines close, contain at most 200 points, and reject degenerate polygons.
- The live hour-6 **tablet and laptop** alignment test is recorded; a unit test alone does not substitute.

**Profiles/approval**
- Level names map to numeric 1–4.
- Changing unsaved preview settings does not persist or affect approvals; stale responses are ignored; preview rate is bounded.
- Contrast warning at <3:1 and required override note.
- Approve sends each **exact server-supplied version**; rejects only intended pages.
- Simulated 409 shows “Look again,” refreshes data, never auto-approves.

**Reader safety**
- Reader uses **only authorized reader routes**; unapproved or outdated image 403 shows no image.
- Single tap/click does nothing; chosen tablet gesture/fallback works; arrow/space/T work without interfering with form inputs.
- Teacher bar disables versions not fully approved; child/level switching doesn't bypass checks.
- Skipped pages, credits, prefetch, object-URL cleanup, version-keyed cache and fast switches verified.
- The actual tablet test includes full-screen and browser gesture interference; laptop test includes keyboard navigation.

**End-to-end checkpoint scripts**

- **Hour 8:** upload demo book; see page states; fix one by click; fix another by outline; see all four looks on live server.
- **Hour 15:** reset; repeat above; create Maya/Leo; approve each sheet; read on tablet; switch child; **unapproved image is denied**, without restarting.
- **Hour 20:** reset; run exact timed judge script, **twice consecutively** with every shown feature working.

If possible run `npm run build`, `npm run typecheck`, `npm test` (or the repo's actual equivalent) before claiming a milestone. Report commands and outcomes, not assumed passes. Backend 403/409 enforcement is tested by Andrew and Kevin; frontend test verifies its correct UI handling.

## 15. Product integrity, privacy and attribution

- Only fictional demo children; no real child identity or sensitive profile data in demo fixtures.
- Inform teachers that book pages are sent to an outside AI service; do not leak any API key in the browser.
- Books used for the demo must have suitable rights. Credits include author, illustrator, publisher, source, license and a note that adaptations were made. Original source images are preserved server-side.
- Avoid promises of clinical benefit, assessment or TVI validation. If teacher review has not occurred, do not claim it has.
- Supported P0 input: PDF, max 30 pages, 50 MB, one page per PDF page. Backend determines and flags unsupported spreads and low-quality artwork. The frontend makes failure/uncertainty visible and offers retry/teacher correction/omit, never a fabricated success.
- The child is not the operator. Teacher retains control over page progression and all approvals.

## 16. Definition of done and reporting format

For each completed slice, report briefly:

1. **Completed:** exact behavior visible now, and whether it uses mocks, live stand-ins or real pipeline.
2. **Files changed:** only paths inside `web/`.
3. **Verified:** commands/tests actually run, plus real tablet/server checks when applicable.
4. **Contract blockers:** concise message to Bryan/Kevin/Andrew, with example payload if needed.
5. **Next milestone:** the next unfinished item under the FINAL plan. Do not jump the Phase 2 gate.

**Do not say “done” when only a static screen exists, a button has no effect, a required API integration is still mocked in live mode, a build is broken, or approval/reader safety hasn't been tested.**

## 17. Start here — instructions for the very next action

1. Read the FINAL plan, full spec, agreed route examples and existing `web/` code.
2. Locate current hackathon hour and determine whether Thomas has finished D1, D2, D3, D4, D5, D6 or D7; if unknown, start with the earliest incomplete P0 task.
3. If at start: confirm Andrew's repo link and normalized HTTP coordinate agreement, find the tablet, and finalize one JSON request/response fixture for every API route with Andrew.
4. Scaffold/repair the Vite+React+TypeScript+Tailwind app; make **every route mockable** and the typed client robust, staying inside `web/`.
5. Implement Library and Subject Review; **switch to Andrew's real stand-in API at hour 3**; then subject editor with normalized click/outline; validate the hour-6 alignment checkpoint.
6. Continue Profiles → Contact Sheet with exact approval tokens/409 → authorized Reader with device-tested controls/prefetch/credits → remove remaining live mocks by hour 14.
7. Do not start any Phase 2 feature until the **hour-15 MVP checkpoint actually passes**.

**Success is a complete, demo-safe, teacher-controlled Mirai frontend — running live on the real API, with original-artwork adaptations and no path to viewing unapproved pages.**
