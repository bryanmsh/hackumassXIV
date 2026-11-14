import type { ReaderManifest } from '../types/api';

/**
 * Where the reader is: an approved page (by id, with its book page number so a
 * position survives a switch to a version that lacks that page), or the
 * credits page that always comes last.
 */
export type Spot = { kind: 'page'; pageId: string; number: number } | { kind: 'credits' };

/** Index into the reading order: 0..pages.length-1 are pages, pages.length is the credits. */
export function indexOf(m: ReaderManifest, spot: Spot): number {
  if (spot.kind === 'credits') return m.pages.length;
  const exact = m.pages.findIndex((p) => p.page_id === spot.pageId);
  if (exact >= 0) return exact;
  // Not approved in this version: go to the next approved page after it, else the credits.
  const after = m.pages.findIndex((p) => p.number >= spot.number);
  return after >= 0 ? after : m.pages.length;
}

export function spotAt(m: ReaderManifest, index: number): Spot {
  const p = m.pages[index];
  return p ? { kind: 'page', pageId: p.page_id, number: p.number } : { kind: 'credits' };
}

/** One step forward or back, stopping at the first page and at the credits. */
export function step(m: ReaderManifest, spot: Spot, delta: 1 | -1): Spot {
  const i = Math.max(0, Math.min(m.pages.length, indexOf(m, spot) + delta));
  return spotAt(m, i);
}

export const sameSpot = (a: Spot | null, b: Spot | null): boolean =>
  a === b || (a !== null && b !== null && (a.kind === 'credits' ? b.kind === 'credits' : b.kind === 'page' && a.pageId === b.pageId));

export const SKIP_REASON_TEXT: Record<string, string> = {
  omitted: 'left out',
  rejected: 'rejected',
  not_approved: 'not approved',
};
