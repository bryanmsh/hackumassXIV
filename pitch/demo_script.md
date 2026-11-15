# Miraai demo script (word for word)

About 4 minutes. **Kevin speaks. Thomas drives** the laptop. Bryan stands by for the server, Andrew for the API.
The app runs in a desktop or laptop browser only. In the reader: arrow keys or space turn the page, T opens the teacher bar.

## Before every judge (2 minutes, Andrew or Bryan)

1. Reset the demo book, so the hard page is unfixed again:
   `python -m api.tools.reset_demo <animal-homes book id>`
   It should print each page back in its first state and "N approvals removed."
2. Check Maya and Leo exist in Profiles and look as below.
3. Thomas opens the Library in a full-screen browser window, zoom 100%.
4. Kevin has the slides on a second screen, and the backup video open in another tab.

Demo profiles (both fictional):

| Child | Look | Colors | Background | Position | Text |
| --- | --- | --- | --- | --- | --- |
| Maya | Tinted | Red | Black | Center | Off |
| Leo | Cut-out | Yellow, blue | Black | Left | Below the picture |

If size, position and text controls are not in Profiles yet, Leo is Cut-out, centered, text off.

## Script

| # | Time | Thomas does | Kevin says |
| --- | --- | --- | --- |
| 1 | 0:00 | Title slide | "Children with cortical visual impairment, CVI, recognize one clear object on a plain background far better than a busy picture-book page. Today their teachers rebuild pages by hand, with scissors and black card, so each child gets only a few books." |
| 2 | 0:20 | Library: Animal Homes, already uploaded | "Miraai adapts a real picture book, using only the book's own artwork. This is Animal Homes, a free StoryWeaver book. When we upload it, each page goes to an AI once to find what the page is about. The upload screen tells the teacher that." |
| 3 | 0:40 | Open Subject review; point at the states | "Every page ends in a clear state. When a page is about one thing, the AI pre-selects it. When a page names several things, it does not guess: it asks the teacher. Nothing reaches a child until the teacher confirms it." |
| 4 | 1:00 | Open page 2: Needs subject, with hornbill, beehive, nest and the combined "beehive, bird and bird nest" offered | "This page is the hard one. 'Birds build their homes up high, and so do bees.' The AI found a hornbill, a beehive and a nest, and offers all three together too. For a child with CVI, three objects can be two too many. Only a person knows which one matters for this child today." |
| 5 | 1:20 | **Suggestions**: pick the hornbill alone, then confirm | "One click on the hornbill, and the teacher confirms. The cut-out is the original drawing, traced by a segmentation model. Nothing is drawn or invented by AI." |
| 6 | 1:35 | **Confirm all** for the remaining pages; **Leave out** any page not wanted | "For pages where the suggestion is right, the teacher confirms them all at once, and leaves out any page that does not work for this child." |
| 7 | 1:50 | Contact sheet: choose Maya, Tinted | "Now the teacher picks a child. Maya sees the subject alone, tinted in her red, on black. Under each page are automatic checks: is the cut-out taken from the original with no stray specks, is the background plain, does the subject stand out. They are measurements, not approval." |
| 8 | 2:15 | **Approve sheet** | "The teacher approves the whole sheet at once. That approval is tied to this exact picture: change her color, or the subject, and the page needs approval again." |
| 9 | 2:30 | Contact sheet: Leo, Cut-out; **Approve sheet** | "Leo sees the same subject in its real colors, on the left, with large text below. A second sheet, not dozens of decisions." |
| 10 | 2:50 | Open the reader for Maya; arrow key through two pages | "The reader is full screen and calm. Nothing moves unless the teacher presses a key. A child's clicks do nothing." |
| 11 | 3:10 | Press **T**, switch to Leo, arrow on | "Switching to Leo is instant, because it reuses the saved cut-outs. No new AI work. Versions that were never approved are greyed out; the reader refuses to show them." |
| 12 | 3:25 | Last page: credits screen | "Every book ends with its author, illustrator and license, and a note that it was adapted." |
| 13 | 3:35 | Limits slide | "What we have not done yet: no child with CVI has used Miraai, and it is not yet reviewed by a TVI. The AI's confidence is not proof; the teacher's confirmation is. That is the point of the design." |
| 14 | 3:50 | Title slide | "Miraai: the book's own pictures, adapted for each child, and a teacher in charge of every page. Thank you." |

## Words to use and avoid

- Say "checks" or "measured." Never say "verified."
- Say "looks" or "modes." Never say a look matches a CVI phase or is right for a child.
- Say "not yet reviewed by a TVI" until a TVI replies.
- Say exactly what the AI does: Gemini picks the subject, a segmentation model traces it, our display code does the rest with no AI.

## If something breaks

| Problem | Do |
| --- | --- |
| Upload or processing is slow | Use the pre-processed copy of Animal Homes; it is already in the Library |
| Gemini is down | On page 2, use **Draw an outline** around the hornbill instead of Suggestions. It calls no model |
| A cut-out looks wrong on stage | Say so: "this is why the teacher reviews every page," and pick another suggestion |
| The live site is down | Say "we will show our recording," then play the backup video. Never present the video as live |

## Open decisions

- Demo book and hard page: Animal Homes, page 2 (Needs subject since commit 9e09be4); the teacher picks the hornbill alone. Confirm with Bryan at hour 10.
- Which edition: `fixtures/` has a 5-page Animal Homes, but Bryan's notes use a longer one (page 10 is the crocodile). Page numbers above are for the 5-page fixture.
- Which pre-selected picks to leave as they are on the other pages. Run the book with Bryan's latest pipeline and `SEGMENTER=sam2` first.
- Timing is a guess until the first rehearsal; cut steps 6 and 12 first if over time.
