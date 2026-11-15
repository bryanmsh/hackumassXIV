# Miraai 24-Hour Build Plan

Nov 14, 2026 · @Andrew Choi

The build has two parts. The MVP is every P0 feature and is done by hour 15. Phase 2 adds the good features, then the extras, until the freeze at hour 20. The last four hours are for fixes, rehearsal and submission. Hour 0 is the moment you start.

## At a glance

&#91;embedded content: roadmap · four phases, three checkpoints, 24 hours\]

The whole team stops only at the three checkpoints. Between them, each person works in their own lane.

## Team

Each person owns one part of the app and its folders, and nobody edits anyone else's folders.

| Person | Owns | In one line | Folders | Lane in the spec |
| --- | --- | --- | --- | --- |
| Bryan | Pipeline and server | Turns a PDF into page images, the AI's choice of subject, and cut-outs. Runs the server | `pipeline/`, `fixtures/`, `infra/`, `Dockerfile`, `compose.yaml`, `Caddyfile` | A |
| Kevin | Display, checks and pitch | Turns a page and a cut-out into what the child sees, checks the result, and owns the slides and demo | `render/`, `checks/`, `eval/`, `pitch/`, `tests/` | B |
| Andrew | API and data | The backend and database: saves everything, tracks approvals, refuses unapproved pages | `api/`, `contracts/` | C |
| Thomas | Web app | Every screen the teacher sees and touches | `web/` | D |

## Decide in the first ten minutes

Four things are settled together before anyone starts, because each one causes a late bug or a missed deadline if left open.

| Decision | Answer | Who acts |
| --- | --- | --- |
| Where the repo is | Andrew creates it in the first five minutes and shares the link, before anything else | Andrew |
| How positions are measured | The API uses fractions from 0 to 1 of the page's width and height, from the top-left corner, for boxes, clicks and outlines. Andrew converts to master pixels in one place before calling Bryan's code. Masks are the size of the 3,000 px master | Andrew, Thomas, Bryan |
| The real deadline | Find out when hacking ends, when submissions close, and whether judging is at tables or on a stage. If "hour 24" is when hacking ends, the plan holds. If it is when you present, move everything an hour earlier | Kevin |
| Who gets the teacher email | Pick one named person now, not a general inbox, so hour 3 is only pressing send. Expect no reply on a weekend; without one the pitch says "not yet reviewed by a teacher" | Kevin |

## Ground rules

- Make your own fakes. Whoever needs a stand-in writes it and swaps in the real thing when it lands, so nobody waits for anyone else's code.
- The contracts in the spec are frozen. A change needs all four and may only add fields.
- Commit small and often to `main`, inside your own folders. `main` must always start.
- Anyone more than two hours behind at a checkpoint gets a partner until the next one.
- Nobody starts a Phase 2 feature until checkpoint 2 passes.
- Run the demo reset script before every rehearsal and every judge, so the hard page is unfixed each time.
- Naps are optional, 90 minutes, between hours 15 and 20, at most two people at once. Bryan and Thomas take one slot and Andrew and Kevin the other, so each working pair keeps one person awake. Each nap costs roughly one Phase 2 feature.

## Hours outline

The MVP takes hours 0 to 15, Phase 2 takes hours 15 to 20, and the wrap-up takes hours 20 to 24. Joining the four parts is spread across hours 2 to 7, one part at a time, so no hour depends on everything meeting at once. The hours are estimates; the checkpoints are the fixed points.

| Hours | Part | Team goal by the end of the block |
| --- | --- | --- |
| 0 to 2 | MVP | Repo exists in five minutes. The four decisions are made. First outputs: page images, a first AI answer, two looks, an app shell, and an API that answers with stand-in data |
| 2 to 4 | MVP | The stand-in API is live on the server with every dependency installed together. Thomas's app talks to it. All four looks exist. The teacher email is sent |
| 4 to 6 | MVP | Kevin's real display code runs inside the API. The cut-out tool is chosen. Gestures are tested on the demo tablet. Click and outline work in the editor, and a drawn outline lands in the right place |
| 6 to 8 | MVP | Bryan's real pipeline is swapped in, which is the only joining left. **Checkpoint 1 at hour 8: one book flows end to end** |
| 8 to 10 | MVP | A child profile changes the picture. Failures are handled |
| 10 to 12 | MVP | A contact sheet can be approved. Backup books are processed. The demo book is chosen. Reader tests are written |
| 12 to 15 | MVP | The reader shows approved pages only. The demo can be reset. No fakes are left. **Checkpoint 2 at hour 15: the MVP is done** |
| 15 to 17 | Phase 2 | Good features 1 and 2: subject size and position, and text below the picture |
| 17 to 20 | Phase 2 | Evaluation counts and slides with numbers, then more good features if time allows. **Checkpoint 3 at hour 20: feature freeze** |
| 20 to 22 | Wrap-up | Submission draft created. Backup books approved. Two rehearsals. Backup video recorded |
| 22 to 24 | Wrap-up | Submission finished. Final rehearsal. Present |

