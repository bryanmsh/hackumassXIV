/** Subject review: each action sends the agreed body, the card shows the server's answer, nothing auto-confirms. */
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http } from 'msw';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { api } from '../api';
import { scenarios } from '../mocks/db';
import { server } from '../mocks/node';

interface Call {
  path: string;
  body: unknown;
}

/** Record every POST the screen makes, then let the mock handle it. */
function capturePosts(): Call[] {
  const calls: Call[] = [];
  server.use(
    http.post('*/api/*', async ({ request }) => {
      const text = await request.clone().text();
      calls.push({ path: new URL(request.url).pathname, body: text ? (JSON.parse(text) as unknown) : null });
      return undefined;
    }),
  );
  return calls;
}

async function open() {
  const books = await api.listBooks();
  const demo = books.find((b) => b.title.startsWith('Animal Homes'))!;
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={[`/books/${demo.id}/subjects`]}>
      <App />
    </MemoryRouter>,
  );
  await screen.findByRole('heading', { name: 'Page 1' });
  const id = (n: number) => demo.pages.find((p) => p.number === n)!.id;
  return { user, demo, id };
}

const card = (n: number) => within(screen.getByRole('heading', { name: `Page ${n}` }).closest('li')!);

describe('Subject review', () => {
  it('shows every page with its state, subject, and AI confidence', async () => {
    await open();
    expect(card(1).getByText('Ready')).toBeInTheDocument();
    expect(card(1).getByText(/AI confidence 0\.88/)).toBeInTheDocument();
    expect(card(3).getByText('Needs subject')).toBeInTheDocument();
    expect(card(3).getByText('No subject chosen yet.')).toBeInTheDocument();
    expect(card(4).getByText('No clear subject')).toBeInTheDocument();
    expect(card(5).getByText('Failed')).toBeInTheDocument();
    expect(card(6).getByText('Unsupported')).toBeInTheDocument();
    // Nothing is confirmed until the teacher says so.
    expect(screen.queryByText('Confirmed')).not.toBeInTheDocument();
    expect(screen.getByText(/of 6 pages decided/)).toHaveTextContent('0 of 6 pages decided');
  });

  it('Confirm sends POST /pages/{id}/confirm and shows Confirmed', async () => {
    const { user, id } = await open();
    const calls = capturePosts();
    await user.click(card(1).getByRole('button', { name: 'Confirm' }));
    expect(await card(1).findByText('Confirmed')).toBeInTheDocument();
    expect(calls[0]).toEqual({ path: `/api/pages/${id(1)}/confirm`, body: null });
    expect(card(1).queryByRole('button', { name: 'Confirm' })).not.toBeInTheDocument();
  });

  it('choosing another candidate sends {candidate: index}', async () => {
    const { user, id } = await open();
    const calls = capturePosts();
    await user.click(card(3).getByRole('button', { name: /beehive/ }));
    expect(await card(3).findByRole('button', { name: /beehive/, pressed: true })).toBeInTheDocument();
    expect(calls[0]).toEqual({ path: `/api/pages/${id(3)}/subject`, body: { candidate: 1 } });
    expect(card(3).getByText(/Subject:/)).toHaveTextContent('beehive');
    expect(card(3).getByRole('button', { name: 'Confirm' })).toBeInTheDocument();
  });

  it('Leave out and Include again send {omitted}', async () => {
    const { user, id } = await open();
    const calls = capturePosts();
    await user.click(card(4).getByRole('button', { name: 'Leave out' }));
    expect(await card(4).findByText('Left out')).toBeInTheDocument();
    await user.click(card(4).getByRole('button', { name: 'Include again' }));
    expect(await card(4).findByRole('button', { name: 'Leave out' })).toBeInTheDocument();
    expect(calls.map((c) => c.body)).toEqual([{ omitted: true }, { omitted: false }]);
    expect(calls.every((c) => c.path === `/api/pages/${id(4)}/omit`)).toBe(true);
  });

  it('Retry on a failed page sends {force: false}; the page goes back to Processing', async () => {
    const { user, id } = await open();
    const calls = capturePosts();
    await user.click(card(5).getByRole('button', { name: 'Retry' }));
    expect(await card(5).findByText('Processing')).toBeInTheDocument();
    expect(calls[0]).toEqual({ path: `/api/pages/${id(5)}/retry`, body: { force: false } });
    expect(await screen.findByText(/Updating every 2 seconds/)).toBeInTheDocument();
  });

  it('Process anyway on an Unsupported page sends {force: true}', async () => {
    const { user, id } = await open();
    const calls = capturePosts();
    await user.click(card(6).getByRole('button', { name: 'Process anyway' }));
    expect(await card(6).findByText('Processing')).toBeInTheDocument();
    expect(calls[0]).toEqual({ path: `/api/pages/${id(6)}/retry`, body: { force: true } });
  });

  it('Confirm all asks first, lists the pages, and only then confirms', async () => {
    const { user, demo } = await open();
    const calls = capturePosts();
    await user.click(screen.getByRole('button', { name: 'Confirm all…' }));
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveTextContent('Confirm 2 subjects?');
    expect(dialog).toHaveTextContent('Pages 1, 2 will be confirmed');
    expect(calls).toHaveLength(0);

    await user.click(within(dialog).getByRole('button', { name: 'Confirm 2' }));
    expect(await screen.findByText('Confirmed 2 pages.')).toBeInTheDocument();
    expect(calls[0]).toEqual({ path: `/api/books/${demo.id}/confirm-all`, body: null });
    expect(card(1).getByText('Confirmed')).toBeInTheDocument();
    expect(card(2).getByText('Confirmed')).toBeInTheDocument();
    expect(card(3).queryByText('Confirmed')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm all…' })).toBeDisabled();
  });

  it('Ask the AI again asks first, then processes only pages not confirmed or left out', async () => {
    const { user, demo } = await open();
    await user.click(card(1).getByRole('button', { name: 'Confirm' }));
    expect(await card(1).findByText('Confirmed')).toBeInTheDocument();
    const calls = capturePosts();
    await user.click(screen.getByRole('button', { name: 'Ask the AI again…' }));
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveTextContent('outside AI service');
    expect(dialog).not.toHaveTextContent('Pages 1,');
    expect(calls).toHaveLength(0);

    await user.click(within(dialog).getByRole('button', { name: /^Ask about \d+$/ }));
    expect(await screen.findByText(/Asking the AI again about \d+ pages?\./)).toBeInTheDocument();
    expect(calls[0]).toEqual({ path: `/api/books/${demo.id}/rerun`, body: null });
    expect(card(1).getByText('Confirmed')).toBeInTheDocument();
    expect(card(1).queryByText('Processing')).not.toBeInTheDocument();
    expect(await card(2).findByText('Processing')).toBeInTheDocument();
  });

  it('Cancel in Confirm all sends nothing', async () => {
    const { user } = await open();
    const calls = capturePosts();
    await user.click(screen.getByRole('button', { name: 'Confirm all…' }));
    await user.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancel' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });

  it('a failed action shows the error on that card and changes nothing', async () => {
    const { user } = await open();
    scenarios.networkErrorNext = true;
    await user.click(card(1).getByRole('button', { name: 'Confirm' }));
    expect(await card(1).findByRole('alert')).toHaveTextContent('Could not reach the server');
    expect(card(1).queryByText('Confirmed')).not.toBeInTheDocument();
    expect(card(1).getByRole('button', { name: 'Confirm' })).toBeEnabled();
  });

  it('links each page to the subject editor', async () => {
    const { id, demo } = await open();
    expect(card(3).getByRole('link', { name: 'Pick on the page' })).toHaveAttribute('href', `/pages/${id(3)}?book=${demo.id}`);
    expect(card(5).getByRole('link', { name: 'Outline by hand' })).toBeInTheDocument();
  });

  it('shows the server’s answer for an unknown book', async () => {
    render(
      <MemoryRouter initialEntries={['/books/bk_missing/subjects']}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/Could not load this book \(HTTP 404\)/)).toBeInTheDocument();
    expect(screen.getByText('Book not found.')).toBeInTheDocument();
  });

  it('recovers from a network error with Try again', async () => {
    const books = await api.listBooks();
    const demo = books.find((b) => b.title.startsWith('Animal Homes'))!;
    scenarios.networkErrorNext = true;
    const user = userEvent.setup();
    render(
      <MemoryRouter initialEntries={[`/books/${demo.id}/subjects`]}>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText('Could not load this book')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('heading', { name: 'Page 1' })).toBeInTheDocument();
  });
});
