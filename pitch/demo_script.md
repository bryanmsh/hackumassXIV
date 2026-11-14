# Mirai demo script (first draft, for checkpoint 2)

Target length: 4 minutes. Six pages of *Animal Homes*, two fictional children, four levels.

| # | Time | On screen | Say |
| --- | --- | --- | --- |
| 1 | 0:00 | Title slide | Children with CVI recognize one clear object on a plain background far better than a busy picture-book page. Teachers rebuild pages by hand, so each child gets only a few books. |
| 2 | 0:25 | Library: upload six pages | Mirai uses the book's own artwork. It sends each page to an AI once to find the subject, and the upload screen says so. |
| 3 | 0:45 | Pages reach their states | Every page ends in a clear state: Ready, Needs subject, No clear subject, or Failed. One bad page never blocks the rest. |
| 4 | 1:05 | Subject review grid | The subject is what the story is about, not the biggest thing. The app shows its choice and its confidence, and the teacher confirms. |
| 5 | 1:25 | Page 3: hornbill, beehive, nest | Here the app is honestly unsure: three subjects of equal weight. It does not guess. The teacher fixes it with one click. |
| 6 | 1:50 | Contact sheet for Maya | Checks rerun: the cut-out comes from the original page in one piece, the background is plain, contrast is measured. The teacher approves the whole sheet at once. |
| 7 | 2:20 | Contact sheet for Leo | Same pages, Leo's settings: real colors, yellow and blue, subject on the left, large text. A second sheet, not 160 decisions. |
| 8 | 2:45 | Reader, Maya then Leo | Full screen, nothing moves unless the teacher moves it. A child's touch does nothing. Switching from Maya to Leo is instant, with no new AI work. |
| 9 | 3:20 | Credits screen | Every book ends with its author, illustrator and CC BY license, noting that pages were adapted. |
| 10 | 3:35 | Limits slide | No child with CVI has used it yet, and no TVI has reviewed it yet. The AI's confidence is not proof; the teacher's confirmation is. |

## Backup plan

- If the upload is slow, open a pre-processed backup book.
- If Gemini is down, show the hand-drawn outline on page 3 instead of the one-click fix. It calls no model.
- Have the screen recording open in another tab.

## To fill in after checkpoint 1

- Which page is actually the hard page.
- Real timings: processing per page and switch time.
