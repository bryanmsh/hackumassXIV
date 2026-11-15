import { useState } from 'react';
import { Link } from 'react-router';
import { api } from '../../api';
import { useAction } from '../../hooks/useAction';
import { useBook } from '../../hooks/useBook';
import type { Book, PageState } from '../../types/api';
import { PAGE_STATE_LABEL, PAGE_STATE_TONE } from '../../utils/display';
import { countByState, processedCount } from '../../utils/pages';
import { Button } from '../ui/Button';
import { errorMessage } from '../ui/LoadState';
import { Badge } from '../ui/StatusBadge';
import { BookCredits } from './BookCredits';
import { OverlayImage } from './OverlayImage';

const STATE_ORDER: PageState[] = ['processing', 'ready', 'needs_subject', 'no_clear_subject', 'failed', 'unsupported'];

/** Square colors for the per-page strip. Text labels are always alongside. */
const SQUARE_TONE: Record<PageState, string> = {
  processing: 'bg-sky-100 text-sky-900 ring-sky-300',
  ready: 'bg-white text-slate-800 ring-slate-400',
  needs_subject: 'bg-amber-100 text-amber-950 ring-amber-300',
  no_clear_subject: 'bg-amber-100 text-amber-950 ring-amber-300',
  failed: 'bg-rose-100 text-rose-900 ring-rose-300',
  unsupported: 'bg-slate-200 text-slate-800 ring-slate-400',
};

