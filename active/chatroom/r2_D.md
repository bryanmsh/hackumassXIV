AGREEMENTS:
- The Critic (F) is right on the strongest point against me: vendors already ship custom vocabulary (Otter since 2019, Verbit, Panopto admin dictionaries, Deepgram and AssemblyAI keyterms). My own R1 admitted boosting is a commodity. The only novel slice is auto-building the glossary from a syllabus plus measuring the result. That is a thin Innovation story, and the Judge's 5/10 is fair.
- The Critic is also right that modern ASR may already get "heap" and "stack" right, so a demo could show no visible gap. I cannot claim a gap I have not measured.
- Judge (E) and Advocate A are right that FocusPage has the more memorable demo. A two-pane text comparison in a loud hall is the least visual of the four, and a live mic is fragile.
- Advocate C (Receipts) already conceded that "first" is false, and I agree the Receipts headline claim has the worst structural problem.
- Advocate B's point that a rerunnable `make eval` is strong evidence applies equally to my benchmark; that is where we are equal.

DISAGREEMENTS:
- The Critic frames the problem as "the gain may be small." That is empirical, not fatal, and it is testable in about an hour. Run stock Deepgram or AssemblyAI on a dense rare-term clip (Dijkstra, Kruskal, amortized, heapify), with a non-native speaker and some noise, and see. If the baseline already scores well, I drop the idea. No other idea has a kill test this cheap.
- Advocate A calls LectureLens the weakest on demo legibility. Partly fair, but a pre-recorded noisy clip played from a laptop is deterministic and removes the live-mic risk. The judge can still speak a term to a second live pane.
- I do not accept Advocate B's claim that "stakes" decide it. Captions for Deaf students are a real access barrier, but I concede B's medication stakes are higher.

REFINED PROPOSAL:
Reframe it as "captions that show their uncertainty about course terms," not "better ASR." Concretely:
1. Gate first: a one-hour baseline test on hard audio before any UI is built. Pass if term error rate (TER) is at least 10 points worse than boosted. Otherwise abandon.
2. Build on the vendor keyterm parameter and say so on stage. The contribution is the syllabus-to-glossary extraction, TER measurement, and a constrained, phonetic-distance correction pass that shows a dotted underline on low-confidence fixes, with the false-correction count reported.
3. Answer moderator Q3 directly: the gain is visible only on adversarial audio, so the demo must use it, and I should state that on the results slide.
4. Q4 (shared uncertainty thread): it is a real improvement only if it ships as a measurable feature (dotted underline plus counts), not only as pitch language.
5. Q5 (outreach): email UMass Disability Services and one Deaf/HoH student Friday night for a one-sentence reaction.

FIXES UPDATE:
- LectureLens: (a) hour-2 kill test; (b) adversarial benchmark with TER and false corrections; (c) correction limited to glossary-near substitutions with confidence scores; (d) cut tap-for-definition and true streaming; (e) a pre-recorded fallback clip; (f) a quoted Deaf/HoH reaction.
- Add to FocusPage: pre-adapt five books and keep the machine-check badge wording ("recognizable by machine check", never "verified safe"). The Critic's wording fix is right.
- Add to Crosscheck: borrow my kill-test habit. Run single-model baselines on glared labels in hour 2 and confirm that silent errors exist at all before building the UI.

IF NOT MY IDEA:
FocusPage. Its demo is the clearest and its competition is manual only. The risk of the heavy build is mitigated by cached cutouts and by cutting L4 and phone input. Crosscheck is a close second, and I would switch to it if the ARIA segmentation test fails.

CONFIDENCE: 3/10 that LectureLens should be the team's pick. It has the lowest build risk but the weakest Innovation and demo impact, and I would only pick it if the hour-2 test shows a large visible gap.
