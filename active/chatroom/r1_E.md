SCORECARD (1-10; total is the sum of all five columns, max 50)

| Idea | Innovation | Functionality | Practicality | Presentation | Demo memorability | Total |
|---|---|---|---|---|---|---|
| A: FocusPage | 8 | 7 | 7 | 8 | 9 | 39 |
| B: Crosscheck | 6 | 8 | 7 | 8 | 8 | 37 |
| C: Receipts | 4 | 6 | 7 | 6 | 6 | 29 |
| D: LectureLens | 5 | 7 | 6 | 7 | 6 | 31 |

Notes behind the numbers: FocusPage is the only one where a judge says "I haven't seen that." The cutout cache with a per-child dial is a real system, not a prompt. Crosscheck has the cleanest measured claim ("N silent errors, X caught"), but multi-model agreement is a known pattern. Receipts is the weakest on Innovation because EdVisorly and Parchment already exist, and its scope is the largest. LectureLens's gain on clean audio may be small, and a live ASR demo in a loud hall is fragile.

CREDIBLE PRIZES (can win, not merely enter)
- FocusPage: Best Accessibility (strong contender), Best UI/UX, Gemini sponsor. Most Impactful AI is plausible. MongoDB is a stretch (profile storage only). Best Overall is a long shot unless the demo lands perfectly.
- Crosscheck: Best Accessibility, MedTech, Most Impactful AI, and the Claude and Gemini sponsor prizes (it uses both). Best Overall is plausible. Most Secure is weak: "we don't store anything" is a claim, not a security design.
- Receipts: Gemini sponsor and maybe MongoDB. Most Impactful AI and Most Secure are not credible. It would enter many categories and win none.
- LectureLens: Best Accessibility, Best Software Hack, and Best UMass Hack (only with real CICS syllabi). Most Impactful AI is possible if the numbers are dramatic.

TOP FIX PER IDEA
- FocusPage: Get one real TVI or CVI professional (Perkins, Anchor Center, a UMass special-ed contact) to look at about 5 adapted pages and give one sentence of feedback. Put it on the slide. "No CVI children tested" is survivable, but "no practitioner has seen this" is not. Also cut scope to L1-L3 if the L4 outline is eating time.
- Crosscheck: Lock the headline metric before building the UI: "of N confident-but-wrong reads by the single model, the ensemble flagged X, with Y false alarms." Spend one hour with a VoiceOver user. That answers both the correlated-error and "disability dongle" critiques.
- Receipts: Cut it to the single moment that wins: the self-report vs. transcript diff with a GPA that shows its work. Drop the student portal and the rules engine. Add a wedge, such as international transcripts, so "doesn't Slate do this?" has an answer.
- LectureLens: Use hard audio (accented speakers, a noisy room, dense vocabulary) so the baseline visibly fails. Report term error rate, including false corrections. A visibly broken baseline is the whole demo.

CURRENT PICK
FocusPage, narrowly over Crosscheck. At a table, I remember the judge picking a book, watching it adapt live, seeing a "verified: still recognized as dog" badge, and then seeing a page get rejected. That is a visual, interactive demo with a self-checking mechanism, and the CVI niche is specific enough to feel real instead of generic "AI for accessibility." The cached cutout and the complexity dial are real engineering beyond an API call, which answers the "AI wrapper" objection. Its weakness is the lack of validation: the clutter metric is only a proxy, and no children were tested. It is also the heaviest build (Gemini, segmentation, a second vision model, a clutter metric, an evaluation), so the scope risk is real. Crosscheck is the safer 36-hour build with the tighter metric, and it loses mainly on Innovation and on live-photo fragility. Receipts and LectureLens trail clearly. Merge note: both A and B rely on "a second model checks the first," so that idea can be a shared thread in the pitch.

WHAT WOULD CHANGE MY MIND
If FocusPage segmentation and recognition retention fail on the 200-object ARIA test by Saturday midday, or no practitioner will give feedback, I would switch to Crosscheck.
