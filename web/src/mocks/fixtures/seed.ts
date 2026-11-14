/**
 * ⚠️ MOCK FIXTURES — proposed shapes only, NOT the Andrew–Thomas agreed examples.
 * Book titles, credits and children are placeholders. Children are fictional.
 */
import type { Candidate, Credits, NormPoint, PageFlag, PageKind, PageState } from '../../types/api';

export interface PageSpec {
  text: string;
  /** Size of the placeholder image in px; only the aspect ratio matters. */
  width: number;
  height: number;
  flags: PageFlag[];
  outcome: {
    state: Exclude<PageState, 'processing'>;
    page_kind: PageKind | null;
    candidates: Omit<Candidate, 'mask_hash'>[];
    selected: number | null;
    reason: string | null;
  };
  /** Outline for manual candidates, by candidate index. */
  outlines?: Record<number, NormPoint[]>;
}

export const PLACEHOLDER_CREDITS: Credits = {
  author: 'Placeholder Author',
  illustrator: 'Placeholder Illustrator',
  publisher: 'Placeholder Publisher',
  source: 'Mock fixture (replace with StoryWeaver source URL)',
  license: 'CC BY 4.0',
};

const auto = (label: string, synonyms: string[], box: [number, number, number, number], confidence: number) => ({
  label,
  synonyms,
  box,
  confidence,
  source: 'auto' as const,
});

/** Six pages that cover every final page state, modeled on the demo plan. */
export const DEMO_PAGES: PageSpec[] = [
  {
    text: 'A weaver bird builds its nest from grass.',
    width: 1600,
    height: 1200,
    flags: [],
    outcome: {
      state: 'ready',
      page_kind: 'single',
      candidates: [auto('weaver bird', ['bird'], [0.38, 0.22, 0.66, 0.62], 0.88)],
      selected: 0,
      reason: null,
    },
  },
  {
    text: 'Spiders spin their homes.',
    width: 1600,
    height: 1200,
    flags: [],
    outcome: {
      state: 'ready',
      page_kind: 'single',
      candidates: [
        auto('spider', ['arachnid'], [0.42, 0.3, 0.6, 0.55], 0.84),
        auto('web', ['spider web'], [0.2, 0.1, 0.85, 0.85], 0.41),
      ],
      selected: 0,
      reason: null,
    },
  },
  {
    text: 'The hornbill, the bees and the birds all live in the same tree.',
    width: 1600,
    height: 1200,
    flags: [],
    outcome: {
      state: 'needs_subject',
      page_kind: 'several',
      candidates: [
        auto('hornbill', ['bird'], [0.08, 0.18, 0.36, 0.6], 0.62),
        auto('beehive', ['hive', 'bees'], [0.44, 0.12, 0.62, 0.42], 0.58),
        auto('nest', ['bird nest'], [0.66, 0.5, 0.92, 0.78], 0.55),
      ],
      selected: null,
      reason: 'Several subjects of equal weight.',
    },
  },
  {
    text: 'Everyone in the forest has a home.',
    width: 1600,
    height: 1200,
    flags: [],
    outcome: {
      state: 'no_clear_subject',
      page_kind: 'scene',
      candidates: [auto('termite mound', ['mound'], [0.55, 0.35, 0.8, 0.9], 0.38)],
      selected: null,
      reason: 'The page is a scene with no single subject.',
    },
  },
  {
    text: 'Tiny termites build tall, tall homes.',
    width: 1600,
    height: 1200,
    flags: [],
    outcome: {
      state: 'failed',
      page_kind: null,
      candidates: [],
      selected: null,
      reason: 'Timed out waiting for the subject service (20 s).',
    },
  },
  {
    text: 'Homes under the sea and homes in the sky.',
    width: 3000,
    height: 1000,
    flags: ['spread'],
    outcome: {
      state: 'unsupported',
      page_kind: null,
      candidates: [],
      selected: null,
      reason: 'Looks like a two-page spread.',
    },
  },
];

/** A fully processed, confirmed backup book (portrait pages, to exercise letterboxing). */
export const BACKUP_PAGES: PageSpec[] = [
  {
    text: 'The duck swims.',
    width: 1200,
    height: 1600,
    flags: [],
    outcome: {
      state: 'ready',
      page_kind: 'single',
      candidates: [auto('duck', ['bird'], [0.3, 0.35, 0.72, 0.68], 0.91)],
      selected: 0,
      reason: null,
    },
  },
  {
    text: 'The duck finds a ball.',
    width: 1200,
    height: 1600,
    flags: [],
    outcome: {
      state: 'ready',
      page_kind: 'single',
      candidates: [auto('ball', ['toy'], [0.4, 0.45, 0.62, 0.62], 0.86)],
      selected: 0,
      reason: null,
    },
  },
  {
    text: 'The duck goes to sleep.',
    width: 1200,
    height: 1600,
    flags: ['low_quality'],
    outcome: {
      state: 'needs_subject',
      page_kind: 'single',
      candidates: [auto('duck', ['bird'], [0.25, 0.4, 0.75, 0.75], 0.66)],
      selected: 0,
      reason: 'Confidence below the threshold.',
    },
  },
];

/** Outcomes cycled through for newly uploaded mock books. */
export const UPLOAD_PAGES: PageSpec[] = DEMO_PAGES;