## Working together

Most tasks are solo. These are the only ones that need more than one person. Andrew is in most of them, so they are spread out: the old plan needed about four hours of Andrew in hours 6 and 7, and this one needs about one.

**At the same screen**

| Hour | Who | Task | How long |
| --- | --- | --- | --- |
| 0 | Everyone | The four decisions above | 10 minutes |
| 0 | Andrew and Thomas | Write one example response for every API route into a shared file, using 0 to 1 positions | 30 minutes |
| 2 | Bryan and Andrew | First deploy: the API on stand-ins, with all three requirements files installed together | 30 minutes |
| 3 | Andrew and Thomas | Point the web app at the live stand-in API | 15 minutes |
| 4 | Andrew and Kevin | Switch the API from the stand-in display to Kevin's real display code | 30 minutes |
| 6 | Andrew and Thomas, Bryan on call | Draw an outline on screen and confirm the cut-out lands in the same place | 15 minutes |
| 7 | Bryan and Andrew | Swap in the real pipeline and redeploy | About 1 hour |
| 10 | Bryan and Kevin | Choose the demo book and its hard page | 15 to 20 minutes |
| 12 | Bryan and whoever is furthest behind | Catch-up pairing | Up to 1 hour |
| 13 | Bryan and Andrew | Run the second look over backup-book pages that were confirmed before it existed | 15 minutes |
| 14 | Andrew and Thomas | Fix the last joining bugs | Up to 1 hour |
| 21 | Kevin and Thomas | Record the backup video, with Thomas driving the app | 30 to 45 minutes |

**Whole team**

| Hour | Task | How long |
| --- | --- | --- |
| 8 | Checkpoint 1: one book flows end to end | 30 minutes |
| 15 | Checkpoint 2: the full demo, then choose Phase 2 features | 45 minutes |
| 20 | Checkpoint 3: feature freeze, and the submission draft is created | 30 minutes |
| 22 to 23 | Finish the submission and the final rehearsal | Most of both hours |

**Quick handoffs, a few minutes each**

| Hour | From | To | What |
| --- | --- | --- | --- |
| 0 | Andrew | Everyone | The repo link, in the first five minutes |
| 2 | Bryan | Everyone | The Gemini model name and how its boxes come back |
| 4 to 5 | Bryan | Kevin | Real page images and cut-outs |
| 11 | Kevin | Andrew | Reader and approval tests to run against the API |
| 17 | Bryan | Kevin | Pipeline results for the evaluation pages |
| 19 | Kevin | Andrew | The final render version, before the final deploy |

**Built separately, tested together**

Each Phase 2 feature needs two or three people's pieces. Each person builds theirs in their own folder, and they meet for ten minutes to test it. The pairs are Kevin and Thomas for size, position and text, and Bryan, Andrew and Thomas for click to refine.

# Part 1: MVP (P0 features, hours 0 to 15)

## Bryan: pipeline and server

Bryan gets the book into the app. The server now goes up at hour 2 on stand-in data, so the risky pipeline work in hours 3 to 7 is never mixed with a first deploy.

