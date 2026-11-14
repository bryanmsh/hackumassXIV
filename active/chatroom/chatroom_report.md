# Agent Chatroom Report

**Problem:** Pick one of four HackUMass XIV ideas (FocusPage, Crosscheck, Receipts, LectureLens) and note potential fixes for each. Pivots and merges are allowed.
**Agents:** 6 (Sonnet) | **Rounds:** 3 | **Date:** 2026-11-13

## Participants

| Agent | Role | R2 confidence (own idea) | Final pick | Final confidence |
|---|---|---|---|---|
| A | FocusPage advocate | 7 | FocusPage | 7/10 |
| B | Crosscheck advocate | 5 | FocusPage if both gates pass, else whichever passes | 5/10 (in Crosscheck) |
| C | Receipts advocate | 2 | FocusPage | 6/10 |
| D | LectureLens advocate | 3 | FocusPage | 6/10 |
| E | Hackathon Judge | n/a | FocusPage | 6/10 |
| F | Critic | n/a | FocusPage (gated) | 7/10 |

Judge's scorecard after fixes (out of 50): **FocusPage 40**, Crosscheck 38, Receipts 32, LectureLens 31.

## Consensus

1. **Build FocusPage, with a small test ("gate") before committing, and Crosscheck as the pre-declared fallback.** All six agents ended there. The Crosscheck advocate agreed FocusPage wins if both pass their gates.
2. **Receipts and LectureLens are out.** Their own advocates rated them 2/10 and 3/10. Receipts' headline claim ("first to cross-check self-report against the official transcript") is false: EdVisorly's EddyVerify markets exactly that. LectureLens's vocabulary boosting is already a standard vendor feature (Otter, Verbit, Panopto, Deepgram and AssemblyAI keyterms). Only "build the glossary automatically from the syllabus" is new, and that is too thin.
3. **Don't build a merged product.** "AI that shows its uncertainty" is fluff as a tagline. It only counts as concrete UI, such as a flagged-page card or a mask overlay.
4. **Ban clinical or certainty words.** FocusPage's badge reads "object still recognizable (machine check)." Never use "verified," "safe," or "CVI-approved." Crosscheck says "readers agree," never "confirmed."
5. **Every idea is open to the "disability dongle" critique** (a tool for disabled users built without them). Email practitioners Friday, but expect maybe 1 reply in 5 on a weekend. The fallback slide reads: "Design follows published guidance (Roman's CVI Range); no user validation yet."
6. **Report counts with denominators, not percentages,** and set pass thresholds before running any test.

## Key Disagreements

**How to run the gate.** This is the one real split.
- *Commit up front, insurance only* (A, C, D, E): commit to FocusPage now and run only its 10-page gate. One person spends 45 to 90 minutes on a Crosscheck photo smoke test as insurance. Their reasoning: a symmetric dual gate burns about 25% of the hours before any product code.
- *Parallel dual gate* (B): two people per idea, hard stop at hour 6, and Crosscheck must also show a catch rate, not just that errors exist.
- *Critic's compromise* (F): two people on FocusPage, one on Crosscheck, one on outreach. Hard stop at hour **2.5**, and FocusPage wins if it passes regardless of Crosscheck.

**Segmentation backend.** A favors SAM 2 prompted with Gemini's bounding box, with crop plus rembg as fallback. C and E favor crop plus rembg alone (no SAM, no hosting). Both link the object name to the mask through Gemini's box.

**What L1 looks like.**
- A and E: a luminance-preserving tint in the child's color, so shading survives.
- C: the real-color cutout with a rim in the child's color.
- F: make L2 (real colors on a plain background) the default.
- Everyone agrees L1 falls back to L2 automatically if recognition fails.

## Recommended Action (orchestrator synthesis)

**Commit to FocusPage. Use the Critic's 2.5-hour gate with the Critic's staffing.** It is cheap enough to satisfy the commit-up-front camp and still produces real Crosscheck data as insurance.

**Friday timeline (H0 = kickoff)**
- **H0–0.5:** Two people pull 10 real StoryWeaver pages (flat, painted, and multi-object). One person shoots 15 degraded bottle photos from 5 bottles and writes the ground truth. The fourth emails a TVI, Perkins, Anchor Center, and UMass Disability Services. That person also checks the "leading cause" and "90% fatigue" figures, confirms Gemini's box output on the current model, and checks the Be My AI and Seeing AI release notes.
- **H0.5–2.5:** FocusPage runs Gemini (subject name plus box), then crop plus rembg inside the box, then the mask sanity check. Two teammates blind-judge whether the correct subject was cut out. Crosscheck runs Claude alone and Gemini alone and counts confident wrong reads. **No UI work yet.**
- **H2.5 hard stop:**
  - FocusPage at 7 or more of 10 → build FocusPage.
  - FocusPage at 4–6 → try SAM 2 box-prompting for 1 hour on 10 new pages.
  - FocusPage still failing and Crosscheck at 3 or more silent errors of 15 → build Crosscheck.
  - Neither passes → ship FocusPage on a curated shelf of the page types that worked, and say so openly.
- **H3–8:** Thin end-to-end slice on one book by H8: ingest, subject and box, cutout cache, L2 then L1, fullscreen viewer.
- **No switching on Saturday** unless Crosscheck's gate already passed. Narrow scope instead.

