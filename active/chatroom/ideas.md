# Four candidate ideas for HackUMass XIV (36-hour hackathon)

None of these are set in stone. The team wants them compared head to head, with potential fixes noted for each.
HackUMass judging criteria: Innovation, Functionality, Practicality, Presentation. Prize tracks mentioned: Best Accessibility Hack, Most Impactful AI, Most Secure Hack, Best UI/UX, Best Software Hack, Best UMass Hack, MedTech, Best Overall. Sponsors: Gemini, Vultr, MongoDB Atlas, domain name; possibly Claude.

---

## IDEA 1: FocusPage — picture books a child with CVI can actually see
Target: Best Accessibility Hack + Gemini, Vultr, MongoDB Atlas, domain sponsor prizes.

**One line:** A teacher opens any digital picture book or uploads a photo of a page. FocusPage turns each page into a version a child with CVI can process, using that child's preferred colors and the visual complexity they can handle. Before a page is shown to the child, the app checks that the main object is still recognizable.

**Problem:** Cortical/cerebral visual impairment (CVI) is brain-based: the eyes work, but the brain struggles to sort what it sees. It is described as a leading cause of childhood visual impairment in the US and other developed countries. Kids with CVI recognize objects much better when an image is simplified: one object, little clutter, strong contrast, often a favorite color. Picture books are busy. Teachers of students with visual impairments (TVIs) and parents simplify pages by hand by cutting, recoloring, and rebuilding them, so each child gets only a few adapted books. Supporting research: a 2025 study (Ophthalmic & Physiological Optics, n=72) found visual fatigue in more than 90% of children with CVI, linked to clutter. An Anchor Center eye-tracking study (Perkins 2026 CVI conference) is testing whether simplified storybook pictures help preschoolers find the target faster; few intervention studies exist.

**Users:** TVIs (primary). Parents and early-intervention/SPED staff (secondary). Buyers are district SPED budgets and organizations such as Perkins.

**How it works:**
1. Input: a digital book (PDF or StoryWeaver) with all pages processed at once, or a photo of one page.
2. Find the main subject once per page: Gemini names it ("the red ball"), a segmentation model cuts it out, and the result is cached.
3. Per-child profile: preferred color(s), background color, and complexity level 1–4 mapped to CVI Range phases. L1: the single object in a preferred color on black. L2: the object in real colors on a plain background. L3: the original scene faded, with the object kept vivid. L4: the original page with the key object outlined in the child's color. Because the cutout is cached, regenerating for another child or level is near-instant: adapt once, and every child gets their own version.
4. Self-check: a second vision model sees only the adapted page and names the object. If it doesn't match, the page is flagged "not verified." Clutter is measured before and after, and it must decrease at each lower level.
5. The teacher approves each page, then it is shown full screen on a tablet or display, or printed.

**What's new:** Today teachers adapt by hand. Vision Nanny (LV Prasad) places images on a background color manually. The ARIA CVI AAC Photoset (about 1,900 objects on black) is a fixed vocabulary, not real books, and is used here for testing. The complexity dial follows the child's progress through the phases.

**Evaluation:** (1) 200 ARIA objects pasted onto cluttered backgrounds give known masks, so segmentation IoU and recognition retention can be measured. (2) 20 StoryWeaver pages (CC-BY): clutter before and after, plus recognition. (3) Clutter metric (proto-object count or feature congestion) compared against human ratings (SAVOIAS/HINDER). (4) Clutter decreases monotonically from L4 to L1 on every page. (5) Self-check flag rate, with a rejected example.

**Demo (2 min):** Profiles "Maya, Phase I, red" and "Leo, Phase II, yellow+blue." The judge picks any StoryWeaver book, which is adapted live with a "verified: still recognized as dog" badge. Switching Maya to Leo is instant. The dial moves L1 to L4. Optionally, the judge photographs a physical book page. The demo ends with a rejected page and a results slide.