| Hours | Task | What to do | Done when | With |
| --- | --- | --- | --- | --- |
| 0 | Page images | Install PyMuPDF. Render each page of the demo PDF at 300 DPI, cap the longer side at 3,000 px, and save a 1,600 px working copy beside it. Pull out each page's text. Commit six pages to `fixtures/`. Send the Vultr GPU request and create the server instance so it is booting | Six page images and their text are on `main`; the instance is starting | Nobody |
| 1 | First AI answer | Get a Gemini key working. Send one page image and its text. Ask whether the page has one subject, several, or is a scene, and for up to three candidates, each with a name, other names for it, a box and a confidence. Ask for JSON. Then send four calls at once to see whether you hit a rate limit | Answers for three pages are saved. The model name and box format are posted to the team | Nobody |
| 2 | Server and first deploy | Install Docker. Run Caddy with HTTPS and a site password. Write the `Dockerfile` so it installs all three requirements files together, which exposes package conflicts now and not at hour 7. Deploy Andrew's API running on stand-ins. While the image builds, write the outline function: fill the teacher's drawn shape and use it as the mask, with no AI | The live site asks for a password and answers API calls with stand-in data | Andrew |
| 3 to 4 | Cut-out trial | Give EdgeSAM setup 45 minutes at most. Type a box around the subject on three pages by hand and get a cut-out for each. Look closely at legs, thin lines and small animals. Also try SAM 2 small on CPU: it runs once per page, so a few seconds each may be acceptable, though that is untested. Use the GPU only if both fail. Decide by the end of hour 4 | Three cut-outs and a decision the team has heard | Kevin at hour 5 |
| 5 to 6 | One function per page | Write `process_page`. It calls Gemini, converts the boxes to master pixels, cuts a mask for each candidate, and cleans each mask by keeping the biggest piece and filling tiny holes. Then it sets the page state by the rules in the spec. Wrap it so an error returns Failed with a reason and never crashes. Add the click function: one point where the teacher clicked | All six test pages return a state, at least one is Needs subject, and a click returns a cut-out | Nobody |
| 7 | Pipeline in | Swap the real pipeline into the API with Andrew and redeploy. This is the only joining left before checkpoint 1 | A real book processes on the live site | Andrew |
| 8 to 9 | Failure handling | Add a 20-second timeout and one retry to every AI call. A rate-limit reply should wait, then retry. Force a failure and confirm the rest of the book still processes. Tune the page-state rules on the six test pages only | A forced failure shows Failed with a reason, and the other pages are fine | Nobody |
| 10 to 11 | Backup books | Pick five books with Kevin, including the demo book. Upload each on the live site, look at every cut-out, and fix bad ones by click or outline | Five books are fully processed on the live server | Kevin |
| 12 | Float | Pair with whoever is furthest behind, most likely Andrew on the reader | That person is unblocked | Whoever is behind |
| 13 to 14 | Keep it running | Redeploy after Andrew's changes. With Andrew, run the second look over backup-book pages that were confirmed before it existed. Watch Gemini usage | The live site matches `main`, and every backup page has a second-look result | Andrew |

## Kevin: display, checks and pitch

Kevin decides how each page looks to the child, writes the automatic checks, and owns the pitch. Kevin's code needs nothing from anyone, so it joins the API early, at hour 4, and Kevin also writes the tests for the reader.

| Hours | Task | What to do | Done when | With |
| --- | --- | --- | --- | --- |
| 0 | Sample files and two answers | Screenshot two pages of any picture book. In any image editor, paint the main object white and everything else black, and save each as a PNG the same size as its page. Then find out the real deadline and judging format, and pick the named teacher to email | Two pages and two masks are saved. The deadline is posted. A name is chosen | Nobody |
| 1 | Cut-out and Tinted | Write a script that loads a page and a mask. Soften the mask edge by 2 px, crop the object, scale it to 60% of the canvas and center it on a black background. That is Cut-out. For Tinted, turn the object into light and dark values and multiply by the child's color, so shading survives | Both looks are right for both samples | Nobody |
| 2 to 3 | Faded page and Outlined | Faded page: drain most of the color, blend with the background color, then paste the object back at full color. Outlined: grow the mask by 8 px, subtract the mask, and fill that ring with the child's color on the untouched page. Add the overlay image, which is the cut-out tinted over the original. Save as WebP. At the end of hour 3, send the teacher email with the four images and three questions | All four looks exist for both samples. The email is sent | Nobody |
| 4 | Display in | Andrew switches the API to your real display code now, using stand-in masks. Fix the display bugs that appear | Andrew's preview shows your looks on the live site | Andrew |
| 5 | Real artwork | Replace your samples with Bryan's six pages and cut-outs. His cut-outs are at the 3,000 px master size and you display at 1,600 px, so scale carefully. Fix what breaks | All six test pages render in all four looks | Bryan |
| 5 to 6 | Checks | Write `run_checks`. Is the cut-out in one piece? Does it touch the page edge? Is the background plain at Tinted and Cut-out? Does the subject stand out from the background? Is it big enough to find? Each check returns pass, warn or fail with one plain sentence | Checks pass on good cut-outs and fail on a deliberately bad one | Nobody |
| 7 | Script steps | List the demo's steps in order. Walk them on the live site as Bryan's pipeline lands, and note what is missing for checkpoint 1 | A step list the team can run at hour 8 | Nobody |
| 8 to 9 | Second look | Write `second_look`. Show Gemini only the Cut-out image on black and ask for the object's name in one to three words. It passes when the answer shares a word with the label or its other names. Then run every check on all six pages | It names the subject on the samples | Nobody |
| 10 | Demo script | Write the script word for word, including who clicks what and when the reset script runs. Choose the demo book and its hard page with Bryan | A one-page script | Bryan |
| 11 | Reader tests | In `tests/`, write tests that call the API from outside: an approved page is served, a never-approved page is refused, a page approved and then changed is refused, and a stale approval gets "look again." They fail until Andrew's routes land, then pass | Four tests exist and Andrew has them | Andrew |
| 12 to 13 | Slides | Outline, then a first draft: the problem, the demo, how it works, what is measured, and the limits | A slide exists for every part of the script | Nobody |
| 14 | Dry run | Run the demo script alone on the live site. Write down every gap for checkpoint 2 | A list of gaps | Nobody |

