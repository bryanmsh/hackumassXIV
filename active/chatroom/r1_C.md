POSITION: Build Receipts, but pitch it as a "show your work" transcript-to-GPA tool for one underserved wedge (international or non-standard transcripts), not as "the first to cross-check self-report."

WHY THIS IDEA WINS:
1. **The demo is the strongest and the most universal.** Any judge understands the red flag in five seconds: "Student said A in AP Chem, transcript says B+." FocusPage needs the judge to understand CVI phases. LectureLens needs a spoken mini-lecture and ears tuned to term errors. Crosscheck needs a medication label and trust in a benchmark. Receipts needs no domain explanation.
2. **It has the safest 36h build path.** The core is OCR/LLM extraction into a table, a diff, and deterministic Python GPA math. There is no segmentation model, no streaming ASR, and no multi-model ensemble. The engineering feedback ("compute in code, flag anomalies") makes it more robust than the other three, which depend on model quality that cannot be tuned on a deadline. A degraded demo still looks fine, because a messy table remains a table.
3. **Real pain and paying buyers.** Schools pay vendors today. FocusPage and LectureLens target budget-starved accessibility buyers. Receipts is a product people already buy. That helps with the Practicality criterion and gives a credible answer to "who uses this Monday?"
4. **Broad prize coverage.** It fits Most Impactful AI, Most Secure (in-memory processing, fake data only, audit log), Best UI/UX (the diff view), Gemini, MongoDB (the rules and audit log), and Best Overall. Crosscheck and FocusPage are more accessibility-concentrated, and they compete with each other for that same track.
5. **Auditable by design.** "Every number has a receipt" (click a GPA to see the source rows and rule) is a strong trust story and a good UI. It is also the right answer to the "AI shouldn't do the math" critique.

WEAKNESSES I ADMIT:
- **My own search undercut our key claim.** EdVisorly's EddyVerify markets automated comparison of self-reported data against the official transcript, course by course, with humans reviewing only flagged mismatches. That is almost exactly our headline differentiator. "First to cross-check" is false and a judge could find it in one search. (Vendor marketing only. I found no independent accuracy data.) STARS EasyImport is confirmed as AI import for the student's self-report, in beta, with no checking step.
- Innovation is the weakest of the four. This is a crowded, solved-ish category.
- Scope creep risk: two portals, a rules engine, AI classification, and a diff.
- Slow university sales, FERPA, and the question of who pays on the student side.
- Extraction accuracy on real, messy transcripts is untested. We can only use fake ones.

FIXES:
- **Drop "first." Lead with transparency and a wedge.** The pitch: "Incumbents give you a number. Receipts gives you a number you can audit, and it handles the transcripts they struggle with." Pick one wedge: international or non-standard transcripts (different grade scales, credit systems, course names), or small schools without Slate-scale budgets. Then demo a transcript on a non-US scale.
- **Collapse to one screen.** One app with a "student" and "school" tab, not two portals. A shared extraction pipeline feeds both.
- **Make the AI classification the hero.** The admissions feedback calls it the hard, valuable part. Show a course-name classifier with confidence and a checkbox for override. Rules live as one JSON preset.
- **Measure it.** Build a 15 to 20 fake-transcript benchmark with known ground truth (varied layouts, scanned or rotated). Report field accuracy and anomaly-detection rate. This answers "doesn't EdVisorly do this?" with numbers instead of claims, and it matches the evaluation rigor of Crosscheck.
- Add an override audit log (cheap, high value to admissions staff).

36H SCOPE:
- **Demo-critical:** (1) upload a fake transcript, then extract into an editable table; (2) student self-report vs official diff, mismatches in red; (3) one JSON preset with grade conversion and "Calculate GPA" in Python, with a click-to-trace receipt for each number; (4) AI course classification with override checkboxes; (5) a small accuracy benchmark slide.
- **Cuttable:** the second preset, the anomaly flags beyond one or two (credit outlier, printed GPA mismatch), sorting, and the audit log (cut last, since it is cheap). Also cut any real auth, multi-tenant setup, and Slate-style integrations.
- **Never cut:** deterministic math, the red diff, the receipt trace, and one honest accuracy number.
