/**
 * Reader safety and input: only reader routes, exact tokens, no image on 403,
 * single taps do nothing, keys and clickers turn pages, the teacher bar offers
 * only fully approved versions, prefetch, and credits last.
 */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { StrictMode } from 'react';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { api } from '../api';
import { scenarios } from '../mocks/db';
import { server } from '../mocks/node';
import type { Book, Profile } from '../types/api';

afterEach(() => server.events.removeAllListeners());

/** Every request the screen makes, as URLs. */
function traffic(): URL[] {
  const seen: URL[] = [];
  server.events.on('request:start', ({ request }) => {
    seen.push(new URL(request.url));
  });
  return seen;
}

async function fixtures() {
  const books = await api.listBooks();
  const backup: Book = books.find((b) => b.title.startsWith('The Duck'))!;
  const demo: Book = books.find((b) => b.title.startsWith('Animal Homes'))!;
  const [maya, leo] = (await api.listProfiles()) as [Profile, Profile];
  return { backup, demo, maya, leo };
}

function openReader(bookId: string, profile: Profile, level = profile.level) {
  const seen = traffic();
  render(
    <MemoryRouter initialEntries={[`/read/${bookId}?profile=${profile.id}&level=${level}`]}>
      <App />
    </MemoryRouter>,
  );
  return seen;
}

const key = (k: string, extra: Record<string, unknown> = {}) => act(() => void fireEvent.keyDown(window, { key: k, ...extra }));
const pageImg = (n: number) => screen.findByRole('img', { name: `Page ${n}` });

/** Approve every ready page of a book for a child and look, using the sheet's own versions. */
async function approveAll(bookId: string, profile: Profile, level: 1 | 2 | 3 | 4) {
  const sheet = await api.getSheet(bookId, { profile: profile.id, level });
  const pages = sheet.pages.filter((p) => p.version).map((p) => ({ page_id: p.page_id, version: p.version!, decision: 'approve' as const }));
  await api.approve(bookId, { profile_id: profile.id, level, pages });
}

