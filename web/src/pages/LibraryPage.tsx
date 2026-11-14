import { useState } from 'react';
import { api } from '../api';
import { BookCard } from '../components/books/BookCard';
import { UploadForm } from '../components/books/UploadForm';
import { PageHeader } from '../components/ui/AppShell';
import { EmptyState, ErrorPanel, Loading } from '../components/ui/LoadState';
import { useApi } from '../hooks/useApi';

/** Library: upload a PDF with credits, list books with live page states. */
export function LibraryPage() {
  const books = useApi((signal) => api.listBooks(signal), 'books');
  const [notice, setNotice] = useState<string | null>(null);

  return (
    <>
      <PageHeader title="Library" />
      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)]">
        <section aria-labelledby="books-h" className="order-2 lg:order-1">
          <h2 id="books-h" className="sr-only">
            Books
          </h2>
          {notice && (
            <p role="status" className="mb-4 rounded-lg bg-emerald-50 p-3 text-emerald-950 ring-1 ring-emerald-200">
              {notice}
            </p>
          )}
          {books.status === 'loading' && <Loading label="Loading books…" />}
          {books.status === 'error' && (
            <ErrorPanel error={books.error} onRetry={books.reload} title="Could not load the library" />
          )}
          {books.data && books.data.length === 0 && (
            <EmptyState title="No books yet">Upload a PDF picture book to get started.</EmptyState>
          )}
          {books.data && books.data.length > 0 && (
            <ul className="grid gap-4 xl:grid-cols-2">
              {books.data.map((b) => (
                <BookCard
                  key={b.id}
                  book={b}
                  onDeleted={(deleted) => {
                    setNotice(`“${deleted.title}” was deleted.`);
                    books.reload();
                  }}
                />
              ))}
            </ul>
          )}
        </section>
        <div className="order-1 lg:order-2">
          <UploadForm
            onUploaded={(_res, title) => {
              setNotice(`“${title}” was uploaded. Its pages are being processed; this list updates every 2 seconds.`);
              books.reload();
            }}
          />
        </div>
      </div>
    </>
  );
}
