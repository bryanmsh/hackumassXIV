POSITION: Build Crosscheck, because it is the only idea whose core claim ("an AI reader that says when it might be wrong") can be proven live, on a judge's own object, with a number attached, in a domain where a wrong answer is dangerous.

WHY THIS IDEA WINS:
1. The stakes are the clearest of the four. A misread "10 mg" vs "40 mg" is a safety event, so judges grasp it in one sentence. FocusPage is touching but its success metric (a proxy for clutter) is admittedly unvalidated with CVI children. LectureLens fixes an annoyance, and the gain on clean audio may be small. Receipts is a business pitch where judges ask "doesn't Slate or EdVisorly do this?" Crosscheck's claim is a measured silent-error count.
2. It has the strongest live-demo interaction. A judge picks a real bottle and the phone speaks the result. Then glare makes a single model say "40 mg" confidently while Crosscheck says "readers disagree on strength." Receipts is mostly a table and red cells. LectureLens is two caption panes, and the judge is a spectator. FocusPage is good, but its verification step is invisible.
3. It covers the most prize tracks with a real fit, not a stretch: Accessibility, MedTech (only Crosscheck truly qualifies), Most Impactful AI, Most Secure (in-memory only, visible in the network tab), UI/UX (VoiceOver-first), plus Claude and Gemini sponsors. The two-model design uses both sponsors for a reason, not as decoration.
4. Scope is the most controllable. There is no auth, no database, no two-sided portal, and no rules engine. The ensemble is three API calls plus about 150 lines of deterministic reconciliation. Receipts has two portals and a rules engine. LectureLens needs streaming ASR plus a correction pass.
5. Its evidence is deterministic and rerunnable: `make eval` on a held-out set shows counts, not vibes.

WEAKNESSES I ADMIT:
- Correlated errors. Claude and Gemini may misread the same glared label the same way. If so, the ensemble catches little and the pitch deflates.
- No blind user consulted. This is the "disability dongle" critique, and a judge may raise it.
- Novelty is unverified. My quick search found no evidence that Be My AI or Seeing AI report per-field confidence or cross-check models, but it also found no documentation either way. Treat "none do this" as unconfirmed, not as a fact. Do not say it on stage without checking their release notes.
- openFDA only confirms a strength exists for a drug. It cannot prove the label is read correctly. Docs show `active_ingredients` with strength strings like "500 mg/1", but I verified that only via third-party pages, not the official field reference.
- A 40-60 photo benchmark is small. Rates will have wide error bars, and "silent errors caught" may be a handful of cases.
- Safety framing. If it ever says "confirmed," someone may over-trust it.

FIXES:
- Counter correlation honestly. Make the thesis "disagreement is a signal, agreement is not proof." Report the agreed-but-wrong cases in the eval as a limitation. Add the OCR witness, since it fails differently from LLMs. Include degraded inputs deliberately, and show the correlated failures rather than hide them.
- Soften the wording. Say "readers agree" instead of "verified," and always end with "confirm with your pharmacist."
- Get one blind or low-vision tester. Contact UMass Disability Services or a local blind-services group Friday, or at minimum cite AFB and WebAIM and test the whole flow with VoiceOver on a team iPhone. Pre-register this as a limitation if no one is reachable.
- Check Be My AI and Seeing AI release notes in the first hour, and reword the pitch to "we measure and flag disagreement" if either has added a similar feature.
- Report counts with the denominator, for example "caught 9 of 11 silent errors; 2 false alarms in 40," and avoid percentages.
- Use fake-name printed labels and the team's own OTC bottles only, and say so.

36H SCOPE:
Demo-critical:
- Mobile web page with a camera or upload input and an aria-live results region.
- Claude and Gemini vision calls returning the same JSON schema.
- Deterministic reconciler (normalize units, compare fields, agree/disagree).
- Spoken uncertainty sentence.
- 40-60 photo benchmark with a CSV, a held-out split labeled Saturday afternoon, and `make eval`.
- A "single model vs Crosscheck" side-by-side on a glared bottle.
Cuttable, in order:
- Re-take guidance (glare/tilt).
- openFDA check.
- OCR witness. Cut this last of the three, since it counters the correlation risk.
- Eval dashboard UI (keep the CLI output).
Never cut: two-model reconciliation, spoken uncertainty, eval numbers, and the VoiceOver walkthrough.
