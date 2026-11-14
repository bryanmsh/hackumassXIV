import type { Book, Page, PageState } from '../types/api';

export function countByState(pages: Page[]): Record<PageState, number> {
  const counts: Record<PageState, number> = {
    processing: 0,
    ready: 0,
    needs_subject: 0,
    no_clear_subject: 0,
    failed: 0,
    unsupported: 0,
  };
  for (const p of pages) counts[p.state] += 1;
  return counts;
}

/** True while the server is still working on this book. Drives 2-second polling. */
export function isBookBusy(book: Book): boolean {
  return book.state === 'ingesting' || book.pages.some((p) => p.state === 'processing');
}

export function selectedLabel(page: Page): string | null {
  if (page.selected === null) return null;
  return page.candidates[page.selected]?.label ?? null;
}

/** Pages that are no longer Processing (whatever state they ended in). */
export function processedCount(pages: Page[]): number {
  return pages.filter((p) => p.state !== 'processing').length;
}

/** Pages "Confirm all" would change: a subject is chosen, not yet confirmed, not left out, not processing. */
export function confirmablePages(pages: Page[]): Page[] {
  return pages.filter((p) => p.selected !== null && !p.confirmed && !p.omitted && p.state !== 'processing');
}

/** Pages that still need the teacher: neither confirmed nor left out. */
export function undecidedPages(pages: Page[]): Page[] {
  return pages.filter((p) => !p.confirmed && !p.omitted);
}
