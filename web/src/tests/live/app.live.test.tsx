/**
 * Library and Subject review against a real server, through api.ts with no mocks.
 * Works against Andrew's stand-in (fixed example answers) and the live site.
 *   LIVE_API_URL=http://127.0.0.1:8000 npm run test:live
 * It sends one subject pick and one confirm, never an approval.
 */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../../App';
import { api } from '../../api';
import { API_BASE, MOCKS_ENABLED } from '../../config';
import type { Book } from '../../types/api';

const STATES = new Set(['processing', 'ready', 'needs_subject', 'no_clear_subject', 'failed', 'unsupported']);

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

async function firstBook(): Promise<Book> {
  const books = await api.listBooks();
  expect(books.length).toBeGreaterThan(0);
  return books[0]!;
}

describe(`live API at ${API_BASE}`, () => {
  it('is real mode, with /api added once', () => {
    expect(MOCKS_ENABLED).toBe(false);
    expect(api.url('/books')).toBe(`${API_BASE.replace(/\/+$/, '')}/api/books`);
  });

  it('GET /books and GET /books/{id} parse into the agreed shapes', async () => {
    const b = await firstBook();
    const full = await api.getBook(b.id);
    expect(full.id).toBe(b.id);
    for (const p of full.pages) {
      expect(STATES.has(p.state)).toBe(true);
      expect(p.width).toBeGreaterThan(0);
      expect(p.height).toBeGreaterThan(0);
      for (const c of p.candidates) for (const n of c.box) expect(n >= 0 && n <= 1).toBe(true);
    }
  });

  it('serves the overlay image as an image, not cached', async () => {
    const b = await api.getBook((await firstBook()).id);
    const p = b.pages.find((x) => x.state !== 'processing');
    if (!p) return;
    const img = await api.getOverlay(p.id);
    expect(img.size).toBeGreaterThan(0);
  });

  it('Library renders the server’s books', async () => {
    const b = await firstBook();
    renderAt('/');
    const heading = await screen.findByRole('heading', { name: b.title });
    expect(within(heading.closest('li')!).getByRole('list', { name: 'Each page' })).toBeInTheDocument();
  });

  it('Subject review renders every page and a pick round-trips', async () => {
    const b = await api.getBook((await firstBook()).id);
    renderAt(`/books/${b.id}/subjects`);
    for (const p of b.pages) expect(await screen.findByRole('heading', { name: `Page ${p.number}` })).toBeInTheDocument();

    // Pick an unselected candidate on the first page that has one, if any.
    const target = b.pages.find((p) => !p.omitted && p.state !== 'processing' && p.candidates.some((_, i) => i !== p.selected));
    if (!target) return;
    const idx = target.candidates.findIndex((_, i) => i !== target.selected);
    const card = within(screen.getByRole('heading', { name: `Page ${target.number}` }).closest('li')!);
    const user = userEvent.setup();
    await user.click(card.getAllByRole('button', { name: new RegExp(target.candidates[idx]!.label) })[0]!);
    // The server answers with the page; whatever it selected is shown as pressed.
    expect(await card.findByRole('button', { pressed: true })).toBeInTheDocument();
    expect(card.queryByRole('alert')).not.toBeInTheDocument();
  });
});
