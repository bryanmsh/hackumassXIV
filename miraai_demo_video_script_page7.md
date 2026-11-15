# Miraai video demo, page 7 version (2 minutes, voice-over)

A screen recording of the live site with a voice-over recorded on top. About 245 spoken words, which leaves room for pauses.

Written for: hackathon judges watching a 2-minute video. Draft for Kevin (owner of `pitch/`); not yet copied there.

## Before recording

1. Reset the demo book: `python -m api.tools.reset_demo <animal-homes book id>`. Page 7 must come back as **Needs subject** ("The page has several subjects").
2. In Subject review, confirm or **Leave out** every page **except page 7**, so the only decision on camera is the hard page.
3. Hover each rabbit chip on page 7 and note what it highlights. Both chips read "rabbit 95%". A combined suggestion may be offered as well (the spec adds one when two or more candidates are sure).
4. Check the two fictional profiles:

| Child | Look | Colors | Background | Position | Text |
| --- | --- | --- | --- | --- | --- |
| Maya | Tinted | Red | Black | Center | Off |
| Leo | Cut-out | Yellow, blue | Black | Left | Off, or Below (white or black, never the child's color) |

5. Dry-run both profiles on page 7 before recording. The two rabbits are far apart on the page, so check that Maya's and Leo's renders look right. The Source fidelity check may flag the cut-out because it is in two pieces. That is by design (spec, Checks and approval), but expect it on the contact sheet.
6. Browser full screen at 1920x1080, zoom 100%, no bookmarks bar or other tabs. Log in to the site password first, so the prompt is not on camera.
7. Record each shot as its own clip, then record the voice-over and trim the clips to fit it. Move the mouse slowly; pause a second after every click.
8. Confirm no teacher of students with visual impairments (TVI) has replied to the review email. If one has, the last line changes.

## Script

| # | Time | On screen | Voice-over |
| --- | --- | --- | --- |
| 1 | 0:00 | Black card, white text: "About 1 in 30 primary school children may have CVI-related vision difficulties." Small caption: "Williams et al., 2021, Bristol, UK. Screening survey, not diagnoses." | "About one in thirty primary school children may have vision difficulties linked to cortical visual impairment, or CVI." |
| 1b | 0:07 | Title card "Miraai" over the original page 7 | "Many of these children find one clear object on a plain background much easier to see than a busy picture-book page. Today, teachers adapt books by hand, one page at a time." |
| 2 | 0:15 | Library, open Animal Homes; Subject review, page 7 (Needs subject). Point at the tunnels, carrots, fish skeleton and stones, then hover each rabbit chip so it lights up | "Miraai does the first pass automatically, using the book's own art. On this page, the tunnels, carrots, fish skeleton and stones are all noise. The AI suggests two rabbits, both at ninety-five percent, but that number is its own guess. The page has several subjects, so it asks the teacher." |
| 3 | 0:38 | Click both rabbit chips, then **Confirm** | "The page text names rats too, but today the teacher picks the rabbits. Two clicks, then confirm. The cut-out comes straight from the original drawing. Nothing is drawn or invented by AI." |
| 4 | 0:53 | Contact sheet: Maya, Tinted; slow pan over the checks; click **Approve sheet** | "Maya sees the rabbits tinted red, on black. Automatic checks measure the cut-out and the contrast, but they are not approval. Only the teacher approves. One click approves the whole sheet." |
| 5 | 1:12 | Contact sheet: Leo, Cut-out; click **Approve sheet** | "Leo sees the same rabbits in their real colours, on the left. Same cut-outs, no new AI work." |
| 6 | 1:22 | Reader for Maya; arrow through two pages; press **T**, switch to Leo, arrow on | "The reader is calm. Nothing moves unless the teacher presses a key, and it only shows pages the teacher has approved." |
| 7 | 1:40 | Side by side: original page 7, Maya's page, Leo's page; then end card with miraai.study | "No child with CVI has used Miraai yet, and no teacher of the visually impaired has reviewed it. That is next. Miraai: the book's own pictures, adapted for every child, with a teacher in charge of every page." |

## End card

*Animal Homes* by Ashwitha Jayakumar, illustrated by Nafisa Nandini Crishna. Pratham Books on StoryWeaver, CC BY 4.0. Adapted by the Miraai team: cut out and recoloured.

## Video description

Williams C. et al. (2021), *Developmental Medicine & Child Neurology*: about 3.4% of 2,298 primary school children in Bristol had at least one CVI-related vision problem in a screening survey.

## Wording

- Say "checks" or "measured". Never say "verified".
- Never say a look is right for a child.
- Never say our own cut-out model is live; the site uses SAM 2.1.
- The opening stat is from a screening survey, not diagnoses: say "may have", never "have CVI".
- The AI does not choose the rabbits. Page 7 is **Needs subject**, so the teacher chooses. Never say "the AI picked".
- The 95% is the AI's own estimate and is not calibrated. Never present it as evidence the suggestion is right.
- The grey shapes on page 7 are a fish skeleton and stones, not fossils.
- Page text is shown in white or black, never in the child's color.
- Do not give a processing time ("in minutes") unless you time the upload on the recording day. Your notes only have 30 s for the 5-page book on the server with GrabCut.

## What changed from the first script

| First script | Now | Why |
| --- | --- | --- |
| "a busy picture-book page is a blur" | "many of these children find one clear object... much easier to see" | CVI is not a blur. Only 15% of affected children in the Bristol study had reduced acuity, and not every child responds the same way. |
| "so these kids get only a handful of books" | "teachers adapt books by hand, one page at a time" | No source for the "handful" claim. |
| "Miraai does it in minutes" | "does the first pass automatically" | No timing for a 12-page book with SAM 2.1. |
| Words "in her red", "big yellow type" | Removed | The spec shows page text in white or black. |
| "One click, the whole book" | "the whole sheet" | Approve sheet covers only the confirmed pages. |
| One click on the hornbill (page 3) | Two clicks on the rabbits (page 7) | New demo page. |

## Sources

- Bristol news release: https://www.bristol.ac.uk/news/2021/february/cvi-study.html
- Williams et al. 2021 abstract: https://zendy.io/title/10.1111/dmcn.14819
- Book credits: https://freekidsbooks.org/animal-homes-early-nature-lessons/
- Paths to Literacy, book modification: https://www.pathstoliteracy.org/modifying-books-children-cvi/
