# Miraai demo script (word for word)

About 4 minutes. **Kevin speaks. Thomas drives** the laptop. Bryan stands by for the server, Andrew for the API.
Live site: [miraai.study](https://miraai.study) (fallback: jensenhuangexecutiveboard.vip), behind the site password.
The app runs in a desktop or laptop browser only. In the reader: arrow keys or space turn the page, **T** opens the teacher bar, **B** blanks the screen, Esc closes the bar.

## Before every judge (2 minutes, Andrew or Bryan)

1. Reset the demo book, so the hard page is unfixed again:
   `python -m api.tools.reset_demo <animal-homes book id>`
   It prints each page back in its first state and "N approvals removed." Profiles, cut-outs and checks are kept.
2. Check Maya and Leo exist in Profiles and look as below.
3. Thomas opens the Library in a full-screen browser window, zoom 100%.
4. Kevin has the slides on a second screen, and the backup video open in another tab.

Demo book: *Animal Homes* (Pratham Books, StoryWeaver, CC BY 4.0), the full 16-page edition. Page 1 is the cover, pages 2 to 12 are the story, pages 13 to 16 are credits and back matter with no subject. **The hard page is page 3**: "Birds build their homes up high. And so do bees."

Demo profiles (both fictional):

| Child | Look | Colors | Background | Position | Extra words below |
| --- | --- | --- | --- | --- | --- |
| Maya | Tinted | Red | Black | Center | Off |
| Leo | Cut-out | Yellow, blue | Black | Left | On |

At Tinted and Cut-out the page's words are always shown in a band below the picture, in the book's own line breaks, without the page number, and in the child's main colour when it reads clearly on the background (red for Maya, yellow for Leo). The "extra words" option only adds a second copy at Faded page and Outlined, where the words also stay on the page.

## Script

| # | Time | Thomas does | Kevin says |
| --- | --- | --- | --- |
| 1 | 0:00 | Title slide | "Children with cortical visual impairment, CVI, recognize one clear object on a plain background far better than a busy picture-book page. Today their teachers rebuild pages by hand, with scissors and black card, so each child gets only a few books." |
| 2 | 0:20 | Library: Animal Homes with its cover, already uploaded | "Miraai adapts a real picture book, using only the book's own artwork. This is Animal Homes, a free StoryWeaver book. On upload, Miraai reads the author, illustrator and license from the book's own credits page, and finds what each page is about. The upload screen tells the teacher that pages go to an outside AI." |
| 3 | 0:40 | Open Subject review; point at the states | "Every page ends in a clear state. When a page is clearly about one thing, it arrives with that subject picked. When a page names several things, Miraai does not guess: it asks the teacher. Nothing reaches a child until the teacher confirms it." |
| 4 | 1:00 | Open page 3: Needs subject, with hornbill, beehive, nest and the combined "beehive, bird and bird nest" offered; hover a chip to light up its object | "This page is the hard one. 'Birds build their homes up high. And so do bees.' The AI found a hornbill, a beehive and a nest, and offers all three together too. For a child with CVI, three objects can be two too many. Only a person knows which one matters for this child today." |
| 5 | 1:20 | **Suggestions**: pick the hornbill alone, then confirm | "One click on the hornbill, and the teacher confirms. The cut-out is the original drawing, traced by a segmentation model. Nothing is drawn or invented by AI." |
| 6 | 1:35 | **Confirm all** for pages already picked; **Leave out** the rest | "Where the pick is right, the teacher confirms them all at once, and leaves out any page that does not work for this child." |
| 7 | 1:50 | Contact sheet: choose Maya, Tinted | "Now the teacher picks a child. Maya sees the subject alone, tinted in her red, on black, with the page's words below in her red too. Under each page are automatic checks: is the cut-out taken from the original with no stray specks, is the background plain, do the subject and the words stand out. They are measurements, not approval." |
| 8 | 2:15 | **Approve sheet** | "The teacher approves the whole sheet at once. That approval is tied to this exact picture: change her color, or the subject, and the page needs approval again." |
| 9 | 2:30 | Contact sheet: Leo, Cut-out; **Approve sheet** | "Leo sees the same subject in its real colors, on the left, with the words in large yellow type, line by line as the book prints them. A second sheet, not dozens of decisions." |
| 10 | 2:50 | Open the reader for Maya; arrow key through two pages | "The reader is full screen and calm. Nothing moves unless the teacher presses a key. A child's clicks do nothing. B blanks the screen when the child needs a rest." |
| 11 | 3:10 | Press **T**, switch to Leo, arrow on | "Switching to Leo is instant, because it reuses the saved cut-outs. No new AI work. Versions that were never approved are greyed out; the reader refuses to show them." |
| 12 | 3:25 | Last page: credits screen | "Every book ends with its author, Ashwitha Jayakumar, its illustrator, Nafisa Nandini Crishna, and its license, with a note that it was adapted." |
| 13 | 3:35 | Limits slide | "What we have not done yet: no child with CVI has used Miraai, and it is not yet reviewed by a TVI. The AI's confidence is not proof; the teacher's confirmation is. That is the point of the design." |
| 14 | 3:50 | Title slide | "Miraai: the book's own pictures, adapted for each child, and a teacher in charge of every page. Thank you." |

## If a judge asks how the AI works

- **Finding the subject:** our own small subject model answers first, and only on a page that is clearly about one thing the page's words name. Every other page goes to Gemini. On Animal Homes our model answers 1 page of 16 (the crocodile); the rest go to Gemini. Accuracy comes first.
- **Tracing it:** SAM 2.1 small on the server's CPU traces the subject from the original page. We also trained our own cut-out model from scratch (0.897 IoU on 100 held-out drawn pages against SAM 2.1's 0.906, about 5 times faster on a GPU); it is ready as a fast fallback but not switched on.
- **Credits:** read straight from the PDF's text, no AI, so a name is copied, never invented. The teacher can edit them.
- **Display:** our own image code, no AI: tint, cut-out, faded page, outline, and the words band.

## Words to use and avoid

- Say "checks" or "measured." Never say "verified."
- Say "looks" or "modes." Never say a look matches a CVI phase or is right for a child.
- Say "not yet reviewed by a TVI" until a TVI replies.
- Say exactly what each part does (above). Never say the cut-out model is live.
- Say "about 1 page in 10 with no outside AI call" only for Andrew's test set; on Animal Homes it is 1 page of 16.

## If something breaks

| Problem | Do |
| --- | --- |
| Upload or processing is slow | Use the pre-processed copy of Animal Homes; it is already in the Library |
| Gemini is down | On page 3, use **Draw an outline** around the hornbill instead of Suggestions. It calls no outside AI |
| A cut-out looks wrong on stage | Say so: "this is why the teacher reviews every page," and pick another suggestion or **Add a missing part** |
| The live site is down | Say "we will show our recording," then play the backup video. Never present the video as live |

## Open decisions

- After the reset, most Animal Homes pages arrive Needs subject, because nearly every page names two animals. Step 6 then leaves most pages out. Before the first judge, decide with Andrew: either leave them out on stage (fast, honest), or pick two or three more pages live and cut step 12.
- Check after a reset that page 3 still offers the hornbill, beehive, nest and the combined option; Gemini's answers vary between runs.
- Timing is a guess until the first rehearsal; cut steps 6 and 12 first if over time.
