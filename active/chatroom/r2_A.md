AGREEMENTS:
- Critic (F), strongest counterargument: the self-check is circular and "verified" reads as a clinical claim. A vision model saying "still a dog" says nothing about whether a child with CVI can process the page. Conceded in full. The badge becomes "object still recognizable (machine check)". We never write "safe" or "CVI-approved". The verifier is a different model family and picks from distractors instead of free-naming. Calling it "verified" was my overreach.
- Judge (E): FocusPage is the heaviest build (Gemini, segmentation, verifier, clutter metric, eval), and my "most buildable" claim was too strong. Crosscheck is the safer 36h build. Pipeline stages are API calls, but integration and segmentation failure on stylized art are real risks.
- Crosscheck advocate (B): the verification step is invisible on screen. True, and I will make it visible (see proposal).
- LectureLens advocate (D): a child's recognition can't be shown in the room. True. We show retention and clutter numbers instead, and say plainly that this is not a clinical outcome.
- Receipts advocate (C) and Critic (F): Receipts' "first" claim is dead. Receipts should drop out unless it takes the international-transcript wedge.
- Crosscheck's "correlated errors plus medication harm" risk is structural, and I accept the Critic's ranking of risk. The Critic's own conclusion (FocusPage is least risky, no safety-critical output) cuts in our favor.
- E's mind-changer is fair: if ARIA segmentation or retention fails by Saturday midday, we switch to Crosscheck.

DISAGREEMENTS:
- F's claim that "clutter decreases monotonically" is trivially satisfiable. Partly agree, so I demote it. The headline claim is object retention on 200 ARIA objects pasted on clutter (IoU plus recognition), where ground truth is free. Clutter reduction is a sanity check only.
- B says Crosscheck's demo is stronger because the judge picks a bottle. Wifi risk and glare variance make a live photo fragile, a point F made against Crosscheck. FocusPage's cached cutouts make the judge-picks-a-book demo latency-proof. A wrong answer in a med-label demo is also a safety story, while a bad cutout is merely visible and teacher-rejectable.
- D and B call FocusPage's payoff invisible. It is the most visible of the four. A busy page collapses to one red object on black, then flips to another child's profile. That demos in 5 seconds, with no explanation of CVI phases beyond one slide.

REFINED PROPOSAL:
Scope down to demo-critical and make uncertainty visible, the best merge from the debate.
- Core: StoryWeaver/PDF ingest, Gemini subject naming, cached cutout, levels L1-L3 (L4 only if time), two child profiles, fullscreen viewer with teacher approve.
- Borrowed from Crosscheck: the "machine check" shows a confidence state per page (recognizable / uncertain / multi-object, teacher review). A flagged page becomes a feature, not a gap. Multi-object and text-in-art pages are flagged, not forced.
- Evidence slide: ARIA retention counts with denominators (for example "recognized on 171 of 200"), one rejected example, and an honest-limits box.
- Pitch opens with a hand-cut, hand-recolored book beside the output.
- Pre-adapt 5 tested books. Keep the live path for a judge's pick, but only on books from a pre-tested list.
- Cut: phone photo, print, login, SAVOIAS, MongoDB beyond profiles.

FIXES UPDATE:
FocusPage: (1) rename the badge, no clinical wording; (2) cross-family verifier with distractors; (3) email a TVI (Perkins, Anchor Center, UMass SPED) on Friday and quote them, or state "no practitioner reached" on the slide; (4) retention counts as the headline, clutter as a sanity check; (5) L1-L3 first; (6) flag, don't force, multi-object pages; (7) verify the leading-cause and 90% figures and the Google-engineer lead in hour 1.
For others: Crosscheck needs the ban on the word "confirmed" plus a cached video fallback. LectureLens needs a baseline test on real speakers by Friday night. Receipts needs the wedge or it should drop.

IF NOT MY IDEA:
Crosscheck. It has the tightest measured claim, MedTech access, and two sponsors, and it is the safest build. It loses to FocusPage only on Innovation and live-photo fragility.

CONFIDENCE: 7/10. The Critic's circularity point is fixable by wording and the visible uncertainty feature. The residual risk is segmentation quality, which a midday Saturday ARIA test resolves.