## Andrew: API and data

Andrew builds the part in the middle that remembers everything and enforces the rules. The other three parts now join one at a time, at hours 2, 3, 4 and 7, so Andrew is never needed in three places at once.

| Hours | Task | What to do | Done when | With |
| --- | --- | --- | --- | --- |
| 0 | Repo, then examples | In the first five minutes, create the repo with the folder layout from the spec, push it, and share the link. Then sit with Thomas for 30 minutes and write one example response for every API route as JSON in a shared file, with positions as 0 to 1 fractions. Then copy in the shared types and the hashing helper | Everyone can commit by minute 5. The examples file is agreed | Thomas |
| 1 | Stand-ins and a skeleton | Write fake versions of Bryan's and Kevin's functions that return fixed, valid output: two candidates, a rectangle mask, and a display that returns the page unchanged. Put each behind a setting. Start an API that answers every route with example-shaped data, so Bryan can deploy it at hour 2 | The API starts and answers on stand-ins | Nobody |
| 2 to 3 | Upload and page states | Set up the Atlas cluster. Uploading a book saves the PDF and answers at once. A background task then makes the page images and processes up to four pages at a time, saving each result as it lands. Add the routes that list books and pages. Help Bryan with the first deploy at hour 2, and tell Thomas when the live site is ready at hour 3 | Uploading a PDF on the live site shows pages moving to Ready | Bryan, Thomas |
| 4 | Display in | Switch the display setting from the stand-in to Kevin's real code. Add the overlay image and the preview route, which takes unsaved settings and stores nothing | The live preview shows Kevin's four looks | Kevin |
| 5 to 6 | Subject routes | One route takes a pick, a click or an outline. Convert 0 to 1 positions to master pixels in exactly one function, then call the matching pipeline function, store the new candidate and select it. Wire the outline to Bryan's real outline function now. Add confirm, leave out and retry. On startup, mark anything still Processing as Failed. At hour 6, check with Thomas that a drawn outline lands in the right place | A killed server restarts with nothing stuck. A drawn outline produces a mask in the same place | Thomas |
| 7 | Pipeline in | Switch the pipeline setting from the stand-in to Bryan's real code and fix what breaks. This is the only joining left | A real book flows end to end on the live site | Bryan |
| 8 to 9 | Profiles | Create and edit a child profile. Compute the settings hash from the display settings only, not the name or the chosen look. Add the route that renders a page for a saved profile | Changing a color and changing it back gives the same hash | Thomas |
| 10 to 11 | Sheet and approve | Sheet route: for each page, return its version, its check results and whether it is approved. Approve route: compare each version sent with the current one, record the matches, and answer "look again" for the rest | A stale approval is refused | Thomas |
| 12 | Reader | List the approved pages for a child and look. Serve a page image only when that exact version is approved, and refuse otherwise. Send "do not cache" with every image. Run Kevin's four tests until they pass. This task is on the never-cut list: if it overruns, take hour 13 for it | Kevin's tests pass | Kevin |
| 13 | Second look job | When a subject is confirmed, start the second look in the background and store its result. Add a command that runs it for pages confirmed earlier, and run it on the backup books with Bryan. **This is the first thing to cut if the reader needed this hour** | Every confirmed page has a second-look result | Bryan |
| 14 | Demo reset | Write a script that returns one book to "just processed": it clears confirmations, teacher-made subjects and approvals, and keeps the pages and the AI's candidates. Then fix the last joining bugs with Thomas | Running it makes the hard page wrong again, ready for the next judge | Thomas |

