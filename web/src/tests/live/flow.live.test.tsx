/**
 * The checkpoint-2 run, through the real screens, against a REAL API that is
 * a throwaway LOCAL instance. It uploads, edits subjects, creates children,
 * approves and reads, so it refuses to run against anything but localhost.
 *
 *   LIVE_API_URL=http://127.0.0.1:8000 LIVE_FLOW=1 LIVE_PDF=/path/book3.pdf npm run test:live
 *
 * The book must be the 3-page PDF from api/tests/helpers.make_pdf(3), with the
 * API on PIPELINE=stub: its pages come out Ready, Needs subject and Failed.
 */
import { readFileSync } from 'node:fs';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../../App';
import { ApiError, api } from '../../api';
import { API_BASE } from '../../config';
import type { Book, NormPoint, Profile } from '../../types/api';

const host = (() => {
  try {
    return new URL(API_BASE).hostname;
  } catch {
    return '';
  }
})();
const LOCAL = host === '127.0.0.1' || host === 'localhost';
const RUN = process.env.LIVE_FLOW === '1' && LOCAL && Boolean(process.env.LIVE_PDF);

const TITLE = `Flow test ${Date.now()}`;
let book: Book;
let maya: Profile;
let leo: Profile;

const FRAME = { left: 100, top: 50, width: 800, height: 600 };
beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
    const r = this.dataset.testid === 'image-frame' ? FRAME : { left: 0, top: 0, width: 0, height: 0 };
    return { ...r, x: r.left, y: r.top, right: r.left + r.width, bottom: r.top + r.height, toJSON: () => r } as DOMRect;
  });
});
afterEach(() => vi.restoreAllMocks());

function renderAt(path: string) {
  cleanup(); // one screen at a time, even within a step
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
  return userEvent.setup();
}

const at = ([x, y]: NormPoint) => ({ clientX: FRAME.left + x * FRAME.width, clientY: FRAME.top + y * FRAME.height });
const card = (n: number) => within(screen.getByRole('heading', { name: `Page ${n}` }).closest('li')!);
const pageNo = (n: number) => book.pages.find((p) => p.number === n)!;

async function createChild(name: string, look: RegExp, colors: string[]) {
  const user = renderAt('/profiles');
  await user.click(await screen.findByRole('button', { name: 'New child profile' }));
  await user.type(screen.getByLabelText('First name'), name);
  await user.click(screen.getByRole('radio', { name: look }));
  for (const c of colors) await user.click(screen.getByRole('button', { name: new RegExp(`^${c}`) }));
  if (!colors.includes('Red')) await user.click(screen.getByRole('button', { name: /^Red/ }));
  await user.click(screen.getByRole('button', { name: 'Save profile' }));
  await screen.findByText(`${name}’s profile was created.`);
}

async function approveSheet(profile: Profile) {
  const user = renderAt(`/books/${book.id}/approve?profile=${profile.id}&level=${profile.level}`);
  await screen.findByRole('heading', { name: 'Page 3' }, { timeout: 10000 });
  await user.click(await screen.findByRole('button', { name: 'Approve sheet…' }));
  await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Approve 3' }));
  expect(await screen.findByText(/^Approved 3 pages for/, {}, { timeout: 10000 })).toBeInTheDocument();
}