**Minimal FocusPage pipeline (agreed)**
1. Ingest: PyMuPDF renders pages to PNG, or StoryWeaver images are used directly.
2. One Gemini Flash call with a JSON schema returns `main_subject`, a box (0–1000 scale), `other_objects`, and flags for `multi_object` and `text_in_art`.
3. Cutout: crop to the box with padding, then rembg (isnet-anime is worth trying for illustrations). Upgrade to SAM 2 with the box as prompt if masks are ragged.
4. Render: L1 tint on black, L2 real colors on plain, L3 faded scene with a vivid object. L4 only if time allows. Cutouts are cached, so switching children or levels is instant.
5. Checks:
   - **C1:** the mask's box overlaps Gemini's box with IoU ≥ 0.6. This catches a wrong object.
   - **C2:** mask area is plausible, the mask is one main connected piece, and it doesn't leak to the page edges.
   - **C3:** a model from a different family (Claude) sees only the L1 render and chooses between the target and *the page's own other objects*.
   - **C4:** if L1 isn't recognized but L2 is, fall back to L2 automatically.
   - Any failure or flag shows a **"teacher review" card**.
6. A "show your work" toggle overlays the Gemini box and mask outline on the original page. This is grafted from Receipts' provenance idea.

**Evidence:** 20 hand-boxed real StoryWeaver pages, reported as accepted/flagged/failed counts (for example, "14 / 4 / 2 of 20"). ARIA becomes a unit test for mask math and the L1 recolor, and the slide says it isn't evidence on illustrations.

**Demo (Judge's 2-min script):**
- Hold up a hand-cut, hand-recolored page next to a blank tablet.
- Give one CVI sentence, then the busy page becomes Maya's red object on black.
- Switch to Leo instantly, then move the dial from L1 to L3.
- The judge picks a book from a shelf of 5–8 pre-tested books, then turn on the mask overlay.
- Show a flagged "teacher review" page and present it as a feature.
- End on the evidence slide with denominators, a practitioner quote or "no user validation yet," and the honest-limits box.

## Fixes per idea (for the record)

**FocusPage (selected)**
- Rename the badge and drop all clinical language.
- Link the name to the mask through Gemini's box, and use box-overlap plus geometric sanity checks (C1–C2) as the main check.
- The verifier uses distractors taken from the same page, not random words.
- Test L1 recognizability, with automatic fallback to L2.
- Make headline evidence real illustrated pages, not ARIA.
- Build L1–L3 first. Cut phone photo, print, SAVOIAS, L4, and MongoDB beyond profiles.
- Use a curated book shelf, cached outputs, and a recorded fallback video.
- Open the pitch with the hand-cut page.
- Make the "Google engineer CVI app" (Szalapski's *Bubbly*, which outlines text, not illustrations) a reference and possible contact.
- Note that CVI Book Nook and APH sequences offer pre-adapted material, so "no competitors" is too strong.

**Crosscheck (fallback)**
- Ban "confirmed."
- Use three output states: *disagree → retake* / *agree + OCR exact token → "readers agree"* / *agree but OCR missing → "couldn't confirm, retake"*. OCR alone never triggers "disagree."
- Match tokens on word boundaries and units, so "10" doesn't match "100."
- Set a false-alarm budget of at most 2 of 20 clean photos.
- The gate must show both errors and catches: at least 3 silent errors and at least 2 flagged.
- Test lookalike names, once/twice, mg/mcg, and refills, not just 10 vs 40.
- Add a same-model rotated re-read witness and an abstention curve.
- Drop the Most Secure claim, since photos go to two cloud vendors. Strip EXIF and show a consent line.
- Add a "prototype, not medical advice" banner and cache the demo bottles.

**Receipts (dropped)**
- Drop "first" and pitch the audit trail.
- Check in hour 1 whether EddyVerify handles non-standard transcripts; if it does, kill the idea.
- One screen, one JSON preset, math in code, click-to-source-pixel provenance.
- Use 20 programmatically generated fake transcripts.
- Skip the international wedge, because foreign grade conversion carries ethics and bias risk.

**LectureLens (dropped)**
- One-hour kill test: compare stock, hand-typed keyterms, and the syllabus glossary on both clean and hard audio. Need a gap of at least 10 TER points (term error rate).
- Disclose how hard clips were sourced, to avoid looking cherry-picked.
- Allow corrections only near glossary terms, show a dotted underline, and count false corrections.
- Build on vendor keyterms and say so on stage.
- Pitch it as "captions that show uncertainty about course terms."

## Unresolved Risks

- **Segmentation on painted or textured art** is untested. Everyone's top risk; only the gate resolves it.
- **Thin end-to-end build:** without a one-book slice by H8, the project may not come together.
- **No practitioner reply** is likely on a weekend.
- **Unverified figures** ("leading cause," "90% fatigue") could be caught by a judge's quick search.
- **Copyright** of adapted commercial books is still unaddressed. StoryWeaver's CC-BY license sidesteps it for the demo.

## Debate Highlights

- **Receipts' advocate disproved their own headline claim** in round 1 by finding EddyVerify, then dropped to 2/10.
- **The Critic reversed course** in round 2: they first called FocusPage "least risky," then downgraded it because the judge-picks-any-book demo was the most fragile live move and rembg doesn't know which object Gemini named. The advocates' fix (Gemini's box links the name to the mask) won the Critic back in round 3.
- **The Crosscheck advocate conceded** that their own gate was too easy ("errors exist ≠ we catch them") and made it harder.
- **The LectureLens advocate withdrew** the adversarial benchmark as cherry-picked.
- **Cross-pollination:** Receipts' provenance became FocusPage's mask overlay. LectureLens's dotted underline became the flagged-page card. Crosscheck's "abstain loudly" became flag-don't-force.

## Full Transcript

- Structured transcript: `active/chatroom/chat.json`
- Per-agent responses: `active/chatroom/r{1,2,3}_{A..F}.md`
- Moderator briefs: `round2_brief.md`, `round3_brief.md`
- Idea write-ups: `ideas.md`