/** One book in the Library. Polls GET /books/{id} every 2 seconds while it is in progress. */
export function BookCard({ book: initial, onDeleted }: { book: Book; onDeleted?: (book: Book) => void }) {
  const { book = initial, error, polling, refresh } = useBook(initial.id, { initial });
  const [askingDelete, setAskingDelete] = useState(false);
  const removal = useAction();

  async function doDelete() {
    const ok = await removal.run('delete', async (s) => {
      await api.deleteBook(book.id, s);
      return true;
    });
    if (ok) {
      setAskingDelete(false);
      onDeleted?.(book);
    }
  }
  const counts = countByState(book.pages);
  const total = book.page_count ?? book.pages.length;
  const processed = processedCount(book.pages);
  const confirmed = book.pages.filter((p) => p.confirmed).length;
  const omitted = book.pages.filter((p) => p.omitted).length;
  /** The first page, as the book's cover in the list. */
  const cover = book.pages.find((p) => p.number === 1) ?? book.pages[0];

  return (
    <li className="flex flex-col gap-4 rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      {/* Cover, title and state. Delete is a small red × up here, far from the main action below. */}
      <div className="flex items-start gap-4">
        <div className="w-28 shrink-0 overflow-hidden rounded-lg bg-slate-100 ring-1 ring-slate-200">
          {cover ? <OverlayImage page={cover} compact /> : <div className="aspect-[4/3]" aria-hidden />}
        </div>
        <div className="flex min-w-0 flex-1 items-start justify-between gap-2">
          <div className="min-w-0">
            <h2 className="break-words text-xl font-bold">{book.title}</h2>
            <div className="mt-1 flex flex-wrap gap-2">
              {book.state === 'ingesting' && <Badge tone={PAGE_STATE_TONE.processing}>Reading PDF</Badge>}
              {book.state === 'failed' && <Badge tone={PAGE_STATE_TONE.failed}>Failed</Badge>}
              {book.state === 'ready' && (
                <span className="text-slate-600">
                  {total} {total === 1 ? 'page' : 'pages'}
                </span>
              )}
            </div>
          </div>
          {onDeleted && !askingDelete && (
            <Button
              variant="ghost"
              className="-me-2 -mt-1 size-11 shrink-0 rounded-full! px-0! text-rose-700 ring-1 ring-inset ring-rose-200 hover:bg-rose-50 hover:text-rose-900"
              onClick={() => setAskingDelete(true)}
              aria-label={`Delete ${book.title}…`}
              title={`Delete ${book.title}…`}
            >
              <svg viewBox="0 0 20 20" className="size-5" aria-hidden fill="none" stroke="currentColor" strokeWidth={2.25} strokeLinecap="round">
                <path d="M5 5l10 10M15 5L5 15" />
              </svg>
            </Button>
          )}
        </div>
      </div>

      {askingDelete && (
        <div role="dialog" aria-modal="false" aria-labelledby={`${book.id}-del-h`} className="rounded-xl bg-rose-50 p-4 ring-1 ring-rose-300">
          <h3 id={`${book.id}-del-h`} className="text-lg font-bold text-rose-950">
            Delete “{book.title}”?
          </h3>
          <p className="mt-1 text-rose-950">
            Its pages, subjects, checks and approvals for every child go with it. This cannot be undone.
          </p>
          {removal.error && (
            <p role="alert" className="mt-2 rounded-lg bg-white p-2 text-rose-900 ring-1 ring-rose-200">
              Not deleted: {errorMessage(removal.error)}
            </p>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            <Button variant="danger" disabled={removal.pending !== null} onClick={() => void doDelete()}>
              {removal.pending ? 'Deleting…' : `Delete ${book.title}`}
            </Button>
            <Button disabled={removal.pending !== null} onClick={() => setAskingDelete(false)}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {book.state === 'ingesting' && <p className="text-slate-700">Reading the PDF and making the page images…</p>}
      {book.state === 'failed' && (
        <p className="text-rose-900">The server could not read this PDF. Check the file and upload it again.</p>
      )}

      {book.state === 'ready' && (
        <section aria-label={`${book.title}: pages`} className="space-y-3">
          <div>
            <div className="flex flex-wrap justify-between gap-2 text-slate-800">
              <span>
                {processed === total ? `All ${total} pages processed` : `Processing: ${processed} of ${total} pages done`}
              </span>
              <span>
                {confirmed} confirmed{omitted > 0 ? ` · ${omitted} left out` : ''}
              </span>
            </div>
            <div
              role="progressbar"
              aria-label={`${book.title}: pages processed`}
              aria-valuemin={0}
              aria-valuemax={total}
              aria-valuenow={processed}
              className="mt-1 h-2.5 overflow-hidden rounded-full bg-slate-200"
            >
              <div className="h-full bg-sky-700" style={{ width: total ? `${(processed / total) * 100}%` : '0%' }} />
            </div>
          </div>

          <ul className="flex flex-wrap gap-2" aria-label="Pages by state">
            {STATE_ORDER.filter((s) => counts[s] > 0).map((s) => (
              <li key={s}>
                <Badge tone={PAGE_STATE_TONE[s]}>
                  {counts[s]} {PAGE_STATE_LABEL[s]}
                </Badge>
              </li>
            ))}
          </ul>

          <ol className="flex flex-wrap gap-1" aria-label="Each page">
            {book.pages.map((p) => (
              <li
                key={p.id}
                title={`Page ${p.number}: ${PAGE_STATE_LABEL[p.state]}${p.omitted ? ' (left out)' : ''}`}
                className={`flex size-8 items-center justify-center rounded text-sm font-semibold ring-1 ring-inset ${SQUARE_TONE[p.state]} ${
                  p.omitted ? 'opacity-50' : ''
                }`}
              >
                <span aria-hidden>{p.number}</span>
                <span className="sr-only">
                  Page {p.number}: {PAGE_STATE_LABEL[p.state]}
                  {p.omitted ? ', left out' : ''}
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {polling && !error && (
        <p className="text-sm text-slate-600" role="status">
          Updating every 2 seconds while pages are processed.
        </p>
      )}
      {error && (
        <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg bg-amber-50 p-3 text-amber-950 ring-1 ring-amber-200">
          <span>
            {polling ? 'Could not update; trying again.' : 'Updates stopped.'} {errorMessage(error)}
          </span>
          {!polling && <Button onClick={refresh}>Try again</Button>}
        </div>
      )}

      <BookCredits book={book} onSaved={refresh} />

      {book.state === 'ready' && (
        <div className="mt-auto flex flex-wrap gap-2 border-t border-slate-200 pt-4">
          <Link
            to={`/books/${encodeURIComponent(book.id)}/subjects`}
            className="inline-flex min-h-11 items-center rounded-lg bg-sky-700 px-4 font-semibold text-white hover:bg-sky-800"
          >
            Review subjects
          </Link>
          <Link
            to={`/books/${encodeURIComponent(book.id)}/approve`}
            className="inline-flex min-h-11 items-center rounded-lg px-4 font-semibold text-sky-800 ring-1 ring-inset ring-slate-300 hover:bg-slate-100"
          >
            Contact sheets
          </Link>
        </div>
      )}
    </li>
  );
}
