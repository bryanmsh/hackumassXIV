import { Link } from 'react-router';
import { useBook } from '../../hooks/useBook';
import type { Book, PageState } from '../../types/api';
import { PAGE_STATE_LABEL, PAGE_STATE_TONE } from '../../utils/display';
import { countByState, processedCount } from '../../utils/pages';
import { Button } from '../ui/Button';
import { errorMessage } from '../ui/LoadState';
import { Badge } from '../ui/StatusBadge';

const STATE_ORDER: PageState[] = ['processing', 'ready', 'needs_subject', 'no_clear_subject', 'failed', 'unsupported'];

/** Square colors for the per-page strip. Text labels are always alongside. */
const SQUARE_TONE: Record<PageState, string> = {
  processing: 'bg-sky-100 text-sky-900 ring-sky-300',
  ready: 'bg-emerald-100 text-emerald-900 ring-emerald-300',
  needs_subject: 'bg-amber-100 text-amber-950 ring-amber-300',
  no_clear_subject: 'bg-amber-100 text-amber-950 ring-amber-300',
  failed: 'bg-rose-100 text-rose-900 ring-rose-300',
  unsupported: 'bg-slate-200 text-slate-800 ring-slate-400',
};

/** One book in the Library. Polls GET /books/{id} every 2 seconds while it is in progress. */
export function BookCard({ book: initial }: { book: Book }) {
  const { book = initial, error, polling, refresh } = useBook(initial.id, { initial });
  const counts = countByState(book.pages);
  const total = book.page_count ?? book.pages.length;
  const processed = processedCount(book.pages);
  const confirmed = book.pages.filter((p) => p.confirmed).length;
  const omitted = book.pages.filter((p) => p.omitted).length;
  const credits = [book.credits.author, book.credits.illustrator].filter(Boolean).join(' · ');

  return (
    <li className="flex flex-col rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="break-words text-xl font-bold">{book.title}</h2>
          {credits && <p className="text-slate-600">{credits}</p>}
        </div>
        {book.state === 'ingesting' && <Badge tone={PAGE_STATE_TONE.processing}>Reading PDF</Badge>}
        {book.state === 'failed' && <Badge tone={PAGE_STATE_TONE.failed}>Failed</Badge>}
      </div>

      {book.state === 'ingesting' && <p className="mt-3 text-slate-700">Reading the PDF and making the page images…</p>}
      {book.state === 'failed' && (
        <p className="mt-3 text-rose-900">The server could not read this PDF. Check the file and upload it again.</p>
      )}

      {book.state === 'ready' && (
        <>
          <div className="mt-3">
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

          <ul className="mt-3 flex flex-wrap gap-2" aria-label="Pages by state">
            {STATE_ORDER.filter((s) => counts[s] > 0).map((s) => (
              <li key={s}>
                <Badge tone={PAGE_STATE_TONE[s]}>
                  {counts[s]} {PAGE_STATE_LABEL[s]}
                </Badge>
              </li>
            ))}
          </ul>

          <ol className="mt-3 flex flex-wrap gap-1" aria-label="Each page">
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
        </>
      )}

      {polling && !error && (
        <p className="mt-3 text-sm text-slate-600" role="status">
          Updating every 2 seconds while pages are processed.
        </p>
      )}
      {error && (
        <div role="alert" className="mt-3 flex flex-wrap items-center gap-3 rounded-lg bg-amber-50 p-3 text-amber-950 ring-1 ring-amber-200">
          <span>
            {polling ? 'Could not update; trying again.' : 'Updates stopped.'} {errorMessage(error)}
          </span>
          {!polling && <Button onClick={refresh}>Try again</Button>}
        </div>
      )}

      <div className="mt-auto flex flex-wrap gap-2 pt-4">
        {book.state === 'ready' ? (
          <>
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
          </>
        ) : null}
      </div>
    </li>
  );
}
