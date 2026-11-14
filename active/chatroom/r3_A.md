AGREEMENTS:
- F is right that a random-distractor multiple choice passes any clean cutout. I drop it as the primary check.
- F is right that ARIA photos are not illustrations. ARIA is demoted to a unit test of mask math and to the L1 recolor test. It is not the headline evidence.
- F is right that linking the name to the mask was unbudgeted. It gets a line item below.
- F is right that L1 single-hue recolor is an untested assumption.

DISAGREEMENTS:
- "Hand-waving" overstates it for the verifier. Chosen carefully, distractors do catch the failure that matters, a wrong object cut out. They are drawn from the same page, not random (see Check 3).
- A dual gate is not realistic as a symmetric contest. Splitting 3-4 people across two prototypes in the first 6 hours costs the winner its build time. The Crosscheck gate (15 photos, 3 API calls) is about 45 minutes for one person, so run it only as fallback insurance. Commit to FocusPage up front. Only FocusPage's gate decides.

FINAL PIPELINE:
1. Ingest: PyMuPDF renders each page to PNG. StoryWeaver pages are images already.
2. One Gemini call (Flash, JSON schema) returns: main_subject name, a bounding box (Gemini's native 0-1000 box output), list_of_other_objects, and flags multi_object and text_in_art. This is the name-to-mask link. The name and box come from the same call.
3. Cutout: SAM 2 prompted with that box (hosted via Replicate, or vit_b on Vultr). Budget 3 hours. Fallback if SAM slips: crop to the Gemini box, then run rembg (isnet-anime) inside the crop. The box forces the right object.
4. Render: L1 is a luminance-preserving tint (shading and internal edges kept) of the child's hue on black. It is not a flat fill. L2 is real colors on plain. L3 is faded scene plus vivid object. Cached cutouts make switching instant.

Checks that catch real failures:
- C1 mask-box sanity: IoU(mask bbox, Gemini box) at least 0.6. This catches the wrong object.
- C2 geometric sanity: mask area 3-70% of the page, one component holding at least 90% of the area, and the mask not touching 3 or more page edges. This catches background leak and fragments.
- C3 cross-family verifier (Claude, since Claude is a possible sponsor): it sees only the L1 render. The choices are the target plus the page's other objects from step 2 (not random words). If the cut grabbed the tree instead of the dog, it picks "tree" and fails.
- C4 L1 recognizability: if the verifier recognizes L2 but not L1, that page auto-falls back to L2 and says so on screen.
- Any failure, or a multi_object or text_in_art flag, shows a "teacher review" card. This is the visible-uncertainty feature.

Evidence: teammates hand-box 20 real StoryWeaver pages (about 40 minutes). Report the Gemini-vs-hand box IoU and counts of accepted / flagged / failed (for example "14 / 4 / 2 of 20"). Headline claim: "recognizable by machine check on X of 20". It is not a clinical claim.

FINAL VERDICT: FocusPage, committed Friday. Gate at hour 6: at least 7 of 10 fresh illustrated pages pass C1-C3 with one prompt iteration allowed. Decision rule:
- 7 or more: build on.
- 4-6: switch to the crop+rembg fallback for 1 hour and retest on 10 new pages.
- Still under 7 at hour 8: switch to Crosscheck only if its 15-photo run showed at least 3 silent errors by then.
- Otherwise ship FocusPage on a curated shelf of pages that pass, with the shelf stated openly.

CONFIDENCE: 7/10. The residual risk is segmentation on painted or textured art. The hour-6 gate finds that out early and cheaply.