## Thomas: web app

Thomas builds everything the teacher sees and touches. From hour 3 the app talks to the live API on stand-in data, so there is no big switch from mocks later, and the tablet gestures are proven at hour 4, not hour 18.

| Hours | Task | What to do | Done when | With |
| --- | --- | --- | --- | --- |
| 0 | Example responses | Sit with Andrew for 30 minutes and agree one example response for every API route, with positions as 0 to 1 fractions. Find the tablet you will demo on | The file is agreed. The demo tablet is in hand | Andrew |
| 1 | App shell | Create a React app with Vite, TypeScript and Tailwind. Add a route for every screen. Put all server calls in one small file. Set up mocks that return the agreed examples, with placeholder images | Every route has a mock | Nobody |
| 2 | Library | An upload button with fields for the book's credits. A list of books, each showing how many pages are ready, need a pick, or failed. Refresh every 2 seconds while a book is processing | Works on mocks | Nobody |
| 3 | Subject review, then go live | A grid with one card per page: the overlay image, the subject's name and confidence, and the page state. Buttons for Confirm, Confirm all, Leave out and Retry. At the end of the hour, change one setting to point the app at the live stand-in API. Keep the mocks as a fallback | Library and Subject review work against the live site | Andrew |
| 4 | Gesture test, then click to pick | Spend ten minutes on the demo tablet with a bare page: try a two-finger swipe and a two-finger tap, and see whether the browser zooms or goes back instead. Turn off the browser's own touch handling on that page and try full-screen mode. If it is still unreliable, switch to a long press in a corner for the teacher bar and a keyboard or clicker for page turns. Then build click to pick: clicking a suggestion selects it, and clicking elsewhere sends that point as 0 to 1 fractions | The gesture method is decided. The right position is sent | Nobody |
| 5 | Outline drawing | A text field for the object's name. Let the teacher draw with a finger or mouse. Keep at most 200 points, close the shape, convert to 0 to 1 fractions, and send | A drawn outline is sent | Nobody |
| 6 | Alignment check | With Andrew, draw an outline on screen and confirm the returned cut-out sits exactly where it was drawn, on both the tablet and a laptop. Fix any offset now | Outline and cut-out line up on both devices | Andrew |
| 7 | Real pipeline data | When Bryan's pipeline lands, check Subject review and the editor against real candidates and states. Fix what breaks | The checkpoint 1 steps work on screen | Bryan, Andrew |
| 8 to 9 | Profiles | A form with name, look (the four named looks), up to three colors from eight swatches, and a background. The live preview asks the server at most every 300 ms and saves nothing until Save. Warn when the color and background are too close, with a note field to override | Trying colors does not disturb approvals | Andrew |
| 10 to 11 | Contact sheet | Choose a child and a look. Show a grid of previews with each page's check results. Approve the sheet, or reject single pages. Send back exactly the versions you received. On "look again," reload those pages and tell the teacher | Works, including a forced "look again" | Andrew |
| 12 | Reader input | Full screen, one page, no buttons. Ignore single touches. Turn pages with the method chosen at hour 4, and with the arrow keys | A single tap does nothing | Nobody |
| 13 | Reader extras | A teacher bar listing only approved versions, with the rest greyed out. Fetch the next page and the other approved versions ahead of time and hold them in memory as blobs, because the server tells the browser not to cache them. Make credits the last screen | Switching child takes under a second with the network throttled | Andrew |
| 14 | Last fixes | Remove any mock still in use. Fix the last joining bugs with Andrew | No screen uses a mock | Andrew |

# Part 2: Phase 2 (good and extra features, hours 15 to 20)

## What is in Phase 2

