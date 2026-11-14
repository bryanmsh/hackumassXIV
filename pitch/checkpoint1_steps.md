# Checkpoint 1: step list (hour 8)

Goal from the plan: **one book flows end to end on the live site**, even if slowly or roughly.
Run it together on one screen. Tick each step, and write what broke in the last column.

Book: `fixtures/animal-homes-pratham-FKB.pdf` (5 pages, StoryWeaver, CC BY 4.0).
Expected from Kevin's local run of Bryan's pipeline: page 1 No clear subject, pages 2 to 5 Needs subject, nothing pre-selected, about 1 minute for the whole book. With Bryan's newer pipeline (not in `main` yet at 15:20), most pages arrive Ready with a combined pick such as "beehive, bird and bird nest"; step 6 then switches it to the hornbill alone.

| # | Who clicks | Where | Do | Expect | OK? | What broke |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Thomas | Live site | Open the site URL in a fresh private window | Password prompt, then the Library | | |
| 2 | Thomas | Library | **Choose a PDF**, pick Animal Homes, fill the five credit fields (author, illustrator, publisher, source, license "CC BY 4.0"), **Upload** | The book appears at once as "Reading PDF" | | |
| 3 | Everyone | Library | Wait, without refreshing | Counts move every 2 s; every page ends in a state; none stuck in Processing | | |
| 4 | Thomas | Subject review | Open the book | 5 cards, each with the overlay, label and confidence, and the page state | | |
| 5 | Thomas | Subject review, page 1 | **Leave out** the cover | "This page is skipped in the reader." | | |
| 6 | Thomas | Subject editor, page 2 | **Suggestions**: pick the hornbill (bird) | The highlight moves to the bird; confirm it | | |
| 7 | Thomas | Subject editor, page 3 | **Tap the object** on the spider | A new cut-out appears where the click was; confirm it | | |
| 8 | Thomas | Subject editor, page 4 | **Draw an outline** around one tortoise, label it "tortoise" | The cut-out sits exactly where it was drawn (the hour-6 alignment check, again) | | |
| 9 | Thomas | Subject editor, page 5 | **Suggestions**: pick a frog; confirm | Confirmed badge | | |
| 10 | Thomas | Profiles | New profile, any name; switch **Look** through Tinted, Cut-out, Faded page, Outlined on one page | The live preview changes to each look within about a second, without saving | | |
| 11 | Kevin | Laptop | `MIRAI_URL=<site> pytest tests` (only if nobody minds "zz-test" books on the live site) | 5 passed | | |

**Passes when:** steps 1 to 10 work on the live site. Slow or rough is fine at this checkpoint.

## Things to watch for (from Kevin's local runs)

- The spider's cut-out may include a patch of web and leaves (GrabCut). If so, try **Tap the object** on the spider's body and compare.
- The tortoise cut-outs may miss the head. Not a blocker; note it for Bryan.
- Contrast warnings on the hornbill at Tinted and Cut-out are real: a dark bird on black.
- Render speed on the laptop was 184 ms per page for real pages; on the server it should be faster. Note it if the preview feels slow.

## After the checkpoint

- Write every "What broke" item into the team chat with an owner.
- Anyone more than two hours behind gets a partner until checkpoint 2.
