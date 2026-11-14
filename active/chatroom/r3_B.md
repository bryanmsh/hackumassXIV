AGREEMENTS:
- Critic: a strong VLM may read a glared bottle correctly. If so, Crosscheck has no demo and no pitch. Only a measurement can settle it, and I will not argue it away.
- Critic: the Most Secure claim is dead. Photos go to two cloud vendors, so "privacy-first" contradicts the design. I withdraw that track.
- Critic: OCR failing on exactly the glared photos could make the app cry wolf. That is a design flaw and I am fixing it below.
- Dual gate (#3): realistic for a team of 3-4, if each gate is timeboxed and its decision rule is written down before anyone runs it. I accept the Critic's tiebreak: if both gates pass, FocusPage wins.

DISAGREEMENTS:
- Critic's gate is too easy to pass. "3 silent errors from one model on 15 photos" proves a problem exists, not that Crosscheck solves it. Three errors the ensemble also misses would be a failed product. The gate must include the catch rate.
- "Zero silent errors" is only about strength. Lookalike drug names (hydroxyzine/hydralazine), "once" vs "twice" in directions, mg vs mcg and refill counts also fail silently. The 15 photos must cover all of these, not only 10 vs 40.
- "Gate fails, pivot to FocusPage" is cleaner than my earlier "5/10 coin flip" suggested. I won't claim Crosscheck is the better build. I claim it has the cheaper, faster gate.

FINAL DESIGN CHANGES:
1. Harder test set, disclosed. Stack the degradations (specular glare across the strength, cylinder wrap, small print, rotation, a crop cutting a digit). Run the model a phone app would actually use for latency (a fast tier) as well as the flagship, and report both. Do not hide which tier was used.
2. OCR cannot veto alone. Use three states. Readers disagree: "readers disagree, retake". Readers agree and the OCR contains the exact strength token, matched with word boundaries and unit awareness ("10" must not match "100"): "readers agree". Readers agree but the OCR is missing or garbled: "readers agree, but the text scan couldn't confirm, retake". OCR failure alone never produces "disagree". That removes the main source of false alarms.
3. Pre-registered false-alarm budget: no more than 2 flagged out of 20 clean photos. Report the count with its denominator.
4. Privacy, stated narrowly: "we store nothing." Photos go to two vendors under zero-retention API terms. Strip EXIF and show a consent line before the first send. Say plainly that on-device is the real fix and is future work. Demo on fake-name labels only. Do not submit for Most Secure.
5. Cached demo bottles plus a recorded fallback video, because of the network dependency.

FINAL VERDICT: Run both gates in parallel, two people each, hard stop at hour 6. Both are throwaway code.
- Crosscheck passes only if (a) a single model makes at least 3 silent errors on 15 degraded photos, (b) the ensemble flags at least 2 of them, and (c) the false-alarm budget in change 3 holds on clean photos.
- FocusPage passes at 7 of 10 real illustrated pages, per the Critic.
- Both pass: FocusPage. Only one passes: that one. Neither passes: run LectureLens's baseline gate, and Receipts is last.
- Nobody reopens the decision after hour 6.

CONFIDENCE: 5/10. If both gates pass, my own verdict is that FocusPage wins, so this number is mostly the chance that Crosscheck passes and FocusPage doesn't.
