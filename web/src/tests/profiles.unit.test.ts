/** Profile form rules and the throttled, stale-proof preview. */
import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../api';
import { PREVIEW_INTERVAL_MS, usePreview } from '../hooks/usePreview';
import type { PreviewInput, Profile } from '../types/api';
import { contrastRatio } from '../utils/contrast';
import { DEFAULT_SETTINGS, LEVELS } from '../utils/display';
import { draftFrom, inputFrom, lowContrast, makeMain, sameSettings, toggleColor, validateDraft } from '../utils/profiles';

const RED = '#E53935';
const YELLOW = '#FDD835';
const BLUE = '#1E88E5';
const GREEN = '#43A047';

describe('profile form rules', () => {
  it('looks are shown by name and sent as 1-4', () => {
    expect(LEVELS.map((l) => [l.value, l.name])).toEqual([
      [1, 'Tinted'],
      [2, 'Cut-out'],
      [3, 'Faded page'],
      [4, 'Outlined'],
    ]);
  });

  it('a new child starts with no look chosen, red on black', () => {
    const d = draftFrom();
    expect(d.level).toBeNull();
    expect(d.colors).toEqual([RED]);
    expect(d.background).toBe('#000000');
  });

  it('colors: 1 to 3, added at the end, never empty', () => {
    expect(toggleColor([RED], BLUE)).toEqual([RED, BLUE]);
    expect(toggleColor([RED, BLUE, GREEN], YELLOW)).toEqual([RED, BLUE, GREEN]);
    expect(toggleColor([RED], RED)).toEqual([RED]);
    expect(toggleColor([RED, BLUE], RED)).toEqual([BLUE]);
    expect(toggleColor([RED], '#fdd835')).toEqual([RED, YELLOW]);
  });

  it('make main moves a color to the front', () => {
    expect(makeMain([RED, BLUE, GREEN], GREEN)).toEqual([GREEN, RED, BLUE]);
    expect(makeMain([RED, BLUE], RED)).toEqual([RED, BLUE]);
  });

  it('warns below 3:1 between the main color and the background', () => {
    expect(contrastRatio(YELLOW, '#FFFFFF')!).toBeLessThan(3);
    expect(lowContrast({ colors: [YELLOW], background: '#FFFFFF' })).toBe(true);
    expect(lowContrast({ colors: [RED], background: '#000000' })).toBe(false);
    // Only the main (first) color counts.
    expect(lowContrast({ colors: [BLUE, YELLOW], background: '#FFFFFF' })).toBe(false);
  });

  it('a low-contrast pair needs a note; the note is dropped when the warning no longer applies', () => {
    const d = { ...draftFrom(), name: 'Sam', level: 1 as const, colors: [YELLOW], background: '#FFFFFF' };
    expect(validateDraft(d).note).toBeDefined();
    expect(inputFrom({ ...d, note: '  keeps attention  ' }).contrast_override_note).toBe('keeps attention');
    expect(inputFrom({ ...d, background: '#000000', note: 'old note' }).contrast_override_note).toBeNull();
  });

  it('name and look are required', () => {
    expect(validateDraft(draftFrom())).toMatchObject({ name: expect.any(String), level: expect.any(String) });
  });

  it('size, position and text come from the controls; outline stays as stored', () => {
    const d = { ...draftFrom(), name: 'Sam', level: 2 as const, size: 'large' as const, position: 'left' as const, textMode: 'below' as const };
    const body = inputFrom(d);
    expect(body.settings).toEqual({ ...DEFAULT_SETTINGS, size: 'large', position: 'left', text_mode: 'below' });
  });

  it('saving keeps size, position, text and outline exactly as stored', () => {
    const leo: Profile = {
      id: 'p2',
      name: 'Leo',
      level: 2,
      settings: { colors: [YELLOW, BLUE], background: '#000000', size: 'large', position: 'left', text_mode: 'below', outline: 'thin' },
      settings_hash: 'x',
      contrast_override_note: null,
    };
    const body = inputFrom({ ...draftFrom(leo), background: '#333333' });
    expect(body.settings).toEqual({ ...leo.settings, background: '#333333' });
    expect(Object.keys(body.settings).sort()).toEqual(Object.keys(DEFAULT_SETTINGS).sort());
  });

  it('sameSettings ignores name, look and note (they do not change settings_hash)', () => {
    expect(sameSettings(DEFAULT_SETTINGS, { ...DEFAULT_SETTINGS, colors: ['#e53935'] })).toBe(true);
    expect(sameSettings(DEFAULT_SETTINGS, { ...DEFAULT_SETTINGS, background: '#FFFFFF' })).toBe(false);
    expect(sameSettings({ ...DEFAULT_SETTINGS, colors: [RED, BLUE] }, { ...DEFAULT_SETTINGS, colors: [BLUE, RED] })).toBe(false);
  });
});

