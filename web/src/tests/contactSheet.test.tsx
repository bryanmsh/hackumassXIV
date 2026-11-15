/**
 * Contact sheet: exact version echo, approve / reject, honest checks, and the
 * 409 "look again" flow that never re-approves on its own.
 */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { HttpResponse, http } from 'msw';
import { MemoryRouter } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';
import { App } from '../App';
import { api } from '../api';
import { scenarios } from '../mocks/db';
import { server } from '../mocks/node';
import type { ApproveRequest, Book, Profile, Sheet } from '../types/api';
import { DEFAULT_SETTINGS } from '../utils/display';

interface Traffic {
  approves: ApproveRequest[];
  sheets: Sheet[];
  renders: URL[];
}

/** Record approve bodies, sheets served and render requests, then let the mocks answer. */
function watch(): Traffic {
  const t: Traffic = { approves: [], sheets: [], renders: [] };
  server.use(
    http.post('*/api/books/:id/approve', async ({ request }) => {
      t.approves.push((await request.clone().json()) as ApproveRequest);
      return undefined;
    }),
    http.get('*/api/render/:pageId', ({ request }) => {
      t.renders.push(new URL(request.url));
      return undefined;
    }),
  );
  server.events.on('response:mocked', async ({ request, response }) => {
    if (/\/api\/books\/[^/]+\/sheet/.test(new URL(request.url).pathname) && response.ok) {
      t.sheets.push((await response.clone().json()) as Sheet);
    }
  });
  return t;
}

async function setup(opts: { confirm?: number[]; profile?: Profile } = {}) {
  const demo: Book = (await api.listBooks()).find((b) => b.title.startsWith('Animal Homes'))!;
  for (const n of opts.confirm ?? [1, 2]) await api.confirmPage(demo.pages.find((p) => p.number === n)!.id);
  const profile = opts.profile ?? (await api.listProfiles())[0]!;
  const t = watch();
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[`/books/${demo.id}/approve?profile=${profile.id}&level=${profile.level}`]}>
      <App />
    </MemoryRouter>,
  );
  await screen.findByRole('heading', { name: 'Page 1' });
  return { demo, profile, t, user };
}

// The sheet recorder listens to MSW events; drop it after each test.
afterEach(() => server.events.removeAllListeners());

const card = (n: number) => within(screen.getByRole('heading', { name: `Page ${n}` }).closest('li')!);
const lastSheet = (t: Traffic) => t.sheets[t.sheets.length - 1]!;
const versionOf = (s: Sheet, n: number) => s.pages.find((p) => p.number === n)!.version;

