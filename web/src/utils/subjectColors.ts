/**
 * Colours for the suggestions on one page, by their position in `page.candidates`.
 * The server only ever appends suggestions, so a suggestion keeps its colour and
 * number while others are confirmed, joined or added. Six colours (blue, orange,
 * purple, pink, teal, yellow; never green), then they repeat and the number inside
 * the marker tells them apart. The classes are literal so Tailwind can find them.
 */
export interface SubjectTone {
  name: string;
  /** Solid fill for the marker and swatch. */
  fill: string;
  /** Text colour that reads on the fill. */
  ink: string;
  border: string;
  /** Light tint of the same colour, for a button background. */
  tint: string;
  ring: string;
}

export const SUBJECT_TONES: readonly SubjectTone[] = [
  { name: 'blue', fill: 'bg-subject-1', ink: 'text-white', border: 'border-subject-1', tint: 'bg-subject-1/10', ring: 'ring-subject-1' },
  { name: 'orange', fill: 'bg-subject-2', ink: 'text-white', border: 'border-subject-2', tint: 'bg-subject-2/10', ring: 'ring-subject-2' },
  { name: 'purple', fill: 'bg-subject-3', ink: 'text-white', border: 'border-subject-3', tint: 'bg-subject-3/10', ring: 'ring-subject-3' },
  { name: 'pink', fill: 'bg-subject-4', ink: 'text-white', border: 'border-subject-4', tint: 'bg-subject-4/10', ring: 'ring-subject-4' },
  { name: 'teal', fill: 'bg-subject-5', ink: 'text-white', border: 'border-subject-5', tint: 'bg-subject-5/10', ring: 'ring-subject-5' },
  { name: 'yellow', fill: 'bg-subject-6', ink: 'text-slate-950', border: 'border-subject-6', tint: 'bg-subject-6/15', ring: 'ring-subject-6' },
];

export function subjectTone(index: number): SubjectTone {
  const n = SUBJECT_TONES.length;
  return SUBJECT_TONES[((index % n) + n) % n]!;
}

/** The number shown in a suggestion's marker and swatch: 1-based. */
export const subjectNumber = (index: number): number => index + 1;
