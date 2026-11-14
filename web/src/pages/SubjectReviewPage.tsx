import { Link, useParams } from 'react-router';
import { api } from '../api';
import { OverlayImage } from '../components/books/OverlayImage';
import { PageHeader } from '../components/ui/AppShell';
import { ErrorPanel, Loading } from '../components/ui/LoadState';
import { Badge, PageStateBadge } from '../components/ui/StatusBadge';
import { useApi } from '../hooks/useApi';
import type { Page } from '../types/api';
import { formatConfidence } from '../utils/display';

// D1 shell: grid of overlays from GET /books/{id}. Confirm / omit / retry actions are D2.
export function SubjectReviewPage() {
  const { id = '' } = useParams();
  const book = useApi((signal) => api.getBook(id, signal), id);

  return (
    <>
      <PageHeader
        title={book.data ? `Subjects · ${book.data.title}` : 'Subject review'}
        back={
          <Link to="/" className="font-semibold text-sky-800 underline">
            ← Library
          </Link>
        }
      />
      {book.status === 'loading' && <Loading label="Loading pages…" />}
      {book.status === 'error' && <ErrorPanel error={book.error} onRetry={book.reload} title="Could not load this book" />}
      {book.data && (
        <ul className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {book.data.pages.map((p) => (
            <PageCard key={p.id} page={p} bookId={id} />
          ))}
        </ul>
      )}
    </>
  );
}

function PageCard({ page, bookId }: { page: Page; bookId: string }) {
  const cand = page.selected !== null ? page.candidates[page.selected] : undefined;
  return (
    <li className="overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-slate-200">
      <OverlayImage page={page} />
      <div className="space-y-2 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-bold">Page {page.number}</span>
          <PageStateBadge state={page.state} />
          {page.confirmed && <Badge tone="bg-emerald-600 text-white ring-emerald-700">Confirmed</Badge>}
          {page.omitted && <Badge tone="bg-slate-700 text-white ring-slate-800">Left out</Badge>}
        </div>
        <p>
          {cand ? (
            <>
              <span className="font-semibold">{cand.label || 'Unlabeled subject'}</span>
              {cand.source === 'auto' && <span className="text-slate-600"> · AI confidence {formatConfidence(cand.confidence)}</span>}
              {cand.source === 'manual' && <span className="text-slate-600"> · outlined by teacher</span>}
              {cand.source === 'click' && <span className="text-slate-600"> · picked by click</span>}
            </>
          ) : (
            <span className="text-slate-600">No subject selected</span>
          )}
        </p>
        {page.reason && <p className="text-sm text-slate-600">{page.reason}</p>}
        {page.state !== 'processing' && (
          <Link
            to={`/pages/${encodeURIComponent(page.id)}?book=${encodeURIComponent(bookId)}`}
            className="inline-flex min-h-11 items-center font-semibold text-sky-800 underline"
          >
            Open in subject editor
          </Link>
        )}
      </div>
    </li>
  );
}