describe('Reader', () => {
  it('shows the first approved page using only the reader routes and the manifest’s own token', async () => {
    const { backup, maya } = await fixtures();
    const manifest = await api.getReaderManifest(backup.id, { profile: maya.id, level: 1 });
    const seen = openReader(backup.id, maya);
    expect(await pageImg(1)).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument(); // no visible controls
    const pageReqs = seen.filter((u) => u.pathname.startsWith('/api/reader/page/'));
    expect(pageReqs.length).toBeGreaterThan(0);
    for (const u of pageReqs) {
      const id = u.pathname.split('/').pop();
      expect(u.searchParams.get('v')).toBe(manifest.pages.find((p) => p.page_id === id)!.v);
    }
    expect(seen.some((u) => u.pathname.startsWith('/api/render') || u.pathname.startsWith('/api/preview'))).toBe(false);
  });

  it('works under React StrictMode (development double mount): the shown image is never a revoked URL', async () => {
    const { backup, maya } = await fixtures();
    const revoke = vi.spyOn(URL, 'revokeObjectURL');
    render(
      <StrictMode>
        <MemoryRouter initialEntries={[`/read/${backup.id}?profile=${maya.id}&level=1`]}>
          <App />
        </MemoryRouter>
      </StrictMode>,
    );
    const img = await pageImg(1);
    await act(() => new Promise<void>((r) => setTimeout(r, 50)));
    expect(revoke.mock.calls.map((c) => c[0])).not.toContain(img.getAttribute('src'));
    await key('ArrowRight');
    const img2 = await pageImg(2);
    expect(revoke.mock.calls.map((c) => c[0])).not.toContain(img2.getAttribute('src'));
  });

  it('a single tap or click does nothing', async () => {
    const { backup, maya } = await fixtures();
    openReader(backup.id, maya);
    await pageImg(1);
    const surface = screen.getByTestId('reader-surface');
    fireEvent.click(surface);
    fireEvent.pointerDown(surface, { pointerId: 1, clientX: 500, clientY: 400, pointerType: 'touch' });
    fireEvent.pointerUp(surface, { pointerId: 1, clientX: 500, clientY: 400, pointerType: 'touch' });
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByRole('img', { name: 'Page 1' })).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('→, Space and PageDown go forward, ← and PageUp back; held keys are ignored; credits come last', async () => {
    const { backup, maya } = await fixtures();
    openReader(backup.id, maya);
    await pageImg(1);
    await key('ArrowRight');
    await pageImg(2);
    await key('ArrowRight', { repeat: true });
    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByRole('img', { name: 'Page 2' })).toBeInTheDocument();
    await key(' ');
    await pageImg(3);
    await key('PageDown');
    const credits = await screen.findByRole('region', { name: 'Credits' });
    expect(within(credits).getByRole('heading', { name: 'The Duck (mock backup)' })).toBeInTheDocument();
    expect(credits).toHaveTextContent('License: CC BY 4.0');
    expect(credits).toHaveTextContent('Changes were made');
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    await key('ArrowRight'); // stays on credits
    expect(screen.getByRole('region', { name: 'Credits' })).toBeInTheDocument();
    await key('PageUp');
    await pageImg(3);
    await key('ArrowLeft');
    await pageImg(2);
  });

  it('prefetches the next page before it is asked for', async () => {
    const { backup, maya } = await fixtures();
    const seen = openReader(backup.id, maya);
    await pageImg(1);
    const second = backup.pages.find((p) => p.number === 2)!.id;
    await waitFor(() => expect(seen.some((u) => u.pathname === `/api/reader/page/${second}`)).toBe(true));
    const before = seen.filter((u) => u.pathname === `/api/reader/page/${second}`).length;
    await key('ArrowRight');
    await pageImg(2);
    expect(seen.filter((u) => u.pathname === `/api/reader/page/${second}`).length).toBe(before); // served from memory
  });

  it('a 403 on an image shows no picture and nothing in front of the child; the teacher bar explains', async () => {
    const { backup, maya } = await fixtures();
    scenarios.readerForbiddenNext = true;
    openReader(backup.id, maya);
    expect(await screen.findByRole('status')).toHaveTextContent('This page cannot be shown');
    expect(screen.getByRole('status')).toHaveClass('sr-only');
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument(); // no visible controls for the child
    await key('t');
    const bar = await screen.findByRole('dialog', { name: 'Teacher controls' });
    expect(within(bar).getByRole('alert')).toHaveTextContent('not approved for this child and look any more');
    expect(within(bar).getAllByRole('link', { name: /contact sheet/ }).length).toBeGreaterThan(0);
  });

  it('if the approval lapses, re-checking (opening the teacher bar) removes the page', async () => {
    const { backup, maya } = await fixtures();
    openReader(backup.id, maya);
    await pageImg(1);
    await api.updateProfile(maya.id, { settings: { ...maya.settings, background: '#FFFFFF' } }); // approvals no longer match
    await key('t');
    expect(await screen.findByText('No pages are approved for this child and look yet. Approve them on the contact sheet first.')).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('B blanks the screen (background only) until the teacher presses B again or turns a page', async () => {
    const { backup, maya } = await fixtures();
    openReader(backup.id, maya);
    await pageImg(1);
    await key('b');
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveClass('sr-only'); // nothing visible in front of the child
    await key('b');
    await pageImg(1);
    await key('B');
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    await key('ArrowRight'); // continuing shows the next page
    await pageImg(2);
    await key('b');
    await key('t');
    const bar = await screen.findByRole('dialog', { name: 'Teacher controls' });
    const user = userEvent.setup();
    await user.click(within(bar).getByRole('button', { name: 'Show the page' }));
    await pageImg(2);
  });

  it('T opens the teacher bar; only fully approved versions can be chosen; Esc closes it', async () => {
    const { backup, maya } = await fixtures();
    openReader(backup.id, maya);
    await pageImg(1);
    await key('t');
    const bar = await screen.findByRole('dialog', { name: 'Teacher controls' });
    const current = within(bar).getByRole('button', { name: 'Maya · Tinted' });
    expect(current).toHaveAttribute('aria-current', 'true');
    const leo = within(bar).getByRole('button', { name: /Leo · Cut-out/ });
    expect(leo).toBeDisabled();
    expect(leo).toHaveTextContent('(not approved)');
    expect(within(bar).getByText(/Page 1 · 1 of 3/)).toBeInTheDocument();
    await key('Escape');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('holding a corner for a second also opens the teacher bar (a harmless extra)', async () => {
    const { backup, maya } = await fixtures();
    openReader(backup.id, maya);
    await pageImg(1);
    const surface = screen.getByTestId('reader-surface');
    fireEvent.pointerDown(surface, { pointerId: 1, clientX: 5, clientY: 5, pointerType: 'touch' });
    expect(await screen.findByRole('dialog', { name: 'Teacher controls' }, { timeout: 2000 })).toBeInTheDocument();
    fireEvent.pointerUp(surface, { pointerId: 1, clientX: 5, clientY: 5, pointerType: 'touch' });
  });

  it('switching to another approved child keeps the page and uses that version’s own token', async () => {
    const { backup, maya, leo } = await fixtures();
    await approveAll(backup.id, leo, 2);
    const leoManifest = await api.getReaderManifest(backup.id, { profile: leo.id, level: 2 });
    const seen = openReader(backup.id, maya);
    await pageImg(1);
    await key('ArrowRight');
    await pageImg(2);
    const page2 = backup.pages.find((p) => p.number === 2)!.id;
    // The same page in Leo's approved version is fetched ahead of time.
    await waitFor(() =>
      expect(seen.some((u) => u.pathname === `/api/reader/page/${page2}` && u.searchParams.get('profile') === leo.id)).toBe(true),
    );

    await key('t');
    const user = userEvent.setup();
    await user.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Leo · Cut-out' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await pageImg(2);
    const leoReqs = seen.filter((u) => u.pathname === `/api/reader/page/${page2}` && u.searchParams.get('profile') === leo.id);
    expect(leoReqs.every((u) => u.searchParams.get('v') === leoManifest.pages.find((p) => p.page_id === page2)!.v)).toBe(true);
    expect(leoReqs.every((u) => u.searchParams.get('level') === '2')).toBe(true);
  });

  it('lists skipped pages for the teacher and never shows them', async () => {
    const { demo, maya } = await fixtures();
    const p1 = demo.pages.find((p) => p.number === 1)!;
    await api.confirmPage(p1.id);
    await api.omitPage(demo.pages.find((p) => p.number === 4)!.id, true);
    const sheet = await api.getSheet(demo.id, { profile: maya.id, level: 1 });
    await api.approve(demo.id, {
      profile_id: maya.id,
      level: 1,
      pages: [{ page_id: p1.id, version: sheet.pages.find((p) => p.page_id === p1.id)!.version!, decision: 'approve' }],
    });
    openReader(demo.id, maya);
    await pageImg(1);
    await key('ArrowRight');
    expect(await screen.findByRole('region', { name: 'Credits' })).toBeInTheDocument(); // only page 1 is approved
    await key('t');
    const bar = await screen.findByRole('dialog');
    expect(bar).toHaveTextContent('page 2 (not approved)');
    expect(bar).toHaveTextContent('page 4 (left out)');
  });

  it('an unknown child is a 404 message, not a crash', async () => {
    const { backup } = await fixtures();
    render(
      <MemoryRouter initialEntries={[`/read/${backup.id}?profile=pr_nobody&level=1`]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByRole('alert')).toHaveTextContent('This book or child was not found.');
  });
});
