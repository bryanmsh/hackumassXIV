RULINGS:
#1 FocusPage still beats Crosscheck, narrowly, but only after the Critic's pipeline fix is adopted. The Critic is right that multiple-choice verification is weak evidence, so it is demoted to a secondary badge. Minimal buildable pipeline:
- Gemini returns a named subject plus a bounding box in one call (box output is native, so no separate grounding step).
- Run rembg/SAM on the box crop only. This links the name to the mask without a new integration.
- Mask sanity gate: the mask must fill 15-90% of the box and be one connected blob. Otherwise the page is flagged "teacher review" and never forced.
- L1 is a luminance-preserving tint, not a flat fill, so shading survives. If L1 fails the recognition check, fall back to L2.
- Fallback with no segmentation: the box outline is L4.
- The ARIA test only measures photo segmentation. Say so on the slide. The headline evidence is 10-15 hand-checked illustrated pages, with counts and denominators.
Crosscheck's rebuttals are honest but don't change the order. Its demo depends on glare producing silent errors, which may not exist, and its privacy and Most Secure claims are dead (two cloud vendors). FocusPage's failure mode is visible and teacher-rejectable. Crosscheck's is a medication harm story.

#2 Crosscheck's response is adequate but leaves it a conditional product. Drop "Most Secure." Ban the word "confirmed." Add the cached fallback video. It remains the right pivot, not the right first bet.

#3 Commit to FocusPage now. Do not run a dual build gate. The "7 of 10 real pages" test is the only gate, and it runs in hours 1-4 with three people. One person spends about 60 minutes on a Crosscheck 15-photo smoke test, purely as insurance. If FocusPage fails the 7/10 test by Friday hour ~5, pivot to Crosscheck, with Saturday midday as too late to switch. Dual gating burns roughly 25% of the hours before the first line of product code.

FINAL PICK: FocusPage. Scope: Gemini name plus box, cutout, L1-L3, two child profiles, a curated shelf of 5-8 pre-tested books, a flag-don't-force confidence card, and a show-your-work mask overlay. Badge text: "object still recognizable (machine check)."

WINNING DEMO SCRIPT (about 2 minutes)
0:00-0:15 Hold up a hand-cut, hand-recolored book page next to a blank tablet. "A teacher spent an evening on this one page."
0:15-0:35 One-sentence CVI explanation. Load a busy picture-book page. It collapses to one red object on black in about 1 second. Say "Maya, Phase I, red."
0:35-0:55 Switch to Leo (yellow and blue, Phase II). The same cached cutout regenerates instantly. Slide the dial L1 to L3.
0:55-1:20 The judge picks any book from the shelf of 5-8. Pages adapt live from cache. Toggle the mask overlay to show the work.
1:20-1:40 Show a flagged page (multi-object or text in the art) with the card "unsure, teacher review." Present it as a feature.
1:40-2:00 Evidence slide: "recognizable on X of N pages" with denominators, one rejected example, the practitioner quote or "no practitioner reached," and the honest-limits box ("no children tested, not clinical").

WHAT LOSES IT:
1. Segmentation quality on painted or textured pages. A cutout that looks wrong in front of a judge undercuts everything.
2. Overclaiming. Clinical-sounding words, "verified," or unchecked figures (90%, the leading-cause claim) will get caught by a judge's quick search.
3. No practitioner voice, plus a fragile live demo on an untested book. Mitigate with the shelf and a recorded fallback video.

CONFIDENCE: 6/10
