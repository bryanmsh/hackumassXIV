import type { BookState, CheckStatus, Level, PageState, Settings } from '../types/api';

/**
 * Display looks are presentation modes, NOT clinical stages or a ladder.
 * The app shows names; the API takes the numbers.
 */
export const LEVELS: readonly { value: Level; name: string; description: string }[] = [
  { value: 1, name: 'Tinted', description: 'The subject alone, tinted in the main color, on a plain background.' },
  { value: 2, name: 'Cut-out', description: 'The subject alone, in its own colors, on a plain background.' },
  { value: 3, name: 'Faded page', description: 'The whole page faded, with the subject kept vivid.' },
  { value: 4, name: 'Outlined', description: 'The original page, with the subject outlined in the main color.' },
];

export function levelName(level: Level): string {
  return LEVELS.find((l) => l.value === level)?.name ?? `Look ${level}`;
}

/** The exact eight swatches from the spec. */
export const SWATCHES: readonly { name: string; hex: string }[] = [
  { name: 'Red', hex: '#E53935' },
  { name: 'Yellow', hex: '#FDD835' },
  { name: 'Orange', hex: '#FB8C00' },
  { name: 'Green', hex: '#43A047' },
  { name: 'Blue', hex: '#1E88E5' },
  { name: 'Purple', hex: '#AB47BC' },
  { name: 'Pink', hex: '#EC407A' },
  { name: 'White', hex: '#FFFFFF' },
];

/**
 * Background choices. The spec names four but gives no hex codes; Andrew
 * confirmed these values are the definition (Kevin's checks use #001F3F too).
 */
export const BACKGROUNDS: readonly { name: string; hex: string }[] = [
  { name: 'Black', hex: '#000000' },
  { name: 'Dark gray', hex: '#333333' },
  { name: 'Navy', hex: '#001F3F' },
  { name: 'White', hex: '#FFFFFF' },
];

/**
 * Defaults for a new child. The page's words are always shown by the display:
 * in place at Faded page and Outlined, below the picture at Tinted and Cut-out.
 * `text_mode: "below"` adds the band below at Faded page and Outlined too.
 */
export const DEFAULT_SETTINGS: Settings = {
  colors: ['#E53935'],
  background: '#000000',
  size: 'medium',
  position: 'center',
  text_mode: 'off',
  outline: 'off',
};

export const PAGE_STATE_LABEL: Record<PageState, string> = {
  processing: 'Processing',
  ready: 'Ready',
  needs_subject: 'Needs subject',
  no_clear_subject: 'No clear subject',
  failed: 'Failed',
  unsupported: 'Unsupported',
};

export const PAGE_STATE_HINT: Record<PageState, string> = {
  processing: 'Work in progress. Review other pages meanwhile.',
  ready: 'The AI suggested a subject. Check it, then confirm or change it.',
  needs_subject: 'The app is unsure which object matters. Pick one.',
  no_clear_subject: 'A scene, a crowd or several equal characters. Pick one or leave the page out.',
  failed: 'Retry, label and outline it by hand, or leave the page out.',
  unsupported: 'A two-page spread or other layout. Leave it out, or process it anyway.',
};

/** Tailwind classes per page state. Calm colors; never the only signal (labels are always shown). */
export const PAGE_STATE_TONE: Record<PageState, string> = {
  processing: 'bg-sky-50 text-sky-800 ring-sky-200',
  // Neutral, not emerald: Ready is the AI's suggestion, not a correct answer. Confirmed is emerald.
  ready: 'bg-white text-slate-800 ring-slate-400',
  needs_subject: 'bg-amber-50 text-amber-900 ring-amber-200',
  no_clear_subject: 'bg-amber-50 text-amber-900 ring-amber-200',
  failed: 'bg-rose-50 text-rose-800 ring-rose-200',
  unsupported: 'bg-slate-100 text-slate-700 ring-slate-300',
};

export const BOOK_STATE_LABEL: Record<BookState, string> = {
  ingesting: 'Reading PDF',
  ready: 'Pages created',
  failed: 'Failed',
};

export const CHECK_TONE: Record<CheckStatus, string> = {
  pass: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  warn: 'bg-amber-50 text-amber-900 ring-amber-200',
  fail: 'bg-rose-50 text-rose-800 ring-rose-200',
};

/** The AI's own confidence as a whole percentage ("85%"). It is the AI's guess, never a score of correctness. */
export function formatConfidence(c: number): string {
  return `${Math.round(Math.min(1, Math.max(0, c)) * 100)}%`;
}

/**
 * Where a subject came from, in words. "manual" covers both a teacher's drawn
 * outline and suggestions the teacher joined together, so it reads "made by
 * teacher" (never "outlined", which is untrue for a joined subject).
 */
export function sourceLabel(source: string): string {
  if (source === 'manual') return 'made by teacher';
  if (source === 'click') return 'picked by clicking';
  return 'suggested by the AI';
}
