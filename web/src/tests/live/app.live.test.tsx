/**
 * The app against a real server, through api.ts with no mocks.
 *   LIVE_API_URL=https://140-82-15-107.sslip.io LIVE_API_AUTH=user:pw npm run test:live
 *
 * READ-ONLY by default: lists, pages, images, and POST /preview (which stores
 * nothing). Tests that change data (a subject pick, a point, an outline) run
 * only with LIVE_ALLOW_WRITES=1: on the real API they change a page's subject,
 * which un-confirms it and voids its approvals. Use them on the skeleton or a
 * throwaway book, never on the demo book before a rehearsal. Nothing here
 * ever approves.
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

const WRITES = process.env.LIVE_ALLOW_WRITES === '1';

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

  it('Subject review renders every page', async () => {
    const b = await api.getBook((await firstBook()).id);
    renderAt(`/books/${b.id}/subjects`);
    for (const p of b.pages) expect(await screen.findByRole('heading', { name: `Page ${p.number}` })).toBeInTheDocument();
  });

  it.skipIf(!WRITES)('WRITES: a candidate pick round-trips', async () => {
    const b = await api.getBook((await firstBook()).id);
    renderAt(`/books/${b.id}/subjects`);
    await screen.findByRole('heading', { name: `Page ${b.pages[0]!.number}` });

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

describe(`live API at ${API_BASE}: subject editor`, () => {
  it('opens a page with its picture ready to tap or draw on', async () => {
    const b = await api.getBook((await firstBook()).id);
    const target = b.pages.find((p) => p.state !== 'processing');
    if (!target) return;
    renderAt(`/pages/${target.id}?book=${b.id}`);
    expect(await screen.findByRole('heading', { name: new RegExp(`Page ${target.number}`) })).toBeInTheDocument();
    expect(await screen.findByTestId('image-frame')).toBeInTheDocument();
  });

  it('a page with no subject still has a picture (the overlay is the plain page)', async () => {
    const b = await api.getBook((await firstBook()).id);
    const target = b.pages.find((p) => p.selected === null && p.state !== 'processing');
    if (!target) return;
    const img = await api.getOverlay(target.id);
    expect(img.size).toBeGreaterThan(0);
  });

  it.skipIf(!WRITES)('WRITES: the server accepts a 0-1 point and a 0-1 outline', async () => {
    const b = await api.getBook((await firstBook()).id);
    const target = b.pages.find((p) => p.state !== 'processing');
    if (!target) return;

    const byPoint = await api.setSubject(target.id, { point: [0.5, 0.5] });
    expect(typeof byPoint.id).toBe('string');
    const byOutline = await api.setSubject(target.id, {
      label: 'test shape',
      outline: [
        [0.4, 0.4],
        [0.6, 0.4],
        [0.6, 0.6],
        [0.4, 0.6],
      ],
    });
    expect(byOutline.candidates.length).toBeGreaterThan(0);
  });
});

describe(`live API at ${API_BASE}: profiles`, () => {
  it('lists profiles and previews unsaved settings without saving anything', async () => {
    const profiles = await api.listProfiles();
    for (const p of profiles) {
      expect([1, 2, 3, 4]).toContain(p.level);
      expect(p.settings.colors.length).toBeGreaterThanOrEqual(1);
    }
    const b = await api.getBook((await firstBook()).id);
    const page = b.pages.find((p) => p.selected !== null && p.state !== 'processing');
    if (!page) return;
    const before = profiles.map((p) => p.settings_hash);
    const img = await api.preview({
      page_id: page.id,
      level: 1,
      settings: { colors: ['#FDD835'], background: '#000000', size: 'medium', position: 'center', text_mode: 'off', outline: 'off' },
    });
    expect(img.size).toBeGreaterThan(0);
    expect((await api.listProfiles()).map((p) => p.settings_hash)).toEqual(before);
  });

  it('the Profiles screen renders the server’s profiles', async () => {
    const profiles = await api.listProfiles();
    renderAt('/profiles');
    for (const p of profiles) expect(await screen.findByRole('heading', { name: p.name })).toBeInTheDocument();
  });
});
