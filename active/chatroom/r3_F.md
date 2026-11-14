CONCESSIONS:
- My dual gate as written (about 6 hours) was too expensive. D's one-hour kill-test habit and A's pre-committed switch trigger show a gate must cost about 2 hours, not an evening.
- A beat me on the mask-box point once scoped properly. Gemini returns a box for the named subject, and SAM or rembg runs inside that box. That is one integration step, not an unbudgeted pipeline. Mask-to-box overlap becomes the automated check.
- B beat me on "OCR cries wolf". That is a measurable false-alarm rate, not a fatal flaw. Reporting it beside the catch rate is stronger than hiding it.
- E and A were right that a curated shelf of 8 pre-tested books, with L1-L3 only, takes away most of the live-demo risk I raised.

PRE-MORTEM (FocusPage chosen, and it loses):
1. Pipeline looks bad on real art. Painted or textured pages give ragged masks, and L1 single-hue recoloring wrecks recognizability. Cheapest prevention: the gate below, plus a shelf of only pre-tested books with cached outputs, and L2 (real colors on a plain background) as the default look. Show the mask overlay.
2. No end-to-end build by Saturday afternoon. Segmentation, verifier, clutter, ARIA eval and profiles all compete for time. Prevention: a thin hard-coded slice (one book, ingest to viewer) by hour 8. Cut order: L4, phone photo, SAVOIAS, MongoDB beyond profiles. Cache the demo path and record a video fallback.
3. Judges read it as "rembg plus a recolor, never tried on a child." Prevention: open with a hand-cut book beside the output. Report ARIA retention with denominators. Include one rejected-page card. Badge text is "object still recognizable (machine check)." Put either a practitioner quote or an explicit "no user validation yet" on a slide.

DECISION RULE + TIMELINE (hour 0 = Friday evening kickoff):
- H0-0.5: assign two people to FocusPage (pull 10 real StoryWeaver pages: flat, painted, multi-object) and one to Crosscheck (5 bottles, 15 photos with glare, curve, blur and crop, plus ground truth). The fourth person emails a TVI and Disability Services and checks the CVI-app and Be My AI claims.
- H0.5-2.5: FocusPage runs Gemini box, then SAM or rembg inside the box, with an automated mask-overlap check. Two teammates blind-judge "correct subject cut" without tuning. Crosscheck runs Claude alone and Gemini alone and counts confident-wrong name or strength reads, plus OCR false alarms on clean photos. No UI work until H2.5.
- H2.5, hard stop. FocusPage passes at 7 of 10 or better. Crosscheck passes at 3 or more silent errors in 15.
  - FocusPage passes: build FocusPage, whatever Crosscheck did.
  - Only Crosscheck passes: build Crosscheck.
  - Both fail: build FocusPage only if at least 5 of 10 pages worked, and restrict the shelf to the page types that worked. Otherwise build Crosscheck as an abstention product and report that honestly.
- H2.5-3: write the loser's result into the slide-deck notes, write the 3-sentence pitch, and set up the repo.
- H3-8: ingest, subject and box, cutout cache, L2 and L1 render, fullscreen viewer, thin end-to-end on one book by H8. One person writes the ARIA eval script in parallel.
- Saturday-midday switch to Crosscheck is allowed only if its gate already passed. Otherwise don't switch, narrow the scope.

FINAL VERDICT: FocusPage, conditional on the 2.5-hour gate. Receipts and LectureLens are out. Do not build a merged product. Graft Receipts' click-to-source provenance as the mask-overlay "show your work" view, and LectureLens' dotted-underline idea as the flagged-page card.

CONFIDENCE: 7
