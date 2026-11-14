import { Link, useParams, useSearchParams } from 'react-router';
import { ApiError, api } from '../api';
import { OverlayImage } from '../components/books/OverlayImage';
import { PageHeader } from '../components/ui/AppShell';
import { ErrorPanel, Loading } from '../components/ui/LoadState';
import { PageStateBadge } from '../components/ui/StatusBadge';
import { useApi } from '../hooks/useApi';
import type { Book, Page } from '../types/api';
import { formatConfidence } from '../utils/display';

/**
 * Contract 1 has no GET /pages/{id}, so the editor loads the page through its
 * book: `?book=` when the link supplies it, otherwise by scanning GET /books.
 */
async function loadPage(pageId: string, bookHint: string | null, signal: AbortSignal): Promise<{ book: Book; page: Page }> {
  const books = bookHint ? [await api.getBook(bookHint, signal)] : await api.listBooks(signal);
  for (const book of books) {
    const page = book.pages.find((p) => p.id === pageId);
    if (page) return { book, page };
  }
  throw new ApiError('http', 'This page was not found.', 404);
}

// D1 shell: shows the page and its candidates. Click-to-pick and outline drawing are D3.
export function SubjectEditorPage() {
  const { id = '' } = useParams();
  const [params] = useSearchParams();
  const bookHint = params.get('book');
  const data = useApi((signal) => loadPage(id, bookHint, signal), `${id}:${bookHint ?? ''}`);
  const book = data.data?.book;
  const page = data.data?.page;

  return (
    <>
      <PageHeader
        title={page ? `Page ${page.number} · subject editor` : 'Subject editor'}
        back={
          book && (
            <Link to={`/books/${encodeURIComponent(book.id)}/subjects`} className="font-semibold text-sky-800 underline">
              ← {book.title}
            </Link>
          )
        }
      />
      {data.status === 'loading' && <Loading label="Loading page…" />}
      {data.status === 'error' && <ErrorPanel error={data.error} onRetry={data.reload} title="Could not load this page" />}
      {page && (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
          <OverlayImage page={page} className="rounded-xl ring-1 ring-slate-200" />
          <aside className="space-y-4">
            <PageStateBadge state={page.state} />
            <h2 className="text-lg font-bold">Suggested subjects</h2>
            {page.candidates.length === 0 ? (
              <p className="text-slate-600">No suggestions for this page.</p>
            ) : (
              <ol className="space-y-2">
                {page.candidates.map((c, i) => (
                  <li key={c.mask_hash} className="rounded-lg bg-white p-3 ring-1 ring-slate-200">
                    <span className="font-semibold">{c.label || 'Unlabeled'}</span>
                    {c.source === 'auto' && <span className="text-slate-600"> · {formatConfidence(c.confidence)}</span>}
                    {page.selected === i && <span className="ml-2 font-semibold text-emerald-800">Selected</span>}
                  </li>
                ))}
              </ol>
            )}
          </aside>
        </div>
      )}
    </>
  );
}
