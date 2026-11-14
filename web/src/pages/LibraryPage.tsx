import { Link } from 'react-router';
import { api } from '../api';
import { PageHeader } from '../components/ui/AppShell';
import { EmptyState, ErrorPanel, Loading } from '../components/ui/LoadState';
import { Badge } from '../components/ui/StatusBadge';
import { useApi } from '../hooks/useApi';
import type { Book } from '../types/api';
import { BOOK_STATE_LABEL, PAGE_STATE_LABEL, PAGE_STATE_TONE } from '../utils/display';
import { countByState } from '../utils/pages';

// D1 shell: lists books from GET /books. Upload, credits and 2-second polling are D2.
export function LibraryPage() {
  const books = useApi((signal) => api.listBooks(signal), 'books');

  return (
    <>
      <PageHeader title="Library" />
      {books.status === 'loading' && <Loading label="Loading books…" />}
      {books.status === 'error' && <ErrorPanel error={books.error} onRetry={books.reload} title="Could not load the library" />}
      {books.data && books.data.length === 0 && (
        <EmptyState title="No books yet">Upload a PDF picture book to get started.</EmptyState>
      )}
      {books.data && books.data.length > 0 && (
        <ul className="grid gap-4 md:grid-cols-2">
          {books.data.map((b) => (
            <BookRow key={b.id} book={b} />
          ))}
        </ul>
      )}
    </>
  );
}

function BookRow({ book }: { book: Book }) {
  const counts = countByState(book.pages);
  return (
    <li className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <div className="flex items-start justify-between gap-3">
        <h2 className="text-xl font-bold">{book.title}</h2>
        <Badge tone="bg-slate-100 text-slate-700 ring-slate-300">{BOOK_STATE_LABEL[book.state]}</Badge>
      </div>
      <p className="mt-1 text-slate-600">
        {book.page_count === null ? 'Counting pages…' : `${book.page_count} pages`}
      </p>
      <ul className="mt-3 flex flex-wrap gap-2" aria-label="Pages by state">
        {(Object.keys(counts) as (keyof typeof counts)[])
          .filter((s) => counts[s] > 0)
          .map((s) => (
            <li key={s}>
              <Badge tone={PAGE_STATE_TONE[s]}>
                {counts[s]} {PAGE_STATE_LABEL[s]}
              </Badge>
            </li>
          ))}
      </ul>
      {book.state !== 'ingesting' && (
        <div className="mt-4 flex flex-wrap gap-2">
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
