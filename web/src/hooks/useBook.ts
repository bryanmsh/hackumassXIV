import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, api, isAbortError } from '../api';
import type { Book, Page } from '../types/api';
import { isBookBusy } from '../utils/pages';

/** The spec: poll GET /books/{id} every 2 seconds while anything is in progress. */
export const BOOK_POLL_MS = 2000;

export interface BookState {
  book: Book | undefined;
  /** 'loading' only before the first answer; later failures keep the last book visible. */
  status: 'loading' | 'success' | 'error';
  /** Last failure, cleared by the next successful load. */
  error: ApiError | Error | null;
  /** True while the book is busy and updates are being fetched. */
  polling: boolean;
  /** Fetch now (after a mutation); polling resumes automatically while busy. */
  refresh: () => void;
  /** Put a page returned by a mutation into the book at once. */
  replacePages: (pages: Page[]) => void;
}

/** Network blips and server errors are worth another try; 4xx answers are not. */
function retryable(err: unknown): boolean {
  if (!(err instanceof ApiError)) return true;
  if (err.kind === 'network') return true;
  if (err.kind === 'http' && err.status !== null) return err.status >= 500 || err.status === 408 || err.status === 429;
  return false;
}

/**
 * Load one book and keep it fresh: while the book is ingesting or any page is
 * Processing, refetch every `intervalMs` (one request at a time, never
 * overlapping). Stops when nothing is in progress, on a non-retryable error,
 * and on unmount. One failed page never blocks the others; it is just a state.
 */
export function useBook(bookId: string, opts: { initial?: Book; intervalMs?: number } = {}): BookState {
  const { initial, intervalMs = BOOK_POLL_MS } = opts;
  const [book, setBook] = useState<Book | undefined>(initial);
  const [status, setStatus] = useState<BookState['status']>(initial ? 'success' : 'loading');
  const [error, setError] = useState<ApiError | Error | null>(null);
  const [stopped, setStopped] = useState(false);
  const [nonce, setNonce] = useState(0);

  // Which refresh request has been answered. A ref (not state) so React
  // StrictMode's double effect run still fetches: it is only set on completion.
  const answered = useRef(initial ? 0 : -1);
  const bookRef = useRef(book);
  bookRef.current = book;

  // A newer copy from a parent list (e.g. the Library reloaded) replaces ours.
  useEffect(() => {
    if (initial) {
      setBook(initial);
      setStopped(false);
    }
  }, [initial]);

  const busy = book !== undefined && isBookBusy(book);

  useEffect(() => {
    const ctrl = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    let done = false;
    const myNonce = nonce;

    const run = async () => {
      try {
        const next = await api.getBook(bookId, ctrl.signal);
        if (done) return;
        answered.current = myNonce;
        setBook(next);
        setError(null);
        setStatus('success');
        setStopped(false);
        if (isBookBusy(next)) timer = setTimeout(() => void run(), intervalMs);
      } catch (err) {
        if (done || isAbortError(err)) return;
        answered.current = myNonce;
        setError(err instanceof Error ? err : new Error(String(err)));
        setStatus(bookRef.current ? 'success' : 'error');
        const current = bookRef.current;
        if (current && isBookBusy(current) && retryable(err)) {
          timer = setTimeout(() => void run(), intervalMs);
        } else {
          setStopped(true);
        }
      }
    };

    if (answered.current !== nonce) void run();
    else if (busy && !stopped) timer = setTimeout(() => void run(), intervalMs);

    return () => {
      done = true;
      ctrl.abort();
      if (timer !== undefined) clearTimeout(timer);
    };
  }, [bookId, nonce, busy, stopped, intervalMs]);

  const refresh = useCallback(() => {
    setStopped(false);
    setNonce((n) => n + 1);
  }, []);

  const replacePages = useCallback((pages: Page[]) => {
    if (!pages.length) return;
    const byId = new Map(pages.map((p) => [p.id, p]));
    setBook((b) => (b ? { ...b, pages: b.pages.map((p) => byId.get(p.id) ?? p) } : b));
  }, []);

  return { book, status, error, polling: busy && !stopped, refresh, replacePages };
}