describe.skipIf(!RUN)(`checkpoint-2 flow on the local real API at ${API_BASE}`, () => {
  it('1. Library: upload with credits, watch pages get their states', async () => {
    const user = renderAt('/');
    const file = new File([readFileSync(process.env.LIVE_PDF!)], 'book3.pdf', { type: 'application/pdf' });
    await user.upload(screen.getByLabelText(/Choose a PDF/), file);
    await user.type(screen.getByLabelText(/Book title/), TITLE);
    await user.type(screen.getByLabelText('Author'), 'Test Author');
    await user.type(screen.getByLabelText('License'), 'CC BY 4.0');
    await user.click(screen.getByRole('button', { name: 'Upload book' }));
    expect(await screen.findByText(new RegExp(`“${TITLE}” was uploaded`), {}, { timeout: 15000 })).toBeInTheDocument();
    const heading = await screen.findByRole('heading', { name: TITLE }, { timeout: 15000 });
    const c = within(heading.closest('li')!);
    expect(await c.findByText('All 3 pages processed', {}, { timeout: 20000 })).toBeInTheDocument();
    book = (await api.listBooks()).find((b) => b.title === TITLE)!;
    expect(book.credits.author).toBe('Test Author');
    expect(book.pages.map((p) => p.state)).toEqual(['ready', 'needs_subject', 'failed']);
  }, 60000);

  it('2. Subject review: confirm the Ready page', async () => {
    const user = renderAt(`/books/${book.id}/subjects`);
    await screen.findByRole('heading', { name: 'Page 1' });
    expect(card(2).getByText('Needs subject')).toBeInTheDocument();
    expect(card(3).getByText('Failed')).toBeInTheDocument();
    await user.click(card(1).getByRole('button', { name: 'Confirm' }));
    expect(await card(1).findByText('Confirmed')).toBeInTheDocument();
  }, 30000);

  it('3. Editor: fix page 2 by clicking the object (0-1 point), then confirm', async () => {
    const user = renderAt(`/pages/${pageNo(2).id}?book=${book.id}`);
    const frame = await screen.findByTestId('image-frame', {}, { timeout: 10000 });
    await user.click(screen.getByRole('button', { name: 'Click the object' }));
    fireEvent.click(frame, at([0.5, 0.5]));
    await user.click(screen.getByRole('button', { name: 'Cut out the object here' }));
    expect(await screen.findByText(/picked by clicking/, {}, { timeout: 10000 })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Confirm this subject' }));
    expect(await screen.findByText('Subject confirmed.')).toBeInTheDocument();
  }, 30000);

  it('4. Editor: fix the Failed page 3 by label + freehand outline, then confirm', async () => {
    const user = renderAt(`/pages/${pageNo(3).id}?book=${book.id}`);
    const frame = await screen.findByTestId('image-frame', {}, { timeout: 10000 });
    expect(screen.getByRole('button', { name: 'Draw an outline', pressed: true })).toBeInTheDocument();
    await user.type(screen.getByLabelText('What is it?'), 'frog');
    const pts: NormPoint[] = Array.from({ length: 300 }, (_, i) => {
      const a = (i / 300) * Math.PI * 2;
      return [0.5 + 0.2 * Math.cos(a), 0.5 + 0.2 * Math.sin(a)];
    });
    const base = { pointerId: 1, isPrimary: true, pointerType: 'touch', button: 0 };
    fireEvent.pointerDown(frame, { ...base, ...at(pts[0]!) });
    for (const p of pts.slice(1)) fireEvent.pointerMove(frame, { ...base, ...at(p) });
    fireEvent.pointerUp(frame, { ...base, ...at(pts[pts.length - 1]!) });
    await user.click(screen.getByRole('button', { name: 'Save outline' }));
    expect(await screen.findByText(/made by teacher/, {}, { timeout: 10000 })).toBeInTheDocument();
    // The server turned our 0-1 outline into a candidate box that matches what was drawn.
    const fresh = await api.getBook(book.id);
    const p3 = fresh.pages.find((p) => p.number === 3)!;
    const box = p3.candidates[p3.selected!]!.box;
    const expected = [0.3, 0.3, 0.7, 0.7];
    box.forEach((n, i) => expect(Math.abs(n - expected[i]!)).toBeLessThan(0.01));
    await user.click(screen.getByRole('button', { name: 'Confirm this subject' }));
    expect(await screen.findByText('Subject confirmed.')).toBeInTheDocument();
  }, 30000);

  it('5. Profiles: create Maya (Tinted, red) and Leo (Cut-out, yellow + blue), with a live preview', async () => {
    await createChild('Maya', /Tinted/, ['Red']);
    await createChild('Leo', /Cut-out/, ['Yellow', 'Blue']);
    // The newest of each name (ids grow over time), in case the database has older ones.
    const profiles = await api.listProfiles();
    const newest = (name: string) => profiles.filter((p) => p.name === name).sort((a, b) => (a.id < b.id ? 1 : -1))[0]!;
    maya = newest('Maya');
    leo = newest('Leo');
    expect(maya.settings.colors).toEqual(['#E53935']);
    expect(leo.settings.colors).toEqual(['#FDD835', '#1E88E5']);
    expect(leo.level).toBe(2);
  }, 60000);

  it('6. Contact sheet: a page changed while open → "Look again"; nothing re-sent', async () => {
    const user = renderAt(`/books/${book.id}/approve?profile=${maya.id}&level=1`);
    await screen.findByRole('heading', { name: 'Page 3' }, { timeout: 10000 });
    await screen.findByRole('button', { name: 'Approve sheet…' });
    // Someone changes page 1's subject after the sheet loaded.
    const p1 = (await api.getBook(book.id)).pages.find((p) => p.number === 1)!;
    const other = p1.candidates.findIndex((_, i) => i !== p1.selected);
    if (other >= 0) await api.setSubject(p1.id, { candidate: other });
    else await api.setSubject(p1.id, { point: [0.2, 0.2] });
    await api.confirmPage(p1.id);
    await user.click(screen.getByRole('button', { name: 'Approve sheet…' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Approve 3' }));
    const alert = await screen.findByRole('alert', {}, { timeout: 10000 });
    expect(alert).toHaveTextContent('Look again');
    expect(alert).toHaveTextContent('Page 1 changed');
    await waitFor(() => expect(card(1).getByText('Changed: look again')).toBeInTheDocument());
    // Decisions wait until the fresh sheet (with the new version) has arrived.
    await waitFor(() => expect(card(1).getByRole('button', { name: 'Approve page' })).toBeEnabled(), { timeout: 10000 });
    await user.click(card(1).getByRole('button', { name: 'Approve page' }));
    await waitFor(() => expect(card(1).getByText('Approved')).toBeInTheDocument(), { timeout: 10000 });
  }, 60000);

  it('7. Contact sheet: approve all of Leo’s sheet', async () => {
    await approveSheet(leo);
  }, 60000);

  it('8. Reader: read as Maya, switch to Leo; an unapproved image is refused', async () => {
    renderAt(`/read/${book.id}?profile=${maya.id}&level=1`);
    expect(await screen.findByRole('img', { name: 'Page 1' }, { timeout: 10000 })).toBeInTheDocument();
    await act(() => void fireEvent.keyDown(window, { key: 'ArrowRight' }));
    expect(await screen.findByRole('img', { name: 'Page 2' }, { timeout: 10000 })).toBeInTheDocument();
    await act(() => void fireEvent.keyDown(window, { key: 't' }));
    const bar = await screen.findByRole('dialog', { name: 'Teacher controls' });
    const user = userEvent.setup();
    await user.click(await within(bar).findByRole('button', { name: 'Leo · Cut-out' }));
    expect(await screen.findByRole('img', { name: 'Page 2' }, { timeout: 10000 })).toBeInTheDocument();

    // A version nobody approved (Maya at Outlined) is refused by the server.
    const p2 = pageNo(2);
    const sheet = await api.getSheet(book.id, { profile: maya.id, level: 4 });
    const v = sheet.pages.find((p) => p.page_id === p2.id)!.version!;
    const refused = await api.getReaderPage(p2.id, { profile: maya.id, level: 4, v }).catch((e: unknown) => e);
    expect(refused).toBeInstanceOf(ApiError);
    expect((refused as ApiError).status).toBe(403);
    expect((refused as ApiError).body).toEqual({ detail: 'not approved' });
  }, 60000);

  it('9. Changing Maya’s colors voids her approvals: the reader shows nothing for her', async () => {
    await api.updateProfile(maya.id, { settings: { ...maya.settings, background: '#FFFFFF' } });
    renderAt(`/read/${book.id}?profile=${maya.id}&level=1`);
    expect(await screen.findByText(/No pages are approved for this child and look yet/, {}, { timeout: 10000 })).toBeInTheDocument();
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    // Changing back restores them (approvals match again).
    await api.updateProfile(maya.id, { settings: maya.settings });
    const m = await api.getReaderManifest(book.id, { profile: maya.id, level: 1 });
    expect(m.pages).toHaveLength(3);
  }, 60000);
});
