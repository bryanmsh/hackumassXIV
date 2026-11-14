import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { api } from '../api';
import { SubjectPageCard } from '../components/subjects/SubjectPageCard';
import { PageHeader } from '../components/ui/AppShell';
import { Button } from '../components/ui/Button';
import { ErrorPanel, Loading, errorMessage } from '../components/ui/LoadState';
import { useAction } from '../hooks/useAction';
import { useBook } from '../hooks/useBook';
import type { Page } from '../types/api';
import { confirmablePages, processedCount, rerunnablePages, undecidedPages } from '../utils/pages';

/**
 * Subject review: every page with its highlighted subject. The teacher
 * confirms, picks another candidate, leaves pages out, retries failures and
 * processes Unsupported pages anyway. Nothing is confirmed automatically.
 */
export function SubjectReviewPage() {
  const { id = '' } = useParams();
  const { book, status, error, polling, refresh, replacePages } = useBook(id);
  const confirmAll = useAction();
  const [asking, setAsking] = useState(false);
  const rerun = useAction();
  const [askingRerun, setAskingRerun] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  function changed(pages: Page[]) {
    setNotice(null);
    replacePages(pages);
    refresh();
  }

  const pages = book?.pages ?? [];
  const confirmable = confirmablePages(pages);
  const undecided = undecidedPages(pages);
  const rerunnable = rerunnablePages(pages);
  const processed = processedCount(pages);

  async function doConfirmAll() {
    const updated = await confirmAll.run('confirm-all', (s) => api.confirmAll(id, s));
    setAsking(false);
    if (updated) {
      changed(updated);
      setNotice(`Confirmed ${updated.length} ${updated.length === 1 ? 'page' : 'pages'}.`);
    }
  }

  async function doRerun() {
    const updated = await rerun.run('rerun', (s) => api.rerunBook(id, s));
    setAskingRerun(false);
    if (updated) {
      changed(updated);
      setNotice(
        updated.length === 0
          ? 'No pages to ask about.'
          : `Asking the AI again about ${updated.length} ${updated.length === 1 ? 'page' : 'pages'}. New suggestions appear as each page finishes.`,
      );
    }
  }

  return (
    <>
      <PageHeader
        title={book ? `Subjects · ${book.title}` : 'Subject review'}
        back={
          <Link to="/" className="font-semibold text-sky-800 underline">
            ← Library
          </Link>
        }
      >
        {book && (
          <>
            <Button
              variant="primary"
              disabled={confirmable.length === 0 || confirmAll.pending !== null}
              onClick={() => {
                setNotice(null);
                setAskingRerun(false);
                setAsking(true);
              }}
            >
              Confirm all…
            </Button>
            <Button
              disabled={rerunnable.length === 0 || rerun.pending !== null}
              onClick={() => {
                setNotice(null);
                setAsking(false);
                setAskingRerun(true);
              }}
            >
              Ask the AI again…
            </Button>
            <Link
              to={`/books/${encodeURIComponent(id)}/approve`}
              className="inline-flex min-h-11 items-center rounded-lg px-4 font-semibold text-sky-800 ring-1 ring-inset ring-slate-300 hover:bg-slate-100"
            >
              Contact sheets →
            </Link>
          </>
        )}
      </PageHeader>

      {status === 'loading' && <Loading label="Loading pages…" />}
      {status === 'error' && <ErrorPanel error={error} onRetry={refresh} title="Could not load this book" />}

      {book && (
        <>
          <div className="mb-5 space-y-2 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <p className="text-lg">
              <strong>{pages.length - undecided.length}</strong> of {pages.length} pages decided
              {undecided.length > 0 && <> · {undecided.length} still need you (confirm a subject or leave the page out)</>}
              {processed < pages.length && <> · {pages.length - processed} processing</>}
            </p>
            <p className="text-slate-700">
              The AI’s confidence is its own guess, not a check that it is right. Look at each highlighted subject before
              you confirm it. Changing a page’s subject means that page needs approval again.
            </p>
            {polling && !error && (
              <p role="status" className="text-sm text-slate-600">
                Updating every 2 seconds while pages are processed.
              </p>
            )}
            {status === 'success' && error && (
              <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg bg-amber-50 p-3 text-amber-950 ring-1 ring-amber-200">
                <span>
                  {polling ? 'Could not update; trying again.' : 'Could not refresh this book.'} {errorMessage(error)}
                </span>
                {!polling && <Button onClick={refresh}>Try again</Button>}
              </div>
            )}
          </div>

          {asking && (
            <div role="dialog" aria-modal="false" aria-labelledby="confirm-all-h" className="mb-5 rounded-xl bg-sky-50 p-4 ring-1 ring-sky-300">
              <h2 id="confirm-all-h" className="text-lg font-bold">
                Confirm {confirmable.length} {confirmable.length === 1 ? 'subject' : 'subjects'}?
              </h2>
              <p className="mt-1">
                Pages {confirmable.map((p) => p.number).join(', ')} will be confirmed with the subject shown on each. Pages
                with no subject, left out, or still processing are not changed.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button variant="primary" disabled={confirmAll.pending !== null} onClick={() => void doConfirmAll()}>
                  {confirmAll.pending ? 'Confirming…' : `Confirm ${confirmable.length}`}
                </Button>
                <Button disabled={confirmAll.pending !== null} onClick={() => setAsking(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
          {askingRerun && (
            <div role="dialog" aria-modal="false" aria-labelledby="rerun-h" className="mb-5 rounded-xl bg-sky-50 p-4 ring-1 ring-sky-300">
              <h2 id="rerun-h" className="text-lg font-bold">
                Ask the AI again about {rerunnable.length} {rerunnable.length === 1 ? 'page' : 'pages'}?
              </h2>
              <p className="mt-1">
                Pages {rerunnable.map((p) => p.number).join(', ')} will be sent to the outside AI service again. Its answers
                can differ each time. New suggestions are added to the ones already there, and the subject on each of
                these pages becomes the AI’s new guess. Pages you have confirmed or left out are not changed.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button variant="primary" disabled={rerun.pending !== null} onClick={() => void doRerun()}>
                  {rerun.pending ? 'Asking…' : `Ask about ${rerunnable.length}`}
                </Button>
                <Button disabled={rerun.pending !== null} onClick={() => setAskingRerun(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
          {rerun.error && (
            <p role="alert" className="mb-5 rounded-lg bg-rose-50 p-3 text-rose-900 ring-1 ring-rose-200">
              Could not ask the AI again: {errorMessage(rerun.error)}
            </p>
          )}
          {confirmAll.error && (
            <p role="alert" className="mb-5 rounded-lg bg-rose-50 p-3 text-rose-900 ring-1 ring-rose-200">
              Confirm all failed: {errorMessage(confirmAll.error)}
            </p>
          )}
          {notice && (
            <p role="status" className="mb-5 rounded-lg bg-emerald-50 p-3 text-emerald-950 ring-1 ring-emerald-200">
              {notice}
            </p>
          )}

          {pages.length === 0 ? (
            <p className="text-slate-700">{book.state === 'ingesting' ? 'Reading the PDF… pages appear here shortly.' : 'This book has no pages.'}</p>
          ) : (
            <ul className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {pages.map((p) => (
                <SubjectPageCard key={p.id} page={p} onChanged={changed} />
              ))}
            </ul>
          )}
        </>
      )}
    </>
  );
}
