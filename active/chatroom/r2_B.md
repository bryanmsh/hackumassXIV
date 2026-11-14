AGREEMENTS:
- Critic (F): "confirmed" is the most dangerous word in my app. It is gone. Outputs are "readers agree," "readers disagree," or "can't read this," always followed by "check with your pharmacist." F's hard rule is adopted: if the OCR witness lacks the strength string, the app never says "agree."
- Critic (F): three live network dependencies can kill a 60-second demo. We need cached responses for the demo bottles plus a recorded fallback video.
- Judge (E): Innovation is my weak column. Multi-model agreement is a known pattern, so I won't claim novelty for it. The contribution is applying it per-field to a safety-critical label, with a measured silent-error count.
- Advocate A: a spoken sentence is hard to show a room. Fair.
- Advocate C and F: Receipts' "first" claim is dead (EddyVerify). Drop it. LectureLens is gated on a Friday-night baseline.
- Moderator Q4: "AI that shows its uncertainty" is pitch fluff as a merge. It is only real as a design principle: abstain loudly. Don't build a combined product.

DISAGREEMENTS:
- Strongest counterargument (Critic F, plus Judge E's Innovation 6): correlated errors plus harm potential. If Claude and Gemini misread the same glared label, the app is dangerous and the pitch deflates. I agree with the risk but not that it is "fatal-if-unfixed." It is measurable by Saturday. That is what the benchmark is for. If silent errors survive the ensemble, we report them. "N confident-wrong reads, X flagged, Y agreed-but-wrong" is a more credible slide than any of the other three ideas can produce.
- Moderator Q1: I accept that FocusPage is the lower-risk build. But "least risky" partly means "least testable." Its core claim (that a child with CVI can process the page) has no ground truth at all. Crosscheck's claim is falsifiable in hours.
- Advocate A on demo legibility: fixable. The demo screen shows large color-coded fields (green "readers agree," amber "readers disagree") alongside the audio. Side by side, Model A alone says "40 mg" confidently and Crosscheck flags it. The visual is a verdict, not a table.
- Judge E's FocusPage lead of 2 points is inside the noise. FocusPage is also the heaviest build by E's own admission.

REFINED PROPOSAL:
1. Kill gate, Friday night (hour ~8): run about 15 degraded photos through each model alone. If neither model makes a confident-wrong read, there is no demo. Pivot to FocusPage and don't sink the weekend.
2. Add a fourth, cheap witness: the same model re-read on a rotated or cropped image. It fails differently from cross-model disagreement and counters correlation.
3. Add an abstention curve: report coverage against wrong-answer rate. If correlation is high, the honest result is "the app abstains more," which is still useful.
4. Pre-register the headline metric before building: "of N single-model confident-wrong strength reads, the ensemble flagged X, with Y false alarms in M clean reads."
5. Outreach (Q5): Friday email to UMass Disability Services and one local blind-services org. Test the whole flow on VoiceOver and write down every friction. If no reply, put "not user-tested; limitation" on the slide.

FIXES UPDATE:
- Wording: never "confirmed" or "verified." Always "readers agree," plus a pharmacist line.
- Hard OCR rule on the strength string.
- Check Be My AI and Seeing AI release notes in hour 1. Don't claim "none do this" without checking.
- Report raw counts with denominators, plus the agreed-but-wrong cases.
- Cached demo bottles, a video fallback, and a "prototype, not medical advice" banner.
- Cut order: re-take guidance, openFDA, eval dashboard UI. The OCR witness is cut last.
- Add to FocusPage: Crosscheck's different-family verifier with distractor choice. Flagged pages shown as "unsure" are a feature, not a gap.
- Add to LectureLens: the Friday baseline gate (under about 10 points of term error rate means pivot).

IF NOT MY IDEA: FocusPage. It has the thinnest competition, a demo that is visual and fast thanks to cached cutouts, and a clear accessibility story. It needs a practitioner quote and a retitled badge ("object still recognizable (machine check)"). I would switch to it if my Friday gate fails.

CONFIDENCE: 5/10. A coin flip with FocusPage. The Friday gate is the tiebreaker, and the team should run it before committing.
