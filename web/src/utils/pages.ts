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