**Honest limits:** No CVI children were tested. Clutter is a proxy (the 2025 study found clutter metrics matched human ratings but didn't predict fatigue). The app doesn't diagnose. Pages with multiple key objects or text in the art are flagged. Photos must be flat. Copyright for sharing adapted commercial books is not addressed.

**Future:** live camera view, whole-book video capture, an eye-tracking study with CVI children.

---

## IDEA 2: Crosscheck — a second opinion on medication labels for blind users

**Problem:** A blind or low-vision user photographs a pill bottle with an AI describer. If the AI misreads "10 mg" as "40 mg," they can't tell. AFB's 2025 survey reports wrong AI information, naming a misread medication label as an example. It also found people with disabilities almost 3x as likely to be unable to get a medication or procedure, and most respondents wanted AI that doesn't save or send private data. WebAIM: 91.3% of screen-reader users use one on mobile, and 70.6% use iOS/VoiceOver. So the plan is a mobile web app that works with VoiceOver, not a custom voice UI.

**Solution:** The phone captures a photo, and three independent "witnesses" read it in parallel: Claude vision (structured JSON), Gemini vision (same schema), and classical OCR raw text. A deterministic reconciler normalizes the fields: drug name, strength and unit, directions, quantity, refills, warnings. A field is confirmed only if both models agree and the value appears in the OCR text. Then an openFDA lookup checks whether the drug actually comes in that strength (endpoints still to be checked). Output goes to an aria-live region: confirmed fields first, then an explicit uncertainty sentence and re-take guidance ("glare detected, tilt the bottle"). Processing is in memory only with no storage, and the network tab shows it.

**60-second demo:** Pitch line: "AI describers misread med labels; Crosscheck says when it isn't sure." The judge picks a bottle from a tray, and the phone reads "two readers agree." With a glared or curved label, Model A alone says "40 mg" confidently, while Crosscheck says "readers disagree on strength." The eval dashboard reruns on the held-out set.

**Technical angle:** A hand-labeled benchmark of 40–60 photos: the team's own OTC bottles, printed mock Rx labels with fake names, and degraded variants (glare, curvature, blur, crop). Ground truth is a CSV. A dev set is used for prompt tuning, and a held-out set is labeled Saturday afternoon and never tuned on. Metrics: per-model field accuracy, silent-error count (wrong and confident), silent errors flagged by the ensemble, and false-alarm rate. Report counts. `make eval` reruns it.

**Categories:** Best Accessibility Hack, MedTech, Most Impactful AI, Best Overall, UI/UX. Sponsors: Claude and Gemini.

**Cuttable:** openFDA check, the OCR witness, re-take guidance. Never cut: two-model reconciliation, spoken uncertainty, eval numbers.

**Biggest risk:** Correlated errors. If both models misread the same way, the ensemble catches little; mitigated with OCR and openFDA. The second risk is the disability-dongle critique if no blind user is consulted.

**Competitors:** Be My AI, Seeing AI, Aira, Envision. The claimed gap is that none report confidence or cross-check models (unverified). Check whether Seeing AI or Be My AI has added a medication mode or confidence output.

---

## IDEA 3: Receipts — AI transcript checker for college admissions

**Problem:** Admissions offices still type grades off transcripts by hand and recalculate GPAs in spreadsheets. Every school has different rules, mistakes happen, and students sometimes self-report grades that don't match the real transcript.

**What we build:**
- Student side: upload a transcript. AI extracts every course and grade into a clean editable table with plain-English descriptions of odd course names.
- School side: scan the official transcript, compare it with the student's self-report, and show mismatches in red.
- School presets: grade conversions, AI classification of courses (core academic vs elective), and a one-click GPA calculation that shows its work.
Stack: React + FastAPI + Gemini. Fake transcripts only.

**Prior feedback already gathered:**
- Judge view: the demo writes itself (a red flag: "Student reported A in AP Chem, transcript shows B+"). It fits many prizes: Most Impactful AI, Most Secure, UI/UX, Gemini, MongoDB, maybe Agentic. Scope risk: two portals, a rules engine, AI classification, a comparison view, and an AI checker is a lot for 36h. Judges will ask "doesn't Slate or EdVisorly do this?"
- VC view: the pain is real and schools already pay vendors. The two-sided design has a network effect. Configurable rules are the moat. Concerns: EdVisorly (100+ schools) and Parchment are entrenched; you'd need a wedge (small schools or international transcripts). University sales are slow (6–18 month procurement, FERPA, SOC 2, Slate integration). Who pays for the student side?
- Admissions officer view: they'd use the swap and override buttons, and presets like "drop lowest," "only 10–12," "honors weight but not dual enrollment." AI course classification is the hard, valuable part. They want an audit log of overrides.
- Engineering view: don't let AI do the math; compute in code. Replace the "AI double check" with anomaly flags (a 0.5-credit outlier, a printed GPA that doesn't match the listed grades). Store rules as JSON config.
- Ethics view: fake transcripts only, mention FERPA once, keep a human approving decisions.
- 36h MVP: the student upload → extraction → editable table; the school upload → extraction → side-by-side diff with red mismatches; one school preset with grade conversion, AI classification with checkboxes, and a "Calculate GPA" button showing its work. If time allows: a second preset, anomaly flags, the override log, sorting.

