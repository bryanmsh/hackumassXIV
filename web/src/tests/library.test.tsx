/** Library: upload with credits, browser-side checks, server rejections, and the book list. */
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http } from 'msw';
import { MemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { scenarios } from '../mocks/db';
import { server } from '../mocks/node';

function renderLibrary() {
  render(
    <MemoryRouter initialEntries={['/']}>
      <App />
    </MemoryRouter>,
  );
  // The file input is visually hidden behind its drop-zone label; accept is
  // not applied so the browser-side type check itself is exercised.
  return userEvent.setup({ applyAccept: false });
}

const fileInput = () => screen.getByLabelText(/Choose a PDF/) as HTMLInputElement;
const pdf = (name = 'owl.pdf') => new File(['%PDF-1.4 fake'], name, { type: 'application/pdf' });

interface Sent {
  file: string | null;
  title: string | null;
  credits: string | null;
}

/** Record each upload's multipart fields, then let the mock handle it. */
function captureUploads(): Sent[] {
  const sent: Sent[] = [];
  server.use(
    http.post('*/api/books', async ({ request }) => {
      const form = await request.clone().formData();
      const file = form.get('file');
      const str = (k: string) => {
        const v = form.get(k);
        return typeof v === 'string' ? v : null;
      };
      sent.push({ file: file && typeof file !== 'string' ? file.name : null, title: str('title'), credits: str('credits') });
      return undefined;
    }),
  );
  return sent;
}

describe('Library', () => {
  it('lists books with page states and a progress count', async () => {
    renderLibrary();
    const heading = await screen.findByRole('heading', { name: 'Animal Homes (mock)' });
    const card = within(heading.closest('li')!);
    expect(card.getByText('All 6 pages processed')).toBeInTheDocument();
    expect(card.getByText('1 Needs subject')).toBeInTheDocument();
    expect(card.getByText('1 Unsupported')).toBeInTheDocument();
    expect(card.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '6');
    expect(card.getByRole('link', { name: 'Review subjects' })).toHaveAttribute('href', expect.stringMatching(/\/subjects$/));

    const busy = within((await screen.findByRole('heading', { name: /Busy Bees/ })).closest('li')!);
    expect(busy.getByText('Reading PDF')).toBeInTheDocument();
    expect(busy.getByText(/Updating every 2 seconds/)).toBeInTheDocument();
    expect(busy.queryByRole('link', { name: 'Review subjects' })).not.toBeInTheDocument();
  });

  it('says pages go to an outside AI service and states the limits', async () => {
    renderLibrary();
    expect(screen.getByText(/sent to an outside AI service/)).toBeInTheDocument();
    expect(screen.getByText(/up to 30 pages and 50 MB/)).toBeInTheDocument();
  });

  it('refuses a non-PDF without sending it', async () => {
    const user = renderLibrary();
    const sent = captureUploads();
    await user.upload(fileInput(), new File(['hello'], 'notes.txt', { type: 'text/plain' }));
    expect(screen.getByRole('alert')).toHaveTextContent('“notes.txt” is not a PDF');
    await user.click(screen.getByRole('button', { name: 'Upload book' }));
    expect(sent).toHaveLength(0);
  });

  it('refuses a PDF over 50 MB without sending it', async () => {
    const user = renderLibrary();
    const sent = captureUploads();
    const big = pdf('huge.pdf');
    Object.defineProperty(big, 'size', { value: 50 * 1024 * 1024 + 1 });
    await user.upload(fileInput(), big);
    expect(screen.getByRole('alert')).toHaveTextContent('up to 50 MB');
    await user.click(screen.getByRole('button', { name: 'Upload book' }));
    expect(sent).toHaveLength(0);
  });

  it('asks for a file when none is chosen', async () => {
    const user = renderLibrary();
    await user.click(screen.getByRole('button', { name: 'Upload book' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Choose a PDF file.');
  });

  it('shows the server’s reason when it rejects the upload', async () => {
    const user = renderLibrary();
    scenarios.uploadTooManyPagesNext = true;
    await user.upload(fileInput(), pdf());
    await user.click(screen.getByRole('button', { name: 'Upload book' }));
    expect(await screen.findByText(/The PDF has 34 pages\. Miraai supports up to 30\./)).toBeInTheDocument();
    expect(screen.getByText('The upload was not accepted.')).toBeInTheDocument();
  });

  it('uploads the file with title and credits as one JSON string, then lists the new book', async () => {
    const user = renderLibrary();
    const sent = captureUploads();
    await user.upload(fileInput(), pdf());
    await user.type(screen.getByLabelText(/Book title/), 'Owl Homes');
    // The credit fields are folded away (the PDF fills them); open them to type.
    await user.click(screen.getByRole('button', { name: 'Type credits now' }));
    await user.type(screen.getByLabelText('Author'), 'R. Writer');
    await user.type(screen.getByLabelText('License'), 'CC BY 4.0');
    await user.click(screen.getByRole('button', { name: 'Upload book' }));

    expect(await screen.findByText(/“Owl Homes” was uploaded/)).toBeInTheDocument();
    expect(sent).toHaveLength(1);
    expect(sent[0]!.file).toBe('owl.pdf');
    expect(sent[0]!.title).toBe('Owl Homes');
    expect(JSON.parse(sent[0]!.credits!)).toEqual({
      author: 'R. Writer',
      illustrator: null,
      publisher: null,
      source: null,
      license: 'CC BY 4.0',
    });
    const card = within((await screen.findByRole('heading', { name: 'Owl Homes' })).closest('li')!);
    expect(card.getByText('Reading PDF')).toBeInTheDocument();
    // The form is cleared for the next book.
    expect(screen.getByLabelText(/Book title/)).toHaveValue('');
  });

  it('sends no credits field when none were typed', async () => {
    const user = renderLibrary();
    const sent = captureUploads();
    await user.upload(fileInput(), pdf());
    await user.click(screen.getByRole('button', { name: 'Upload book' }));
    await screen.findByText(/was uploaded/);
    expect(sent[0]!.credits).toBeNull();
    expect(sent[0]!.title).toBeNull();
  });

  it('an upload with blank credits shows the credits read from the PDF, on the book card', async () => {
    const user = renderLibrary();
    await user.upload(fileInput(), pdf('owl.pdf'));
    await user.click(screen.getByRole('button', { name: 'Upload book' }));
    const card = within((await screen.findByRole('heading', { name: 'owl' })).closest('li')!);
    const credits = within(card.getByRole('region', { name: 'Credits of owl' }));
    expect(credits.getByText('Ashwitha Jayakumar')).toBeInTheDocument();
    expect(credits.getByText('Nafisa Nandini Crishna')).toBeInTheDocument();
    expect(credits.getByText('Pratham Books')).toBeInTheDocument();
    expect(credits.getByText('StoryWeaver')).toBeInTheDocument();
    expect(credits.getByText('CC BY 4.0')).toBeInTheDocument();
    expect(credits.queryByText('Not found')).not.toBeInTheDocument();
    // The upload form says where credits come from, before any field is opened.
    expect(screen.getByText(/read from the PDF where possible/)).toBeInTheDocument();
  });

  it('Edit credits saves all five through PATCH /books/{id} {credits}; a blank shows “Not found”', async () => {
    const user = renderLibrary();
    await user.upload(fileInput(), pdf('owl.pdf'));
    await user.click(screen.getByRole('button', { name: 'Upload book' }));
    const li = (await screen.findByRole('heading', { name: 'owl' })).closest('li')!;
    const card = within(li);
    const bodies: unknown[] = [];
    server.use(
      http.patch('*/api/books/:id', async ({ request }) => {
        bodies.push(await request.clone().json());
        return undefined;
      }),
    );
    await user.click(card.getByRole('button', { name: 'Edit credits of owl' }));
    const form = within(card.getByRole('form', { name: 'Edit credits of owl' }));
    expect(form.getByLabelText('Author')).toHaveValue('Ashwitha Jayakumar');
    await user.clear(form.getByLabelText('Illustrator'));
    await user.clear(form.getByLabelText('Author'));
    await user.type(form.getByLabelText('Author'), 'R. Writer');
    await user.click(form.getByRole('button', { name: 'Save credits' }));
    expect(await card.findByText('Credits saved.')).toBeInTheDocument();
    expect(bodies).toEqual([
      { credits: { author: 'R. Writer', illustrator: null, publisher: 'Pratham Books', source: 'StoryWeaver', license: 'CC BY 4.0' } },
    ]);
    const credits = within(card.getByRole('region', { name: 'Credits of owl' }));
    expect(credits.getByText('R. Writer')).toBeInTheDocument();
    expect(credits.getByText('Not found')).toBeInTheDocument();
    expect(credits.getByText(/Type anything marked/)).toBeInTheDocument();
  });

  it('Delete book asks first and names the book; Cancel sends nothing; Delete sends DELETE and removes the card', async () => {
    const user = renderLibrary();
    const heading = await screen.findByRole('heading', { name: 'Animal Homes (mock)' });
    const card = within(heading.closest('li')!);
    const deletes: string[] = [];
    server.use(
      http.delete('*/api/books/:id', ({ request }) => {
        deletes.push(new URL(request.url).pathname);
        return undefined;
      }),
    );
    await user.click(card.getByRole('button', { name: 'Delete Animal Homes (mock)…' }));
    const dialog = within(card.getByRole('dialog', { name: 'Delete “Animal Homes (mock)”?' }));
    expect(dialog.getByText(/cannot be undone/)).toBeInTheDocument();
    await user.click(dialog.getByRole('button', { name: 'Cancel' }));
    expect(deletes).toEqual([]);
    expect(card.queryByRole('dialog')).not.toBeInTheDocument();

    await user.click(card.getByRole('button', { name: 'Delete Animal Homes (mock)…' }));
    await user.click(card.getByRole('button', { name: 'Delete Animal Homes (mock)' }));
    expect(await screen.findByText('“Animal Homes (mock)” was deleted.')).toBeInTheDocument();
    expect(deletes).toHaveLength(1);
    expect(deletes[0]).toMatch(/^\/api\/books\/[^/]+$/);
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Animal Homes (mock)' })).not.toBeInTheDocument());
  });

  it('a failed delete says so and keeps the book', async () => {
    const user = renderLibrary();
    const heading = await screen.findByRole('heading', { name: 'Animal Homes (mock)' });
    const card = within(heading.closest('li')!);
    await user.click(card.getByRole('button', { name: 'Delete Animal Homes (mock)…' }));
    scenarios.networkErrorNext = true;
    await user.click(card.getByRole('button', { name: 'Delete Animal Homes (mock)' }));
    expect(await card.findByText(/Not deleted: Could not reach the server/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Animal Homes (mock)' })).toBeInTheDocument();
  });

  it('shows a retry when the list cannot load', async () => {
    scenarios.networkErrorNext = true;
    const user = renderLibrary();
    expect(await screen.findByText('Could not load the library')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByRole('heading', { name: 'Animal Homes (mock)' })).toBeInTheDocument();
  });
});
