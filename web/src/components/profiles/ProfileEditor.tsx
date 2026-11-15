import { useId, useMemo, useState, type FormEvent } from 'react';
import { api } from '../../api';
import { useAction } from '../../hooks/useAction';
import type { Profile } from '../../types/api';
import { MIN_SWATCH_CONTRAST } from '../../utils/contrast';
import { BACKGROUNDS, LEVELS, SWATCHES, levelName } from '../../utils/display';
import {
  LAYOUT_LEVELS,
  MAX_COLORS,
  POSITIONS,
  SIZES,
  MAX_NAME_LENGTH,
  MAX_NOTE_LENGTH,
  backgroundName,
  draftFrom,
  inputFrom,
  isSwatch,
  parseCustomColor,
  lowContrast,
  mainContrast,
  makeMain,
  sameSettings,
  settingsFrom,
  swatchName,
  toggleColor,
  validateDraft,
  type DraftErrors,
  type ProfileDraft,
} from '../../utils/profiles';
import { Button } from '../ui/Button';
import { errorMessage } from '../ui/LoadState';
import { ProfilePreview } from './ProfilePreview';

const inputClass =
  'mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-600/30';

/**
 * Create or edit a child's display profile. Trying colors and looks only
 * changes the live preview; nothing reaches the server until Save.
 */
