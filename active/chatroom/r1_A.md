POSITION: Build FocusPage, the only idea whose output (a busy picture-book page visibly simplified for one specific child) demos in five seconds, runs on off-the-shelf parts, and can be evaluated with free synthetic ground truth.

WHY THIS IDEA WINS:
1. **Demo legibility.** A cluttered page becomes one red object on black, then flips to another child's profile instantly. Crosscheck's payoff is a spoken sentence, hard to show a room. LectureLens needs live audio in a loud hall where ASR gains look small. Receipts is a table diff, the demo judges have seen from Slate/EdVisorly.
2. **Thin competition.** Quick search found only manual or fixed-content tools: APH CVI Complexity Sequences (ten fixed image sets), Paths to Literacy CVI Book Builder (templates), Little Bear Sees (how-to guides), Vision Nanny. I found no tool that auto-adapts real books. Receipts faces EdVisorly/Parchment (100+ schools, 50k-transcript scale); Crosscheck faces Be My AI/Seeing AI (unverified); LectureLens faces custom-vocabulary ASR APIs.
3. **Most buildable.** Every stage is an API or library call: Gemini names the object, rembg/U2-Net (or hosted SAM 2) cuts it out, Pillow handles recolor, fade and outline. Cached cutouts make child/level switches instant, so the demo can't lag. Receipts needs two portals plus a rules engine; Crosscheck needs three witnesses plus a labeled benchmark; LectureLens needs streaming ASR.
4. **Free evaluation labels.** ARIA objects pasted on clutter give known masks (IoU, recognition retention); StoryWeaver is CC-BY. Crosscheck needs 40-60 hand-labeled photos; LectureLens needs 15 minutes of hand-corrected audio.
5. **Track fit and story.** Best Accessibility is the core target for a real population (2025 study: fatigue in over 90% of children with CVI, linked to clutter). Gemini is central, MongoDB holds profiles and cutouts, Vultr hosts it, and UI/UX is plausible.

WEAKNESSES I ADMIT:
- No CVI child tested, and clutter is only a proxy (the 2025 study found clutter metrics matched human ratings but did not predict fatigue). Expect a sharp judge to push here.
- Segmentation fails on multi-object pages, text-in-art, and thin or transparent objects, all common in picture books.
- The self-check is partly circular if Gemini both names and verifies, and an "unverified" flag on a good page looks bad live.
- Niche audience: the first 20 seconds must teach CVI.
- One unverified lead (a Google engineer's CVI literacy app) could undercut novelty; check it first.
- Copyright of adapted commercial books is unaddressed.

FIXES:
- Use a different model family as the verifier, and have it choose among distractors rather than free-name.
- Claim two measurable things only: object retention (IoU and recognition on ARIA) and monotonic clutter reduction. State plainly it is not a clinical outcome.
- Pre-adapt five StoryWeaver books for reliability, but keep a live path for a judge's pick.
- Open the pitch by showing a hand-cut, hand-recolored book next to the output.
- Email one TVI (Perkins, Anchor Center) before Saturday and quote them. This answers the disability-dongle critique that also hurts Crosscheck.
- Merge option: borrow Crosscheck's "show your uncertainty" idea so flagged pages become a feature, not a gap.

36H SCOPE:
- Demo-critical: StoryWeaver/PDF page ingest, Gemini subject naming, cutout with cache, levels L1-L4, two profiles, fullscreen viewer with teacher approve, verified badge, one rejected-page example, ARIA IoU results slide.
- Timeboxed: clutter metric (edge density or proto-object count, not full feature congestion).
- Cuttable: phone photo input, print export, accounts/login, batch-UI polish, SAVOIAS correlation, MongoDB beyond basic profile storage.
- Split: segmentation and levels pipeline; viewer and profile UI; eval and verifier; pitch, TVI outreach and data prep.

Sources: pathstoliteracy.org/resources/cvi-book-builder, aph.org/blog/create-custom-lessons-with-the-cvi-complexity-sequences-app, littlebearsees.org/2016/09/10/reducing-visual-complexity-books
