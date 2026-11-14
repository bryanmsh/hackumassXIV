POSITION: Build LectureLens, because its core claim (course-aware captions beat stock captions on course terms) can be proven live, on a fresh clip, with a number, using one cheap API call, so it carries the least build risk of the four.

WHY THIS IDEA WINS:
1. Lowest technical risk, knowable by hour 2. Deepgram (Nova-3/Flux `keyterm`, up to ~100 terms) and AssemblyAI (streaming `keyterms_prompt`, ~100 terms) document keyword boosting, so the biased-ASR core is one parameter on a hosted API. FocusPage chains segmentation, two vision models, a clutter metric and profiles. Receipts needs two portals plus a rules engine. Crosscheck needs a labeled photo benchmark plus three-witness reconciliation.
2. The demo is self-evident. Two panes, same audio: stock says "Dyke's trah" and "heap a fly"; ours says "Dijkstra" and "heapify". A judge can say a term and watch. Receipts' payoff is a table diff judges have seen; FocusPage's payoff (a child with CVI recognizing the object) cannot be shown in the room.
3. Falsifiable measured claim: term error rate across baseline, glossary prompt, and prompt plus correction, including false corrections introduced, rerun on a clip recorded at the table.
4. Real users and a legal tailwind: Deaf and hard-of-hearing students, and the ADA Title II web accessibility rule for large public universities. Real UMass CICS syllabi also target Best UMass Hack.
5. Honest differentiation: boosting itself is a commodity vendor feature. My search found Otter has a manual custom vocabulary (2019 launch, paid tiers) and Panopto has a site-level admin dictionary (Aalto emails words to be added). I found no evidence either builds a vocabulary automatically from a student's own syllabus or slides. That gap (automatic, per-course, student-controlled) is the claim.

WEAKNESSES I ADMIT:
- Thin moat: a vendor could add "upload your syllabus" in a sprint.
- Gain on clean speech may be small; modern ASR handles "heap" and "stack". The lift is in rare terms, names, accents.
- The benchmark (15 min hand-corrected) is hours of labor, and a teammate-recorded set invites overfitting doubts.
- No Deaf user input, so the disability-dongle critique applies; a few points of term accuracy is incremental.
- A correction pass adds latency, and caption lag is a top Deaf-user complaint.
- Visually the least flashy: text on a screen.

FIXES:
- Pitch it as a course-aware layer on any ASR, not a new ASR. Say upfront that boosting is a vendor feature; our contribution is auto-extraction, measurement, and flagging uncertainty.
- Build an adversarial benchmark: dense rare terms (Dijkstra, heapify, amortized, Kruskal), two fast or non-native speakers, some noise. Report TER and false corrections. A null result on clean audio is fine if stated.
- Constrain the correction pass to substitutions near glossary terms (edit or phonetic distance), each with a confidence score, instead of free LLM rewriting.
- Show low-confidence fixes with a dotted underline. This borrows Crosscheck's "say when unsure" strength.
- Contact UMass Disability Services or one Deaf/HoH student by Saturday morning and quote them on the slide.
- Merge option: LectureLens plus Crosscheck's uncertainty framing, as one "AI that shows its uncertainty to accessibility users" story.

36H SCOPE:
Demo-critical: (1) syllabus/slide PDF to editable glossary; (2) streaming ASR with keyterm boost beside a stock pane on the same audio; (3) benchmark script for WER and TER across three setups, plus a results slide; (4) clean two-pane UI with highlighted corrected terms.
Nice to have: constrained correction with confidence flags; preloaded CICS syllabus.
Cuttable: tap-for-definition, true streaming (3-second chunks are fine), speaker labels, accounts, mobile.

Sources: developers.deepgram.com/docs/keyterm; assemblyai.com/blog/streaming-keyterms-prompting; nojitter.com/ai-speech-technologies/otterai-adds-custom-vocabulary; blogs.aalto.fi/opit/?p=1553
