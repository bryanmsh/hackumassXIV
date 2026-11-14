import type { HexColor, Level, Profile, ProfileInput, Settings, SubjectPosition, SubjectSize, TextMode } from '../types/api';
import { MIN_SWATCH_CONTRAST, contrastRatio } from './contrast';
import { BACKGROUNDS, DEFAULT_SETTINGS, SWATCHES } from './display';

export const MAX_COLORS = 3;
export const MAX_NAME_LENGTH = 40;
export const MAX_NOTE_LENGTH = 200;

/** What the form edits. Fields without P0 controls ride along unchanged in `base`. */
export interface ProfileDraft {
  name: string;
  level: Level | null;
  colors: HexColor[];
  background: HexColor;
  note: string;
  /** Phase 2 controls. Size and position apply at Tinted and Cut-out; text below applies at every look. */
  size: SubjectSize;
  position: SubjectPosition;
  textMode: TextMode;
  /** The saved settings (or defaults for a new child); `outline` (no control yet) comes from here. */
  base: Settings;
}

export const SIZES: readonly { value: SubjectSize; name: string; hint: string }[] = [
  { value: 'small', name: 'Small', hint: '40% of the picture area' },
  { value: 'medium', name: 'Medium', hint: '60% of the picture area' },
  { value: 'large', name: 'Large', hint: '80% of the picture area' },
];

export const POSITIONS: readonly { value: SubjectPosition; name: string }[] = [
  { value: 'center', name: 'Center' },
  { value: 'left', name: 'Left' },
  { value: 'right', name: 'Right' },
  { value: 'upper', name: 'Upper' },
  { value: 'lower', name: 'Lower' },
];

/** Size and position only change Tinted and Cut-out; Faded page and Outlined keep the book's layout. */
export const LAYOUT_LEVELS: readonly Level[] = [1, 2];

export function draftFrom(profile?: Profile): ProfileDraft {
  if (!profile) {
    return {
      name: '',
      level: null, // the teacher chooses; the app never recommends a look
      colors: [...DEFAULT_SETTINGS.colors],
      background: DEFAULT_SETTINGS.background,
      note: '',
      size: DEFAULT_SETTINGS.size,
      position: DEFAULT_SETTINGS.position,
      textMode: DEFAULT_SETTINGS.text_mode,
      base: { ...DEFAULT_SETTINGS, colors: [...DEFAULT_SETTINGS.colors] },
    };
  }
  return {
    name: profile.name,
    level: profile.level,
    colors: [...profile.settings.colors],
    background: profile.settings.background,
    note: profile.contrast_override_note ?? '',
    size: profile.settings.size,
    position: profile.settings.position,
    textMode: profile.settings.text_mode,
    base: { ...profile.settings, colors: [...profile.settings.colors] },
  };
}

/** The full Contract 2 settings object: the form's colors and background, everything else kept. */
export function settingsFrom(d: ProfileDraft): Settings {
  return { ...d.base, colors: [...d.colors], background: d.background, size: d.size, position: d.position, text_mode: d.textMode };
}

const norm = (hex: string) => hex.toUpperCase();

/** Add a swatch at the end, or remove it. Never below 1 or above 3. */
export function toggleColor(colors: HexColor[], hex: HexColor): HexColor[] {
  const i = colors.findIndex((c) => norm(c) === norm(hex));
  if (i >= 0) return colors.length > 1 ? colors.filter((_, j) => j !== i) : colors;
  return colors.length < MAX_COLORS ? [...colors, norm(hex)] : colors;
}

/** Move a chosen swatch to the front, making it the main color. */
export function makeMain(colors: HexColor[], hex: HexColor): HexColor[] {
  const i = colors.findIndex((c) => norm(c) === norm(hex));
  if (i <= 0) return colors;
  return [colors[i]!, ...colors.filter((_, j) => j !== i)];
}

export function swatchName(hex: string): string {
  return SWATCHES.find((s) => norm(s.hex) === norm(hex))?.name ?? `Custom ${norm(hex)}`;
}

export const isSwatch = (hex: string): boolean => SWATCHES.some((s) => norm(s.hex) === norm(hex));

/** A custom colour: any 6-digit hex (the API accepts any). Returned normalised, or null. */
export function parseCustomColor(input: string): HexColor | null {
  const m = /^#?([0-9a-f]{6})$/i.exec(input.trim());
  return m ? `#${m[1]!.toUpperCase()}` : null;
}

export function backgroundName(hex: string): string {
  return BACKGROUNDS.find((b) => norm(b.hex) === norm(hex))?.name ?? hex;
}

/** Main color against background, 1–21. */
export function mainContrast(d: Pick<ProfileDraft, 'colors' | 'background'>): number | null {
  const main = d.colors[0];
  return main ? contrastRatio(main, d.background) : null;
}

export function lowContrast(d: Pick<ProfileDraft, 'colors' | 'background'>): boolean {
  const r = mainContrast(d);
  return r !== null && r < MIN_SWATCH_CONTRAST;
}

/** Same display settings, so the server's settings_hash (and every approval) is unchanged. */
export function sameSettings(a: Settings, b: Settings): boolean {
  return (
    a.colors.length === b.colors.length &&
    a.colors.every((c, i) => norm(c) === norm(b.colors[i] ?? '')) &&
    norm(a.background) === norm(b.background) &&
    a.size === b.size &&
    a.position === b.position &&
    a.text_mode === b.text_mode &&
    a.outline === b.outline
  );
}

export interface DraftErrors {
  name?: string;
  level?: string;
  colors?: string;
  note?: string;
}

export function validateDraft(d: ProfileDraft): DraftErrors {
  const e: DraftErrors = {};
  if (!d.name.trim()) e.name = 'Enter the child’s first name.';
  if (d.level === null) e.level = 'Choose a look.';
  if (d.colors.length < 1 || d.colors.length > MAX_COLORS) e.colors = 'Choose 1 to 3 colors.';
  if (lowContrast(d) && !d.note.trim()) e.note = 'Write a short note to keep these colors, or pick another pair.';
  return e;
}

/** The request body. The note is kept only while the warning applies. */
export function inputFrom(d: ProfileDraft): ProfileInput {
  if (d.level === null) throw new Error('A look must be chosen before saving.');
  return {
    name: d.name.trim(),
    level: d.level,
    settings: settingsFrom(d),
    contrast_override_note: lowContrast(d) ? d.note.trim() : null,
  };
}
