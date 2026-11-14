AGREEMENTS:
- Receipts' "first to cross-check" is dead (C conceded). Its structural problems (EdVisorly, fake data, scope) stand.
- Every idea needs a practitioner quote, and A, B and D all say so.
- Checks on a model's output must be deterministic where possible (B's OCR rule, C's math in code, D's constrained correction).

DISAGREEMENTS:
- A calls FocusPage "most buildable." I called it least risky in R1 and I now downgrade that. A bad cutout is visible, but the judge-picks-any-book demo is the most failure-prone live move of the four. Fix: a curated shelf of 8 pre-tested books, and the judge chooses from the shelf.
- The shared thread "AI that shows its uncertainty" is fluff as a tagline. It only counts if each app has a concrete UI element: FocusPage's rejected-page card, Crosscheck's spoken disagreement, LectureLens's dotted underline.
- E's view that Crosscheck's Most Secure case is "weak" is right, and I'd go further. Sending label photos to two cloud vendors contradicts a privacy-first pitch. Drop that claim.

FIX VERDICTS:
- FocusPage, "different-family verifier with distractors": hand-waving. A multiple-choice verifier passes almost any clean cutout. It tests whether a VLM can recognize the object, not whether the cutout is correct, and not whether a child can see it. The check that catches real failures is mask sanity: the mask's box should overlap the box Gemini grounded, and the mask's area should be plausible. Two holes A skipped:
  - rembg and U2-Net find the salient object, not "the red ball" Gemini named. Linking the name to the mask needs Gemini box output prompting SAM, which is an unbudgeted integration step.
  - My search found general-purpose rembg models are trained on photos, and there was no benchmark on children's book art. Flat, hard-edged art may be easy, but textured and painted pages are unverified. Test 10 real pages Friday night.
  - The ARIA eval uses photos pasted on clutter, so a high IoU there says little about illustrations. Also, L1 recolors a multicolored object to one hue, which may destroy recognizability. That needs testing, not assuming.
- Crosscheck, "OCR must contain the strength string": necessary, not sufficient. Substring matching has traps ("10" inside "100", the same number in a different field). OCR fails on exactly the glare and curvature cases the demo needs, so the app may say "disagree" so often it cries wolf. Report the false-alarm rate next to the catch rate. Bigger unaddressed risk: modern VLMs may read glared bottles correctly, leaving zero silent errors to catch and no demo. Test 15 degraded photos in the first hours.
- Receipts, "international transcript wedge": hand-waving. The team can't author or verify foreign grade scales, since credential evaluators disagree on conversions. Automated GPA conversion for international applicants is an ethics problem (bias, high stakes). The surviving piece is click-to-source-pixel provenance, which could merge into Crosscheck as per-field "show me where you read this."
- LectureLens, "adversarial benchmark": cherry-picking by design. Judges will read hard audio chosen to break the baseline as rigged. The fair baseline is the same ASR with a hand-typed keyterm list, which leaves "syllabus to glossary" as the only novelty, and an LLM does that trivially. It is still the weakest on Innovation.

NEW RISKS:
- A: the "Google engineer CVI app" exists. It is Tommy Szalapski's Bubbly / Roman Word Bubbling, which adds color outlines to text, not illustrations. It is not a competitor, but it is adjacent. Reference it, and he is a plausible contact.
- B: the Claude and Gemini ensemble could still produce agreed-but-wrong reads on glare, and a "readers agree" line invites over-trust.
- C: AI course classification and GPA in admissions carries disparate-impact risk.
- D: correction passes add caption lag, the problem the pitch cites.

REFINED VIEW:
Both front-runners earned the position, but neither has been tested. Run a Friday-night gate:
- FocusPage passes if the right subject is cut on at least 7 of 10 real illustrated pages without hand-tuning.
- Crosscheck passes if the single model makes at least 3 silent errors on 15 degraded photos.
- If both pass, I'd endorse FocusPage. It has a stronger demo, and its practitioner outreach is easier (TVIs and CVI parents are active online). Relabel the badge "object still recognizable (machine check)" and never say "verified."
- If only one passes, build that one.
- Receipts and LectureLens are fallbacks only.

OUTREACH (realistic):
- Offices (UMass Disability Services, Perkins, Anchor Center) are closed or slow on weekends. Don't count on them.
- Send Friday emails asking for async reactions to 3 screenshots, not calls. Expect maybe 1 reply in 5.
- More reachable: public CVI communities and parent groups, Szalapski, blind-user subreddits, the UMass blind or Deaf student orgs, and a VoiceOver user on the team or among hackers.
- Fallback: state "design follows published guidance (Roman's CVI Range, WebAIM); no user validation yet" on a slide. Honest beats invented.

CONFIDENCE: 6
