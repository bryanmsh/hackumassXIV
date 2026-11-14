import { useEffect, useId, useMemo, useState } from 'react';
import { api } from '../../api';
import { useApi } from '../../hooks/useApi';
import { usePreview } from '../../hooks/usePreview';
import type { Book, Level, Page, Settings } from '../../types/api';
import { levelName } from '../../utils/display';
import { Button } from '../ui/Button';
import { errorMessage } from '../ui/LoadState';

interface Sample {
  page: Page;
  book: Book;
  label: string;
}

/** Pages that can be previewed: a subject is chosen and processing is over. Confirmed pages first. */
function samplesFrom(books: Book[]): Sample[] {
  const out: Sample[] = [];
  for (const book of books) {
    for (const page of book.pages) {
      if (page.selected === null || page.state === 'processing') continue;
      const subject = page.candidates[page.selected]?.label || 'subject';
      out.push({ page, book, label: `${book.title} · page ${page.number} (${subject})` });
    }
  }
  return out.sort((a, b) => Number(b.page.confirmed) - Number(a.page.confirmed));
}

/**
 * Live preview of UNSAVED settings on one sample page (POST /preview, at most
 * every 300 ms). Not a saved version, not approved, never shown to a child.
 */
export function ProfilePreview({ settings, level }: { settings: Settings; level: Level | null }) {
  const id = useId();
  const books = useApi((signal) => api.listBooks(signal), 'preview-books');
  const samples = useMemo(() => samplesFrom(books.data ?? []), [books.data]);
  const [pageId, setPageId] = useState<string | null>(null);

  useEffect(() => {
    if (pageId === null && samples[0]) setPageId(samples[0].page.id);
  }, [pageId, samples]);

  const sample = samples.find((s) => s.page.id === pageId) ?? samples[0];
  const input = sample && level !== null ? { page_id: sample.page.id, settings, level } : null;
  const preview = usePreview(input);
  const ratio = sample ? `${sample.page.width} / ${sample.page.height}` : '4 / 3';

  return (
    <section aria-labelledby={`${id}-h`} className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id={`${id}-h`} className="text-lg font-bold">
          Preview
        </h3>
        <span className="text-sm text-slate-600">Unsaved settings · not approved for reading</span>
      </div>

      {books.status === 'loading' && <p className="text-slate-600">Finding a sample page…</p>}
      {books.status === 'error' && (
        <p role="alert" className="text-rose-900">
          Could not load sample pages: {errorMessage(books.error)}{' '}
          <button type="button" className="font-semibold underline" onClick={books.reload}>
            Try again
          </button>
        </p>
      )}
      {books.status === 'success' && samples.length === 0 && (
        <p className="rounded-lg bg-slate-100 p-3 text-slate-700">
          The preview needs a page with a chosen subject. Upload a book and review its subjects first.
        </p>
      )}

      {samples.length > 0 && (
        <>
          <div>
            <label htmlFor={`${id}-page`} className="text-sm font-semibold">
              Sample page
            </label>
            <select
              id={`${id}-page`}
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 text-base"
              value={sample?.page.id ?? ''}
              onChange={(e) => setPageId(e.target.value)}
            >
              {samples.map((s) => (
                <option key={s.page.id} value={s.page.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          <div className="relative overflow-hidden rounded-xl bg-slate-200 ring-1 ring-slate-300" style={{ aspectRatio: ratio }}>
            {preview.url && (
              <img
                src={preview.url}
                alt={`Preview of ${sample?.label ?? 'the sample page'}${level !== null ? ` in ${levelName(level)}` : ''}`}
                className={`absolute inset-0 h-full w-full object-contain ${preview.current ? '' : 'opacity-60'}`}
                draggable={false}
              />
            )}
            {level === null && <Overlay>Choose a look to see the preview.</Overlay>}
            {level !== null && !preview.url && preview.status === 'loading' && <Overlay>Making the preview…</Overlay>}
            {preview.url && !preview.current && preview.status === 'loading' && (
              <span role="status" className="absolute right-2 top-2 rounded bg-black/70 px-2 py-1 text-sm text-white">
                Updating…
              </span>
            )}
            {preview.status === 'error' && (
              <Overlay>
                <span role="alert" className="text-rose-900">
                  Preview unavailable: {errorMessage(preview.error)}
                </span>
                <Button className="mt-2" onClick={preview.retry}>
                  Try again
                </Button>
              </Overlay>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function Overlay({ children }: { children: React.ReactNode }) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-100/80 p-4 text-center text-slate-700">{children}</div>
  );
}