**Competitors:** Slate (Reader AI summarizes essays but doesn't turn transcripts into course data out of the box). STARS EasyImport (a student uploads a transcript and AI fills the self-reported record, with no checking step). Parchment Data Automation (OCR into Slate, 95%+ at UT Austin, 50k-transcript scale). EdVisorly/EddyAI is the strongest: AI extraction plus rules-based GPA recalculation, duplicate detection, 100+ partners, and a claimed 99% accuracy. Claimed differentiators: checking self-report against the official record, every number traceable to its source, and a design for both students and schools.
Pitch line: "Most schools still enter transcript data by hand. The tools that automate it are expensive and only read one document. We're the first to cross-check what students say against what their transcript shows, and every number we produce comes with a receipt."

---

## IDEA 4: LectureLens — live captions that know your course

**Problem:** Deaf and hard-of-hearing students, and anyone rewatching a recording, get auto-captions that mangle course terms like "Dijkstra," "amortized," and "heapify." Deaf students at Cambridge said auto-caption quality was doubtful and had to arrange their own support (Varsity). Caption lag and not knowing who is speaking are the key problems in small groups (arXiv 2109.10412). Large public universities now fall under the ADA Title II web accessibility rule (NPR).

**Solution:** Paste a syllabus or slide deck. It builds a course glossary, runs streaming ASR biased toward that glossary, then a correction pass limited to glossary terms that flags low-confidence fixes. Tap any term in the captions for its definition.

**60-second demo:** A teammate gives a 30-second mini-lecture on heaps and Dijkstra. Two caption panes run side by side: stock ASR and LectureLens. Then the benchmark table is shown.

**Technical angle:** A course-term error-rate benchmark: about 15 minutes of audio on 3 CS topics (teammates plus public lectures with transcripts), hand-corrected. Report WER and term error rate for three setups: baseline, glossary prompt, and glossary prompt plus correction, including the false corrections introduced. Rerun it at the table on a fresh clip.

**Prizes:** Best Accessibility Hack, Most Impactful AI, Best Software Hack, plus Best UMass Hack if glossaries come from real UMass CICS syllabi.

**Cuttable:** term definitions, and true streaming (fall back to 3-second chunks). Biggest risk: on clean audio the gain may be small; use dense vocabulary and varied speakers.

**Competitors:** Panopto/Echo360 auto-captions, Verbit, and Otter, plus cloud ASR APIs that accept custom word lists (from memory; verify). How it differs: the glossary is built automatically from course materials, it's student-controlled, and term accuracy is measured.