export function ProfileEditor({
  profile,
  onSaved,
  onCancel,
}: {
  profile?: Profile;
  onSaved: (p: Profile, created: boolean) => void;
  onCancel: () => void;
}) {
  const ids = useId();
  const [draft, setDraft] = useState<ProfileDraft>(() => draftFrom(profile));
  const [errors, setErrors] = useState<DraftErrors>({});
  const [custom, setCustom] = useState('#1E88E5');
  const customColors = draft.colors.filter((c) => !isSwatch(c));
  const customValid = parseCustomColor(custom);
  const customFull = draft.colors.length >= MAX_COLORS;
  const save = useAction();
  const settings = useMemo(() => settingsFrom(draft), [draft]);
  const ratio = mainContrast(draft);
  const low = lowContrast(draft);
  const settingsChanged = profile !== undefined && !sameSettings(profile.settings, settings);

  const set = (patch: Partial<ProfileDraft>) => setDraft((d) => ({ ...d, ...patch }));

  async function submit(e: FormEvent) {
    e.preventDefault();
    const found = validateDraft(draft);
    setErrors(found);
    if (Object.keys(found).length) return;
    const body = inputFrom(draft);
    const saved = await save.run('save', (s) => (profile ? api.updateProfile(profile.id, body, s) : api.createProfile(body, s)));
    if (saved) onSaved(saved, !profile);
  }

  return (
    <form
      onSubmit={submit}
      noValidate
      aria-labelledby={`${ids}-h`}
      className="grid gap-6 rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]"
    >
      <div className="space-y-6">
        <h2 id={`${ids}-h`} className="text-2xl font-bold">
          {profile ? `Edit ${profile.name}` : 'New child profile'}
        </h2>

        <div>
          <label htmlFor={`${ids}-name`} className="font-semibold">
            First name
          </label>
          <input
            id={`${ids}-name`}
            className={inputClass}
            value={draft.name}
            maxLength={MAX_NAME_LENGTH}
            autoComplete="off"
            aria-invalid={errors.name ? true : undefined}
            aria-describedby={`${ids}-name-hint`}
            onChange={(e) => set({ name: e.target.value })}
          />
          <p id={`${ids}-name-hint`} className="mt-1 text-sm text-slate-600">
            First name only. The demo uses fictional children.
          </p>
          {errors.name && <FieldError>{errors.name}</FieldError>}
        </div>

        <fieldset>
          <legend className="font-semibold">Look</legend>
          <p className="text-sm text-slate-600">
            Looks are ways of showing the page, not stages or steps. Any look can suit any child; Miraai does not recommend one.
          </p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {LEVELS.map((l) => (
              <label
                key={l.value}
                className={`flex min-h-11 cursor-pointer gap-3 rounded-lg p-3 ring-1 ring-inset ${
                  draft.level === l.value ? 'bg-sky-50 ring-2 ring-sky-600' : 'ring-slate-300 hover:bg-slate-50'
                }`}
              >
                <input
                  type="radio"
                  name={`${ids}-level`}
                  value={l.value}
                  checked={draft.level === l.value}
                  onChange={() => set({ level: l.value })}
                  className="mt-1 size-5"
                />
                <span>
                  <span className="block font-semibold">{l.name}</span>
                  <span className="block text-sm text-slate-600">{l.description}</span>
                </span>
              </label>
            ))}
          </div>
          {errors.level && <FieldError>{errors.level}</FieldError>}
        </fieldset>

        <fieldset>
          <legend className="font-semibold">The page’s words</legend>
          <p className="text-sm text-slate-600">
            A picture book is words and pictures, so the words are always shown. At Faded page and Outlined they stay where
            the book put them, as vivid as the subject. At Tinted and Cut-out, where the page itself is gone, they are drawn
            large and bold in a band under the picture, in the child’s main colour when it stands out from the background.
          </p>
          <label className="mt-2 flex min-h-11 w-fit cursor-pointer items-center gap-3 rounded-lg px-2 ring-1 ring-inset ring-slate-300 hover:bg-slate-50">
            <input
              type="checkbox"
              className="size-6"
              checked={draft.textMode === 'below'}
              onChange={(e) => set({ textMode: e.target.checked ? 'below' : 'off' })}
            />
            Also show the words below the picture at Faded page and Outlined
          </label>
        </fieldset>

        <fieldset>
          <legend className="font-semibold">Colors</legend>
          <p className="text-sm text-slate-600">
            Choose 1 to 3. The first is the main color: it tints the subject in Tinted and draws the outline in Outlined.
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            {SWATCHES.map((s) => {
              const pos = draft.colors.findIndex((c) => c.toUpperCase() === s.hex.toUpperCase());
              const on = pos >= 0;
              const full = !on && draft.colors.length >= MAX_COLORS;
              const only = on && draft.colors.length === 1;
              return (
                <button
                  key={s.hex}
                  type="button"
                  aria-pressed={on}
                  disabled={full || only}
                  title={full ? 'Up to 3 colors. Remove one to add another.' : only ? 'At least one color is needed.' : undefined}
                  onClick={() => set({ colors: toggleColor(draft.colors, s.hex) })}
                  className={`flex min-h-11 items-center gap-2 rounded-full py-1 pl-1 pr-3 ring-1 ring-inset disabled:cursor-not-allowed ${
                    on ? 'bg-sky-50 font-semibold ring-2 ring-sky-700' : 'bg-white ring-slate-300 hover:bg-slate-50 disabled:opacity-50'
                  }`}
                >
                  <span className="size-8 rounded-full ring-1 ring-slate-400" style={{ backgroundColor: s.hex }} aria-hidden />
                  {s.name}
                  {pos === 0 && <span className="text-sm text-sky-800"> (main)</span>}
                  {pos > 0 && <span className="text-sm text-slate-600"> ({pos + 1})</span>}
                </button>
              );
            })}
          </div>
          {/* Why some swatches are off, said in view (not only in a tooltip). */}
          {draft.colors.length >= MAX_COLORS && <p className="mt-2 text-sm text-slate-600">Up to 3 colors. Remove one to add another.</p>}
          {draft.colors.length === 1 && <p className="mt-2 text-sm text-slate-600">At least one color is needed, so the last one cannot be removed.</p>}
          <div className="mt-3 rounded-lg bg-slate-50 p-3 ring-1 ring-inset ring-slate-200">
            <label htmlFor={`${ids}-custom`} className="font-semibold">
              Custom color <span className="font-normal text-slate-600">(optional)</span>
            </label>
            <p className="text-sm text-slate-600">Any color, when none of the eight suits this child. It counts toward the three.</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <input
                id={`${ids}-custom`}
                type="color"
                className="size-11 cursor-pointer rounded-lg border border-slate-300 bg-white p-1"
                value={customValid ?? '#000000'}
                onChange={(e) => setCustom(e.target.value.toUpperCase())}
                aria-describedby={`${ids}-custom-hex`}
              />
              <label htmlFor={`${ids}-custom-hex`} className="font-semibold">
                Hex code
              </label>
              <input
                id={`${ids}-custom-hex`}
                className="w-32 rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-base"
                value={custom}
                maxLength={7}
                autoComplete="off"
                spellCheck={false}
                onChange={(e) => setCustom(e.target.value)}
              />
              <Button
                disabled={!customValid || customFull || draft.colors.some((c) => c.toUpperCase() === customValid)}
                onClick={() => customValid && set({ colors: toggleColor(draft.colors, customValid) })}
              >
                Add this color
              </Button>
              {!customValid && <span className="text-sm text-rose-800">Use a 6-digit code such as #1E88E5.</span>}
            </div>
            {customColors.length > 0 && (
              <ul className="mt-2 flex flex-wrap gap-2" aria-label="Custom colors chosen">
                {customColors.map((c) => (
                  <li key={c} className="flex min-h-11 items-center gap-2 rounded-full bg-sky-50 py-1 pl-1 pr-2 font-semibold ring-2 ring-sky-700">
                    <span className="size-8 rounded-full ring-1 ring-slate-400" style={{ backgroundColor: c }} aria-hidden />
                    {swatchName(c)}
                    {draft.colors[0]?.toUpperCase() === c.toUpperCase() && <span className="text-sm text-sky-800">(main)</span>}
                    <Button
                      variant="ghost"
                      className="min-h-9 px-2 py-1 text-sm"
                      disabled={draft.colors.length === 1}
                      aria-label={`Remove ${swatchName(c)}`}
                      onClick={() => set({ colors: toggleColor(draft.colors, c) })}
                    >
                      Remove
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          {draft.colors.length > 1 && (
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
              <span className="text-slate-700">Main color:</span>
              {draft.colors.slice(1).map((c) => (
                <Button key={c} variant="ghost" className="min-h-9 px-2 py-1 text-sm" onClick={() => set({ colors: makeMain(draft.colors, c) })}>
                  Make {swatchName(c)} main
                </Button>
              ))}
            </div>
          )}
          {errors.colors && <FieldError>{errors.colors}</FieldError>}
        </fieldset>

        <fieldset>
          <legend className="font-semibold">Background</legend>
          <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {BACKGROUNDS.map((b) => (
              <label
                key={b.hex}
                className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-lg p-2 ring-1 ring-inset ${
                  draft.background.toUpperCase() === b.hex.toUpperCase() ? 'bg-sky-50 ring-2 ring-sky-600' : 'ring-slate-300 hover:bg-slate-50'
                }`}
              >
                <input
                  type="radio"
                  name={`${ids}-bg`}
                  value={b.hex}
                  checked={draft.background.toUpperCase() === b.hex.toUpperCase()}
                  onChange={() => set({ background: b.hex })}
                  className="size-5"
                />
                <span className="size-7 rounded ring-1 ring-slate-400" style={{ backgroundColor: b.hex }} aria-hidden />
                <span>{b.name}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="font-semibold">Subject size</legend>
          <p className="text-sm text-slate-600">
            How much of the picture the subject fills, in Tinted and Cut-out. Faded page and Outlined keep the book’s own layout.
          </p>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {SIZES.map((o) => (
              <label
                key={o.value}
                className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-lg p-2 ring-1 ring-inset ${
                  draft.size === o.value ? 'bg-sky-50 ring-2 ring-sky-600' : 'ring-slate-300 hover:bg-slate-50'
                }`}
              >
                <input type="radio" name={`${ids}-size`} value={o.value} checked={draft.size === o.value} onChange={() => set({ size: o.value })} className="size-5" />
                <span>
                  <span className="block font-semibold">{o.name}</span>
                  <span className="block text-sm text-slate-600">{o.hint}</span>
                </span>
              </label>
            ))}
          </div>
          {draft.level !== null && !LAYOUT_LEVELS.includes(draft.level) && (
            <p className="mt-1 text-sm text-slate-600">Not used in {levelName(draft.level)}; kept for Tinted and Cut-out.</p>
          )}
        </fieldset>

        <fieldset>
          <legend className="font-semibold">Subject position</legend>
          <p className="text-sm text-slate-600">
            Where the subject sits on the page, in Tinted and Cut-out. Some children see better in one part of their visual field;
            that is the teacher’s call.
          </p>
          <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-5">
            {POSITIONS.map((o) => (
              <label
                key={o.value}
                className={`flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-lg p-2 ring-1 ring-inset ${
                  draft.position === o.value ? 'bg-sky-50 font-semibold ring-2 ring-sky-600' : 'ring-slate-300 hover:bg-slate-50'
                }`}
              >
                <input type="radio" name={`${ids}-position`} value={o.value} checked={draft.position === o.value} onChange={() => set({ position: o.value })} className="size-5" />
                {o.name}
              </label>
            ))}
          </div>
        </fieldset>

        {low && ratio !== null && (
          <div role="alert" className="space-y-2 rounded-lg bg-amber-50 p-4 text-amber-950 ring-1 ring-amber-300">
            <p className="font-semibold">
              {swatchName(draft.colors[0] ?? '')} on {backgroundName(draft.background).toLowerCase()} has a contrast of{' '}
              {ratio.toFixed(1)} to 1, below {MIN_SWATCH_CONTRAST} to 1.
            </p>
            <p className="text-sm">
              This guide comes from web accessibility rules for text. It is an engineering starting point, not a clinical rule
              for CVI. At Cut-out and Faded page the subject keeps its own colors, so this check says less there.
            </p>
            <div>
              <label htmlFor={`${ids}-note`} className="font-semibold">
                To keep these colors, say why
              </label>
              <textarea
                id={`${ids}-note`}
                className={inputClass}
                rows={2}
                maxLength={MAX_NOTE_LENGTH}
                value={draft.note}
                aria-invalid={errors.note ? true : undefined}
                onChange={(e) => set({ note: e.target.value })}
              />
            </div>
            {errors.note && <FieldError>{errors.note}</FieldError>}
          </div>
        )}

        {settingsChanged && (
          <p className="rounded-lg bg-sky-50 p-3 text-sky-950 ring-1 ring-sky-200">
            Saving these colors means pages approved for {profile.name} need approval again. Changing back to the old colors
            later brings those approvals back.
          </p>
        )}
        {save.error && (
          <p role="alert" className="rounded-lg bg-rose-50 p-3 text-rose-900 ring-1 ring-rose-200">
            Not saved: {errorMessage(save.error)}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          <Button type="submit" variant="primary" disabled={save.pending !== null}>
            {save.pending ? 'Saving…' : profile ? 'Save changes' : 'Save profile'}
          </Button>
          <Button onClick={onCancel} disabled={save.pending !== null}>
            Cancel
          </Button>
        </div>
      </div>

      <div className="xl:sticky xl:top-4 xl:self-start">
        <ProfilePreview settings={settings} level={draft.level} />
      </div>
    </form>
  );
}

function FieldError({ children }: { children: React.ReactNode }) {
  return (
    <p role="alert" className="mt-1 font-semibold text-rose-800">
      {children}
    </p>
  );
}
