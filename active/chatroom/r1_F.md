**FATAL-IF-UNFIXED**

- **FocusPage:** The self-check is circular. A vision model confirming "still a dog" tells you nothing about whether a child with CVI can process the page, and the write-up admits no CVI child was tested. Judges and TVIs will read "verified" as a clinical claim. Fix: rename the badge "object still recognizable (machine check)" and never say "safe" or "CVI-approved". Get one TVI, or the Perkins or CVI Book Nook community, to react to the output before Sunday. Keep the 2-minute demo on the cached-cutout speed and the L1-L4 dial, and drop the live photo-of-a-page path unless it is rock solid.
- **Crosscheck:** Correlated errors plus a medication-harm framing. If Claude and Gemini both misread the same glared label, the screen says "two readers agree" and the user takes the wrong dose. "Confirmed" is the most dangerous word in the app. Fix: never output "confirmed" or "safe". Say "readers agree; verify with your pharmacist." Report the silent-error rate that survives the ensemble, including cases where all witnesses agreed and were wrong, and put that number on a slide. Add one hard rule: if the OCR witness lacks the strength string, the app never says "agree." Talk to at least one blind user or an org rep before Saturday.
- **Receipts:** Its central claim is false. EdVisorly's EddyVerify (their own pages) already compares self-reported application data against official transcripts course by course and flags discrepancies, and EddyAI recalculates GPAs using institution rules. "First to cross-check" will get you caught on the first judge question. Fix: drop "first." Wedge on something they don't do, such as international or non-standard transcripts, or a per-number "receipt" UI that links each figure to a pixel region of the source document. Scope is also fatal: two portals plus a rules engine plus a diff is too much for 36 hours. Cut it to one flow: upload, extract, diff, show your work.
- **LectureLens:** The gain may be small, and the vendors already do this. Otter has had Custom Vocabulary since 2019, Verbit offers custom dictionaries and a live product, Panopto has custom dictionaries, and cloud ASR has phrase hints. Your novelty is auto-building the glossary from a syllabus plus the term-error benchmark. On clean CS speech modern ASR may already get these terms mostly right, so the demo could show no visible difference. Fix: run the baseline on your actual speakers and clips by Friday night. If the gap is under about 10 points of term error rate, pivot to messy audio (accents, mic distance), or merge into a different idea.

**OTHER RISKS**

FocusPage
- Segmentation fails on stylized illustrations (overlapping characters, text in the art). The demo only works on books you pre-tested. Know which books those are.
- The "clutter decreases monotonically" claim is trivially satisfiable and can be gamed. Clutter metrics didn't predict fatigue (their own cited study).
- Disability-dongle risk is moderate: the tool is for teachers, and nobody who has CVI has seen it.

Crosscheck
- Wifi risk: two cloud models plus openFDA means three network dependencies live. One 10-second latency spike or rate limit kills a 60-second demo. Prepare cached fallbacks and a video.
- Using real pill bottles and an unsupervised health claim: the demo must say it's a prototype and not medical advice.
- A benchmark of 40-60 photos, mostly team-made mock labels, is too small to support accuracy claims. Report raw counts with no percentages.

Receipts
- Real transcripts are FERPA-sensitive, so you are limited to fake ones. Extraction accuracy on fake transcripts proves little, and judges know it.
- Moat claim (configurable rules) is exactly what EdVisorly sells with 100+ schools.
- The unanswered "who pays for the student side?" question was raised in the prior feedback.

LectureLens
- Streaming ASR plus a correction pass is a latency trap. Caption lag is the problem you cite, and a correction pass adds lag.
- An LLM correction pass can hallucinate "fixes" that put wrong words in a deaf student's captions. The false-correction count must be reported.
- No Deaf or HoH student was consulted. The write-up is built on citations, not users.

**CLAIMS THAT NEED VERIFYING**
- Receipts: "first to cross-check self-report vs transcript" is contradicted by EddyVerify. Also "99% accuracy" and "95%+ at UT Austin" are vendor claims.
- Crosscheck: "none report confidence or cross-check models" is still unverified. My search found no Be My AI or Seeing AI confidence feature, but that is absence of evidence, not proof. Check the app release notes directly.
- LectureLens: "student-controlled glossary" as differentiator. Otter's custom vocabulary is per-account, so students can already add terms. Only the auto-build from a syllabus is plausibly new.
- FocusPage: no AI CVI-simplification tool turned up in my search (the only AI mention was a forward-looking one), which supports novelty. But CVI Book Nook and Little Bear Sees already supply pre-adapted material. Also verify the "leading cause" and "90% fatigue" figures against the cited papers.
- Crosscheck: the WebAIM mobile and iOS percentages need a source check. Also the openFDA endpoints "still to be checked."

**LEAST-RISKY IDEA:** FocusPage. Competitors are manual, with no AI incumbent found. Failures are graceful (a bad cutout is visible and the teacher approves each page). It has no safety-critical output, and caching makes the demo fast and resistant to latency. The main risk is overclaiming "verified."

**MOST-RISKY IDEA:** Receipts. It has the most scope, the false "first" claim, strong incumbents that hold the exact feature, a slow-sales market, and fake data that makes accuracy claims weak. Crosscheck is a close second on harm potential, but its risk is manageable through wording and framing. Receipts' risk is structural.