Phase 2 starts only after checkpoint 2 passes. Good features (P1 in the spec) come first, in the order below; extras (P2 in the spec) come only when every good feature is done. Five hours is realistically enough for the first three.

| Order | Feature | Kind | Who builds a piece |
| --- | --- | --- | --- |
| 1 | Subject size and position | Good | Kevin, Thomas |
| 2 | Text below the picture | Good | Kevin, Thomas |
| 3 | Evaluation counts on a slide | Good | Bryan, Kevin |
| 4 | Click to refine a cut-out | Good | Bryan, Andrew, Thomas |
| 5 | Edge contrast warning | Good | Kevin, Thomas |
| 6 | Tidy hand-drawn outlines | Good | Bryan, Andrew |
| 7 | Blank screen between pages | Good | Thomas |
| 8 | Custom color picker | Extra | Thomas |
| 9 | Photo of a physical page | Extra | Bryan, Thomas |
| 10 | Export as PDF with credits | Extra | Kevin, Andrew, Thomas |
| 11 | Teacher notes, read-aloud | Extra | Andrew, Thomas |

Until features 1 and 2 land, Leo's demo profile is Cut-out, centered, with text off.

## Bryan in Phase 2

| Hours | Task | What to do | Done when | With |
| --- | --- | --- | --- | --- |
| 15 to 16 | Good: click to refine | Rerun the cut-out tool with the original box plus the teacher's extra click as a second hint. Save the result as a new cut-out and keep the old one | A missed tail can be added with one click | Andrew, Thomas |
| 17 | Evaluation run | Run Kevin's 20 evaluation pages through `process_page`. Save each page's state and chosen subject to one file | Kevin has the file | Kevin |
| 18 | Good: tidy outlines | For a hand-drawn outline, run the cut-out tool on the area it covers. Use the result only if it overlaps the outline well; otherwise keep the outline as drawn | A rough outline snaps to the object on two test pages | Andrew |
| 19 | Final cut-outs | Check the demo book's cut-outs one last time. Do the final deploy with Andrew | The demo book is final on the live site | Andrew |
| If time | Extra: photo of a page | Accept a JPG or PNG as a one-page book | A phone photo of a flat page processes | Thomas |

## Kevin in Phase 2

| Hours | Task | What to do | Done when | With |
| --- | --- | --- | --- | --- |
| 15 | Good: size and position | Scale the subject to 40%, 60% or 80% of the picture area. Place it center, left, right, upper or lower, always kept inside the edges | Leo's subject sits left and large | Thomas |
| 16 | Good: text below | Reserve the bottom 16% of the canvas as a text band. Draw the page text large, in white or black, whichever contrasts more. Add the text contrast check, and keep the band out of the background check | Text shows and never overlaps the subject | Thomas |
| 17 | Evaluation labels and counts | For 20 pages from other books, write down the intended subject before opening Bryan's results. Then compare, and count correct subjects, correctly flagged pages, confidently wrong pages and cut-out defects | Counts are ready for a slide | Bryan |
| 18 | Slides with numbers | Add the counts as counts, not percentages. Run ChatGPT once by hand on three pages for one comparison slide. Finish the second draft | Slides are complete | Nobody |
| 19 | Final display | Add the edge contrast warning if there is time. Then set the final render version and tell Andrew | No display changes after this | Andrew |
| If time | Extra: export as PDF | Lay the approved pages into a PDF with the credits as the last page | A book exports with credits | Andrew, Thomas |

## Andrew in Phase 2

| Hours | Task | What to do | Done when | With |
| --- | --- | --- | --- | --- |
| 15 to 16 | Bug list | Work through the checkpoint 2 bugs first. Then accept refine requests on the subject route, and pass the tidy option for outlines | Checkpoint 2 bugs are closed | Bryan, Thomas |
| 17 | Approval tests | Extend Kevin's tests to the edge cases: profile edited, subject changed, render version changed, and switching back restores the approval | All pass | Nobody |
| 18 | Re-approve tool | A script that copies a backup book's approvals to a new render version. It is for emergencies only and prints everything it writes | It runs on one backup book | Bryan |
| 19 | Final deploy | After Kevin sets the final render version, do the final deploy with Bryan | The live site is final | Bryan, Kevin |
| If time | Extra: teacher notes | Store a short note per page and child | A note saves and reloads | Thomas |

## Thomas in Phase 2