describe('usePreview', () => {
  afterEach(() => vi.useRealTimers());

  const input = (bg: string): PreviewInput => ({ page_id: 'pg1', level: 1, settings: { ...DEFAULT_SETTINGS, background: bg } });

  /** api.preview stand-in that answers after `ms`, ignoring aborts (as a slow server would). */
  function fakePreview(ms: (body: PreviewInput) => number) {
    return vi.spyOn(api, 'preview').mockImplementation(
      (body) => new Promise((resolve) => setTimeout(() => resolve(new Blob([body.settings.background])), ms(body))),
    );
  }

  it('asks at most once per 300 ms and always ends on the latest settings', async () => {
    vi.useFakeTimers();
    const spy = fakePreview(() => 5);
    const { rerender, result } = renderHook(({ i }) => usePreview(i), { initialProps: { i: input('#000000') } });
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(spy).toHaveBeenCalledTimes(1);

    for (const bg of ['#111111', '#222222', '#333333', '#444444']) {
      rerender({ i: input(bg) });
      await act(() => vi.advanceTimersByTimeAsync(50));
    }
    expect(spy).toHaveBeenCalledTimes(1);
    await act(() => vi.advanceTimersByTimeAsync(PREVIEW_INTERVAL_MS));
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy.mock.calls[1]![0].settings.background).toBe('#444444');
    await act(() => vi.advanceTimersByTimeAsync(10));
    expect(result.current.current).toBe(true);
    expect(result.current.status).toBe('loaded');
  });

  it('ignores a slow, stale answer that lands after a newer one', async () => {
    vi.useFakeTimers();
    const spy = fakePreview((b) => (b.settings.background === '#000000' ? 1000 : 5));
    const { rerender, result } = renderHook(({ i }) => usePreview(i), { initialProps: { i: input('#000000') } });
    await act(() => vi.advanceTimersByTimeAsync(0));
    rerender({ i: input('#FFFFFF') });
    await act(() => vi.advanceTimersByTimeAsync(PREVIEW_INTERVAL_MS + 10));
    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy.mock.calls[0]![1]?.aborted).toBe(true);
    const shownUrl = result.current.url;
    expect(result.current.current).toBe(true);
    await act(() => vi.advanceTimersByTimeAsync(2000)); // the stale black answer arrives now
    expect(result.current.url).toBe(shownUrl);
    expect(result.current.current).toBe(true);
  });

  it('sends nothing until there is something to preview, and releases the image on unmount', async () => {
    vi.useFakeTimers();
    const spy = fakePreview(() => 1);
    const revoke = vi.spyOn(URL, 'revokeObjectURL');
    const { rerender, unmount, result } = renderHook(({ i }: { i: PreviewInput | null }) => usePreview(i), {
      initialProps: { i: null as PreviewInput | null },
    });
    await act(() => vi.advanceTimersByTimeAsync(1000));
    expect(spy).not.toHaveBeenCalled();
    rerender({ i: input('#000000') });
    await act(() => vi.advanceTimersByTimeAsync(10));
    const url = result.current.url;
    expect(url).not.toBeNull();
    unmount();
    expect(revoke).toHaveBeenCalledWith(url);
  });
});
