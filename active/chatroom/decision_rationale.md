# Why FocusPage? The reasoning behind the pick

*From a 6-agent debate (4 idea advocates, a hackathon judge and a critic), 3 rounds, 2026-11-13.*

## The decision in one paragraph

All six agents converged on **FocusPage**. The two advocates for the ideas that were dropped (Receipts, LectureLens) did too. It won because it is the only idea that is new, visual, and fails safely at the same time. A judge sees a busy picture-book page turn into one clear object in a child's favorite color, then switch to another child's version instantly. Nobody at the table has seen that before. When the AI gets a page wrong, the result is a visibly bad cutout that a teacher rejects, not a dangerous answer. **Crosscheck** is the fallback because it is the safest build with the tightest metric, but it depends on a premise that hasn't been checked yet. **Receipts** and **LectureLens** were eliminated because their core novelty claims didn't survive fact-checking.

---

## Reason 1: It's the only idea where judges will say "I haven't seen that"

Innovation was the deciding criterion, and FocusPage was the only idea whose novelty claim held up when the agents searched.

| Idea | What the debate found about novelty |
|---|---|
| **FocusPage** | No AI tool found that automatically adapts *real books* for CVI. Existing options are manual or fixed content: Vision Nanny, the APH CVI Complexity Sequences, the Paths to Literacy Book Builder, and pre-adapted material from CVI Book Nook and Little Bear Sees. The closest lead, a Google engineer's CVI app (Szalapski's *Bubbly*), outlines **text**, not illustrations. |
| Crosscheck | Asking several AI models and comparing answers is a well-known technique. The Judge scored Innovation 6/10. The claim that "Be My AI or Seeing AI don't report confidence" couldn't be confirmed either way. |
| Receipts | **Disproved.** The Receipts advocate found that EdVisorly's EddyVerify already markets cross-checking self-reported grades against official transcripts, which was Receipts' headline "first." Innovation 4–5/10. |
| LectureLens | Custom-vocabulary captioning already exists in Otter (since 2019), Verbit, Panopto, Deepgram and AssemblyAI. Only "auto-build the glossary from a syllabus" is new, and the Critic noted an LLM does that trivially. Innovation 5/10. |

The Judge also argued that FocusPage answers the "AI wrapper" objection. Cutting each object out once, caching it, and re-rendering per child is real engineering, not a single prompt.

## Reason 2: It has the most memorable demo

The Judge gave FocusPage the top demo-memorability score (9/10) in every round. Each idea's payoff is something different to look at:

