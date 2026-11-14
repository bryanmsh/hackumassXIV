AGREEMENTS:
- The Critic (F) is right that "first to cross-check" is dead. EddyVerify markets exactly that. I put "first" in the pitch line, and a judge could falsify it in one search. Drop it.
- The Judge (E) is right that Receipts scores lowest on Innovation (4). Its prize list is also fair: I can't defend Most Impactful AI or Most Secure for a fake-data transcript tool. Best case is Gemini and maybe MongoDB.
- F is right that fake-only data weakens any accuracy claim. A benchmark on transcripts we generate ourselves proves less than Crosscheck's photos of real bottles.
- A is right that Receipts' payoff is a table diff. My round 1 claim that "no domain explanation" makes it the strongest demo was too generous. Easy to understand is not the same as memorable.
- Scope: in 36 hours, two portals plus a rules engine can't be built. I already conceded that.

DISAGREEMENTS:
- I only partly accept "most risky" (F). Receipts' risk is commercial: slow sales, FERPA, who pays. Hackathon judges don't score that. Its build risk is the lowest of the four, because the core is extraction, a diff and Python math, and it degrades gracefully. F is right about hackathon risk, which is the risk of not winning. On that measure it is the weakest.
- A is wrong that judges "have seen" Slate or EdVisorly demos. Judges ask "doesn't X do this?" because the answer is a one-search lookup. That is a credibility problem, not a familiarity problem.
- I'd push back on E giving Presentation only 6. The click-to-trace receipt (click a GPA, see the source rows and the pixel region) is a good UI moment. It is a feature, not an idea.

REFINED PROPOSAL:
I don't have a pivot that wins. The most defensible version is "Receipts for non-standard transcripts": one screen, one JSON preset, a non-US grade scale, and every GPA click-traces to a highlighted region of the source. Its weak points are that I haven't verified EdVisorly or Parchment fail on international transcripts, and that without real transcripts I can't prove we do better. So this is a pitch wedge, not evidence. I wouldn't bet the weekend on it.
The component worth keeping is provenance: every extracted value links to the pixel region it came from. That is a strong feature for another idea.

FIXES UPDATE:
Receipts, if chosen:
1. Drop "first." Pitch the audit trail.
2. One screen, no student portal, one preset.
3. Check in hour 1 whether EddyVerify handles international or non-standard transcripts. If it does, kill the idea.
4. Generate 20 fake transcripts programmatically in varied layouts, so ground truth is exact.
5. Report field accuracy as counts.
For other ideas:
- Crosscheck: show the bounding box where each field was read. This makes disagreement legible on screen. It also gives the judge something to see, which E noted was Crosscheck's weakness.
- Crosscheck and FocusPage: generate mock labels or test pages programmatically for exact ground truth, as Receipts' benchmark would.
- FocusPage: add a mask or cutout overlay "show your work" view, so the verified badge is not a black box.

IF NOT MY IDEA:
FocusPage, as the Judge and Critic both rank it first (E 39, F least risky), with a hard checkpoint: the ARIA IoU test by Saturday midday. If it fails, switch to Crosscheck. Merging into Crosscheck is reasonable only if the team accepts that the reconciler and "say when unsure" framing is the product, and cites Be My AI only after the release-notes check.

CONFIDENCE: 2/10 that Receipts should be the pick.
