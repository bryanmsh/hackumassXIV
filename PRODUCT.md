# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Primary: a teacher of students with visual impairments (TVI).** They adapt picture books by hand today, so each child gets only a few. They work at a desktop or laptop browser, one book at a time, reviewing pages and approving versions before reading with a child.
- **Secondary (from the spec, not yet validated):** parents reading at home; early-intervention and special-education staff. Buyers are school district special-education budgets and CVI organizations.
- **The child** (with cortical visual impairment, CVI) is the audience of the reader and never the operator. Teacher and child share the same desktop or laptop browser; tablets and touch gestures are not a target.

## Product Purpose

Miraai adapts picture-book pages for children with CVI using the book's own artwork, and keeps the teacher in control of what each child sees. A teacher uploads a PDF; the app finds the subject of each page once, cuts it out of the original page, and re-displays that same cut-out per child profile. The slow AI work happens once per book; everything after is fast, repeatable display from saved parts.

Success right now (HackUMass XIV demo): a judge watches the six-page *Animal Homes* flow end to end, including the one page the AI gets wrong, the one-click teacher fix, and approval of contact sheets for Maya and Leo, and trusts the tool because it admits uncertainty and keeps a person in charge. A later classroom pilot is not the current goal.

## Positioning

The subject always comes from the original page through a mask; nothing is drawn or invented by AI. Tinting, resizing, repositioning and outlines are display changes on top of that cut-out. A teacher approves every version before a child sees it. A generic image filter or a general-purpose image model cannot truthfully make either promise.

## Operating Context

- Flow: upload PDF (up to 30 pages, 50 MB) → per-page processing → teacher subject review (confirm, pick another, hand-outline, or leave out) → child profiles → contact sheet per child and level → teacher approves → full-screen reader paced by the teacher → credits screen.
- Page states: Processing, Ready, Needs subject, No clear subject, Failed, Unsupported. Every page ends in a clear state and one failed page never blocks the rest.
- Reader: one approved page at a time, full screen. Nothing moves unless the teacher moves it: no auto-advance, no animation or flashing transitions, no visible buttons, a child's clicks do nothing. Keys: arrows or space turn pages, T opens the teacher bar, B blank screen (P1). Switching child or level takes under a second from saved cut-outs.
- Four looks, shown by name, sent as numbers 1 to 4: Tinted, Cut-out, Faded page, Outlined. They are presentation modes, not a ladder.
- Demo profiles are fictional: Maya (Tinted, red, black background) and Leo (Cut-out, yellow and blue, black background, left, text below the picture).
- Book pages are sent to an outside AI service to find the subject; the upload screen says so.

## Capabilities and Constraints

- Stack in place: React 18, Vite, TypeScript, Tailwind CSS in `web/`; FastAPI API; our own subject model for subject choosing (Gemini until 2026-11-15); our cut-out model with SAM 2.1 behind it for cut-outs. Atkinson Hyperlegible is the chosen text font.
- Automatic checks (subject match, source fidelity, page edge, background detail, subject visibility, second look) say the adaptation was built correctly. Only the teacher approves. Each measurement is reported on its own; there is no combined score.
- An approval is tied to one page, one cut-out, one profile's settings and one look; changing any of them requires approval again.
- Positions in the API are 0 to 1 fractions of page size.
- Contrast ratios (3:1 swatch vs background, 4.5:1 text) and the 15% and one-half targets are engineering starting points, not clinical CVI thresholds.
- Out of scope: diagnosing CVI or recommending a look, live camera mode, accounts, sharing between teachers, commercial books.
- Undecided: whether *Animal Homes* is the demo book; which six pages; whether a sheet can approve several looks for one child.

## Brand Commitments

- Name: Miraai.
- Never label a page "verified". Never claim a look matches a clinical CVI phase, recommend a look for a child, or claim a child can see or understand a page. Binding for UI and marketing copy alike.

## Evidence on Hand

- No child with CVI has used the tool and no TVI has reviewed it. A TVI email with mock-ups is drafted (`pitch/tvi_email.md`, `pitch/tvi_mockups/`); until a TVI replies, public statements say "not yet reviewed by a TVI."
- Demo content: *Animal Homes* from StoryWeaver (CC BY 4.0, credits and license must be kept and changes noted). A 20-page hand-labeled StoryWeaver evaluation set is planned (P1); results are reported as counts, not percentages. No measured results exist yet. Do not fabricate testimonials, accuracy numbers or customers.

## Product Principles

1. **The teacher decides.** The app flags uncertainty and shows its reasoning; it never auto-approves, and a person's confirmation outranks any model confidence.
2. **Original pixels only.** Every display is the book's own art, altered only by tint, size, position or outline, and the untouched original is always kept.
3. **Say what the checks mean.** Checks report measured facts, one by one; they are never presented as proof, a score, or "verified."
4. **The child's screen is calm.** Nothing moves, advances or invites a touch unless the teacher acts.
5. **Admit failure and recover.** Every page has a clear state and a manual path (label and outline by hand) that works even when the AI services are down.

## Accessibility & Inclusion

- The audience has CVI: simple pictures, one object, little clutter, strong contrast. Children can need extra processing time, so pacing is entirely teacher-controlled.
- Teacher-facing screens use Atkinson Hyperlegible; any text shown to the child is large and checked at 4.5:1.
- Keyboard operation of the reader is a requirement, not an extra, since it is the only input method.