- **FocusPage:** a cluttered page becomes one red object on black. Switch to "Leo" and the same page appears in yellow and blue at a different level, instantly. Visual, fast, and understandable without much explanation.
- **Crosscheck:** the result is mostly a spoken sentence, which is hard to show to a room (the FocusPage advocate's point, which the Crosscheck advocate conceded).
- **Receipts:** a table with red cells. Easy to understand, but as the Receipts advocate admitted, "easy to understand is not the same as memorable."
- **LectureLens:** two panes of text. The gain may be invisible on clean audio, and a live mic in a loud hall is fragile.

Because the cutouts are cached, switching between children and levels is effectively instant, so the most impressive part of the demo is also the part least likely to lag.

## Reason 3: When it fails, it fails safely

This argument moved the Judge and the Critic away from Crosscheck.

- **FocusPage's failure mode is a bad cutout.** It is visible, the teacher approves every page anyway, and flagged pages get a "teacher review" card. Nothing harmful reaches a child.
- **Crosscheck's failure mode is a medication harm story.** If Claude and Gemini both misread the same glared label, the app says "readers agree" and a blind user may take the wrong dose. The Critic called "confirmed" "the most dangerous word in the app." Careful wording reduces this risk but can't remove it, and a judge can raise it.

The Critic ranked FocusPage *least risky* in round 1, while noting it has no safety-critical output and no AI incumbent.

## Reason 4: Its biggest weaknesses turned out to be fixable

FocusPage took the hardest attacks of the debate, and the agents found concrete answers to each.

| Attack (from) | Fix that resolved it |
|---|---|
| "The self-check is circular. A vision model saying 'still a dog' says nothing about whether a child with CVI can see it, and 'verified' reads as a clinical claim." (Critic, R1) | Rename the badge to **"object still recognizable (machine check)"**. Never say "verified," "safe," or "CVI-approved." State openly that it is not a clinical result. |
| "A multiple-choice verifier passes almost any clean cutout." (Critic, R2) | Make the **main check geometric**: the cutout must line up with the box Gemini drew around the named object, which catches a wrong object, and must have a plausible size and shape. The verifier becomes secondary and chooses between the target and the page's *own other objects*, not random words. |
| "The background-removal tool (rembg) cuts out whatever stands out most, not the object Gemini named, and linking them isn't budgeted." (Critic, R2) | Gemini returns the object's **name and a box in one call**, and the page is cropped to that box before cutting. The box forces the right object, so no extra integration is needed. |
| "Recoloring a multicolored object to one hue may destroy recognizability." (Critic, R2) | Level 1 becomes a **tint that keeps the shading**. If it isn't recognized, the page **falls back to Level 2 automatically** (real colors on a plain background). |
| "The ARIA test uses photos, not illustrations." (Critic, R2) | The headline evidence becomes **20 real StoryWeaver pages**, reported as counts (e.g. "14 accepted / 4 flagged / 2 failed of 20"). ARIA is demoted to a unit test. |
| "Letting the judge pick *any* book is the most fragile live move of the four." (Critic, R2) | Use a **curated shelf of 5–8 pre-tested books**. The judge picks from the shelf, outputs are cached, and a recorded fallback video is ready. |

Once these were adopted, the Critic conceded the main points in round 3 and endorsed FocusPage (7/10).

## Reason 5: It meets every judging criterion without overreaching

| Criterion | Why FocusPage scores well |
|---|---|
| Innovation | A per-child complexity dial tied to CVI phases, adapt-once/serve-every-child, and a self-check. No AI competitor found. |
| Functionality | Each stage is a known tool (Gemini, rembg or SAM, Pillow), and the cache makes the demo fast. |
| Practicality | It replaces hand work teachers already do (cutting and recoloring pages). It uses free CC-BY books, and the buyers exist (district special-ed budgets, Perkins). |
| Presentation | Named child profiles, a before/after anyone can see, a "show your work" overlay, and honest counts. The demo opens with a hand-cut page next to the tablet. |

Crosscheck covers more prize tracks on paper (Accessibility, MedTech, Most Impactful AI, Claude and Gemini sponsors). But its "Most Secure" claim fell apart, because photos go to two cloud vendors, and the Judge thought FocusPage was likelier to *win* Best Accessibility outright.

---

## Why not the others

**Crosscheck: kept as the fallback, not chosen.** It was close (Judge: 38 vs 40, and the Crosscheck advocate called it a "coin flip"). It has the tightest measurable claim ("of N confident-wrong reads, the ensemble flagged X") and the most contained build. It lost on three counts:
1. **An untested premise.** If a modern model reads glared labels correctly, there are zero silent errors to catch and no demo. The Critic raised this, and the Crosscheck advocate conceded only a measurement can settle it.
2. **Harm framing.** A wrong "readers agree" on a medication label is a story judges remember for the wrong reasons.
3. **Lower innovation**, since comparing several models is a known pattern.

It stays the fallback because its gate test is cheap (15 photos, about an hour) and its build is the safest if FocusPage's segmentation fails.

**Receipts: eliminated.** Its central differentiator was false (EddyVerify), the scope was the largest (two portals plus a rules engine), fake transcripts make any accuracy claim weak, and the proposed "international transcripts" wedge turned out to be an ethics risk (automated foreign grade conversion). Its advocate ended at 2/10 and recommended FocusPage. The idea worth keeping is **"every number shows where it came from,"** which became FocusPage's "show your work" overlay.

**LectureLens: eliminated.** It was the easiest to build, but its novelty is thin, and the improvement may not be visible on clean audio. Tuning the benchmark on hard audio would look cherry-picked, a point the advocate conceded. Its advocate ended at 3/10 and recommended FocusPage. What carries over is the **set-the-pass-threshold-first, kill-test-early habit** and the **visible low-confidence marker** idea.

---

## What would change the decision

The pick is conditional on one test, run before any UI is built:

> **By hour 2.5 on Friday:** run 10 real, varied StoryWeaver pages (flat, painted, multi-object) through Gemini box → crop → rembg, with no hand-tuning. Two teammates judge each page blind.
> - **7 or more of 10** cut out the right object → build FocusPage.
> - **4–6 of 10** → spend 1 hour trying SAM 2 with the box as a prompt, then retest on 10 new pages.
> - **Still failing, and** Crosscheck's parallel smoke test found **≥3 confident misreads in 15 photos** → switch to Crosscheck.
> - **Neither passes** → ship FocusPage on a shelf limited to the page types that worked, and say so openly.

**Residual risk everyone named:** how well cutouts work on painted or textured illustrations. That is why confidence ended at 6–7/10 rather than higher. The gate exists to find out within hours instead of on Saturday afternoon.

## Final agent standings

| Agent | Final pick | Confidence |
|---|---|---|
| FocusPage advocate | FocusPage | 7/10 |
| Crosscheck advocate | FocusPage if both gates pass | 5/10 (in Crosscheck) |
| Receipts advocate | FocusPage | 6/10 |
| LectureLens advocate | FocusPage | 6/10 |
| Hackathon Judge | FocusPage | 6/10 |
| Critic | FocusPage (gated) | 7/10 |