describe('Contact sheet', () => {
  it('shows the exact version previews for the chosen child and look, with checks and states', async () => {
    const { t } = await setup();
    await waitFor(() => expect(t.renders.length).toBeGreaterThanOrEqual(2));
    // Previews are fetched with each page's own version, as the sheet gave it.
    for (const url of t.renders) {
      const pageId = url.pathname.split('/').pop();
      const sheetPage = lastSheet(t).pages.find((p) => p.page_id === pageId)!;
      expect(url.searchParams.get('v')).toBe(sheetPage.version);
      expect(url.searchParams.get('level')).toBe('1');
    }
    expect(card(1).getByText('Not approved')).toBeInTheDocument();
    expect(card(1).getByRole('list', { name: 'Checks' })).toBeInTheDocument();
    expect(card(3).getByText('Confirm a subject in Subject review first.')).toBeInTheDocument();
    expect(card(3).queryByRole('button', { name: /Approve/ })).not.toBeInTheDocument();
    expect(screen.getByText(/they do not replace your review/)).toBeInTheDocument();
  });

  it('Approve sheet asks first, then sends every open page with its exact version', async () => {
    const { t, user, profile } = await setup();
    await user.click(screen.getByRole('button', { name: 'Approve sheet…' }));
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveTextContent('Approve 2 pages for Maya · Tinted?');
    expect(t.approves).toHaveLength(0);

    await user.click(within(dialog).getByRole('button', { name: 'Approve 2' }));
    expect(await screen.findByText('Approved 2 pages for Maya · Tinted.')).toBeInTheDocument();
    const sheetBefore = t.sheets[0]!;
    expect(t.approves[0]).toEqual({
      profile_id: profile.id,
      level: 1,
      pages: [
        { page_id: sheetBefore.pages[0]!.page_id, version: versionOf(sheetBefore, 1), decision: 'approve' },
        { page_id: sheetBefore.pages[1]!.page_id, version: versionOf(sheetBefore, 2), decision: 'approve' },
      ],
    });
    await waitFor(() => expect(card(1).getByText('Approved')).toBeInTheDocument());
    expect(card(2).getByText('Approved')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Read with Maya · Tinted' })).toBeInTheDocument();
  });

  it('rejecting one page sends only that page, and Approve sheet then leaves it out', async () => {
    const { t, user } = await setup();
    await user.click(card(2).getByRole('button', { name: 'Reject page' }));
    await waitFor(() => expect(card(2).getByText('Rejected')).toBeInTheDocument());
    expect(t.approves[0]!.pages).toEqual([{ page_id: lastSheet(t).pages[1]!.page_id, version: versionOf(t.sheets[0]!, 2), decision: 'reject' }]);

    await user.click(screen.getByRole('button', { name: 'Approve sheet…' }));
    expect(screen.getByRole('dialog')).toHaveTextContent('Approve 1 page');
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Approve 1' }));
    await screen.findByText(/Approved 1 page/);
    expect(t.approves[1]!.pages.map((p) => p.decision)).toEqual(['approve']);
    expect(card(2).getByText('Rejected')).toBeInTheDocument();
    expect(card(2).getByRole('button', { name: 'Approve instead' })).toBeInTheDocument();
  });

  it('409: shows "Look again", reloads, never re-sends, and the next approve uses the NEW version', async () => {
    const { t, user } = await setup();
    const oldV1 = versionOf(t.sheets[0]!, 1);
    scenarios.approveConflictNext = true; // page 1 changes on the server as the request lands
    await user.click(screen.getByRole('button', { name: 'Approve sheet…' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Approve 2' }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Look again');
    expect(alert).toHaveTextContent('Page 1 changed');
    expect(alert).toHaveTextContent('Your other 1 decision was saved.');
    await waitFor(() => expect(t.sheets.length).toBeGreaterThanOrEqual(2));
    expect(t.approves).toHaveLength(1); // no automatic retry
    expect(screen.queryByText(/^Approved \d/)).not.toBeInTheDocument(); // no false success

    await waitFor(() => expect(versionOf(lastSheet(t), 1)).not.toBe(oldV1));
    expect(card(1).getByText('Changed: look again')).toBeInTheDocument();
    expect(card(1).getByText('Not approved')).toBeInTheDocument();
    expect(card(2).getByText('Approved')).toBeInTheDocument();

    await user.click(card(1).getByRole('button', { name: 'Approve page' }));
    await waitFor(() => expect(card(1).getByText('Approved')).toBeInTheDocument());
    expect(t.approves[1]!.pages).toEqual([{ page_id: lastSheet(t).pages[0]!.page_id, version: versionOf(t.sheets[1]!, 1), decision: 'approve' }]);
    expect(t.approves[1]!.pages[0]!.version).not.toBe(oldV1);
    expect(card(1).queryByText('Changed: look again')).not.toBeInTheDocument();
  });

  it('after a 409, decisions wait for the fresh sheet (a slow reload cannot send the old version)', async () => {
    const { t, user } = await setup();
    const oldV1 = versionOf(t.sheets[0]!, 1);
    scenarios.approveConflictNext = true;
    await user.click(screen.getByRole('button', { name: 'Approve sheet…' }));
    scenarios.latencyMs = 400; // the reload after the 409 is slow
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Approve 2' }));
    await screen.findByRole('alert', {}, { timeout: 3000 });
    expect(card(1).getByRole('button', { name: 'Approve page' })).toBeDisabled();
    await waitFor(() => expect(card(1).getByRole('button', { name: 'Approve page' })).toBeEnabled(), { timeout: 3000 });
    scenarios.latencyMs = 0;
    await user.click(card(1).getByRole('button', { name: 'Approve page' }));
    await waitFor(() => expect(card(1).getByText('Approved')).toBeInTheDocument());
    expect(t.approves.at(-1)!.pages[0]!.version).not.toBe(oldV1);
  });

  it('shows failing and warning checks, and lists them before approving', async () => {
    const low = await api.createProfile({
      name: 'Sam',
      level: 1,
      settings: { ...DEFAULT_SETTINGS, colors: ['#FDD835'], background: '#FFFFFF' },
      contrast_override_note: 'Testing',
    });
    const { user } = await setup({ profile: low });
    expect(card(1).getAllByText('Warning').length).toBeGreaterThan(0);
    expect(card(1).getByText(/below 3:1/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Approve sheet…' }));
    expect(screen.getByRole('dialog')).toHaveTextContent('Page 1: Contrast warning');
  });

  it('a failed request records nothing and says so', async () => {
    const { user } = await setup();
    // Fail the approve request itself. (The shared "next request fails" flag could be used up
    // by a preview image or sheet refresh that is still arriving, which made this test flaky.)
    server.use(http.post('*/api/books/:id/approve', () => HttpResponse.error(), { once: true }));
    await user.click(card(1).getByRole('button', { name: 'Approve page' }));
    expect(await screen.findByText(/Nothing was recorded: Could not reach the server/)).toBeInTheDocument();
    expect(card(1).getByText('Not approved')).toBeInTheDocument();
  });

  it('shows the second look, including a pending one', async () => {
    await setup({ confirm: [1] });
    expect(card(1).getByText(/still checking/)).toBeInTheDocument();
    expect(screen.getByText(/second look is still running/)).toBeInTheDocument();
  });

  it('choosing a child starts on that child’s own look; looks are listed by name', async () => {
    const demo: Book = (await api.listBooks()).find((b) => b.title.startsWith('Animal Homes'))!;
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={[`/books/${demo.id}/approve`]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText('Choose a child and a look to see this book’s contact sheet.')).toBeInTheDocument();
    const child = screen.getByLabelText('Child');
    await waitFor(() => expect(within(child).getByRole('option', { name: 'Leo (Cut-out)' })).toBeInTheDocument());
    await user.selectOptions(child, within(child).getByRole('option', { name: 'Leo (Cut-out)' }));
    expect(screen.getByLabelText('Look')).toHaveDisplayValue('Cut-out');
    expect(await screen.findByRole('heading', { name: 'Page 1' })).toBeInTheDocument();
  });

  it('switching to another child moves the look to that child’s own look, even when a look is already set', async () => {
    const { user } = await setup(); // Maya, Tinted
    expect(screen.getByLabelText('Look')).toHaveDisplayValue('Tinted');
    const child = screen.getByLabelText('Child');
    await user.selectOptions(child, within(child).getByRole('option', { name: 'Leo (Cut-out)' }));
    expect(screen.getByLabelText('Look')).toHaveDisplayValue('Cut-out');
  });

  it('the Reader link appears only once a page is approved', async () => {
    const { user } = await setup();
    expect(screen.queryByRole('link', { name: /Read with/ })).not.toBeInTheDocument();
    await user.click(card(1).getByRole('button', { name: 'Approve page' }));
    expect(await screen.findByRole('link', { name: 'Read with Maya · Tinted' })).toHaveAttribute(
      'href',
      expect.stringMatching(/^\/read\/.+\?profile=.+&level=1$/),
    );
  });
});