| Hours | Task | What to do | Done when | With |
| --- | --- | --- | --- | --- |
| 15 | Good: size and position | Two controls in Profiles. The preview updates as they change | Both controls change the preview | Kevin |
| 16 | Good: text and refine | A text on or off control in Profiles. In the Subject editor, an "add a missing part" click mode if Bryan builds refine | Both work on the live site | Kevin, Bryan |
| 17 | Good: blank screen | A reader option that shows the plain background between pages until the teacher continues | Works on the tablet | Nobody |
| 18 | Tablet pass | Use every screen on the demo tablet and on a laptop, start to finish, after a reset. Write down every problem | A written list | Nobody |
| 19 | Fixes | Fix what the tablet pass found | The list is closed | Nobody |
| If time | Extra: custom colors | A color picker beside the eight swatches | A custom color saves and previews | Nobody |

# Wrap-up (hours 20 to 24)

## The last four hours

No new features after hour 20. Everyone's job is to make the demo safe. The submission is created as a draft at hour 20 and edited from then on, so nothing depends on a first send at the last minute.

| Hours | Bryan | Kevin | Andrew | Thomas |
| --- | --- | --- | --- | --- |
| 20 | Confirm and approve all five backup books on the live server | Create the submission draft with title, team and one paragraph. Reset the demo, then rehearsal 1, timed | Bug fixes only | Bug fixes only |
| 21 | Check the backup books still read with the AI switched off | Reset, then rehearsal 2. Record the backup video | Bug fixes only | Drive the app for the video |
| 22 | Add "how it works" and "how to run it" to the draft | Finish the project description in the draft | Write the README | Add a screenshot of each screen to the draft |
| 23 | Last deploy by 23:00, then touch nothing | Reset, then rehearsal 3. Final check of the submission by 23:30 | Stand by for fixes | Stand by for fixes |

If Kevin's check at hour 0 shows submissions close before hour 24, move the whole table earlier by that amount.

## Checkpoints

Each checkpoint is the same routine: run the script on one screen together, write down what broke, and decide who pairs with whom.

| Checkpoint | Script to run | Passes when |
| --- | --- | --- |
| 1, hour 8 | Upload the demo book. Watch pages get states. Fix one subject with a click. Fix another by drawing an outline. View one page in all four looks | Every step works on the live site, even if slowly or roughly |
| 2, hour 15: MVP done | Run the reset script. Then everything in checkpoint 1, plus: create Maya and Leo, approve a contact sheet for each, read the book on the tablet, switch child mid-book, try to open an unapproved version | The reader refuses the unapproved version, and the rest runs without a restart |
| 3, hour 20: freeze | Reset, then the demo script exactly as it will be presented, timed | It fits the time limit, and every feature shown works twice in a row |

## If you are behind

| At | If this is not working | Do this |
| --- | --- | --- |
| Hour 2 | The three requirements files will not install together | Bryan and the owner of the clashing package fix versions now. Do not carry it to hour 7 |
| Hour 4 | EdgeSAM is not installed after 45 minutes | Go straight to SAM 2 small on CPU. If that also fails, use the GPU, and until then use hand-drawn outlines |
| Hour 4 | Two-finger gestures are unreliable on the tablet | Use a long press in a corner for the teacher bar and a keyboard or clicker for page turns |
| Hour 6 | A drawn outline lands in the wrong place | Stop and fix it before anything else. Check that only one function converts 0 to 1 positions to pixels |
| Hour 8 | The AI's subject choice is unreliable | Treat every page as "teacher picks." The demo still works and the story is still honest |
| Hour 8 | A book does not flow end to end | Bryan and Andrew pair until it does. Plan for no Phase 2 |
| Hour 12 | The reader's approval check overruns | Andrew keeps going into hour 13 and the second-look job is cut. Second look is a warning, not part of the promise |
| Hour 15 | Approval or the reader is unfinished | Phase 2 becomes MVP work, with Bryan helping Andrew and Kevin helping Thomas. No extras |
| Hour 15 | The Contact sheet is unfinished | Approve from a simple list of pages, without previews |
| Hour 20 | Anything is flaky | Cut it from the demo and show a backup book |

**Never cut:** original-artwork cut-outs, two children on one book, teacher approval before reading, and the reader refusing unapproved pages. Those four are what make Miraai more than an image filter.
