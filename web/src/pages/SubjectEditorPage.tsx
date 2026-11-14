import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { ApiError, api } from '../api';
import { PageSurface, type EditorMode } from '../components/subjects/PageSurface';
import { PageHeader } from '../components/ui/AppShell';
import { Button } from '../components/ui/Button';
import { ErrorPanel, Loading, errorMessage } from '../components/ui/LoadState';
import { Badge, PageStateBadge } from '../components/ui/StatusBadge';
import { useAction } from '../hooks/useAction';
import { useApi } from '../hooks/useApi';
import { useBook } from '../hooks/useBook';
import type { NormPoint, Page } from '../types/api';
import { OUTLINE_PROBLEM_TEXT, outlineProblem, roundPoint } from '../utils/coordinates';
import { PAGE_STATE_HINT, formatConfidence } from '../utils/display';

/**
 * Contract 1 has no GET /pages/{id}, so the editor finds the page through its
 * book: `?book=` when the link supplies it, otherwise by scanning GET /books.
 */
async function findBookId(pageId: string, signal: AbortSignal): Promise<string> {
  const books = await api.listBooks(signal);
  const book = books.find((b) => b.pages.some((p) => p.id === pageId));
  if (!book) throw new ApiError('http', 'This page was not found.', 404);
  return book.id;
}

export function SubjectEditorPage() {
  const { id = '' } = useParams();
  const [params] = useSearchParams();
  const hint = params.get('book');
  const resolved = useApi((signal) => (hint ? Promise.resolve(hint) : findBookId(id, signal)), `${id}:${hint ?? ''}`);

  if (resolved.status === 'loading') return <Loading label="Loading page…" />;
  if (resolved.status === 'error' || !resolved.data) {
    return <ErrorPanel error={resolved.error} onRetry={resolved.reload} title="Could not load this page" />;
  }
  return <EditorForBook key={`${resolved.data}:${id}`} bookId={resolved.data} pageId={id} />;
}

function EditorForBook({ bookId, pageId }: { bookId: string; pageId: string }) {
  const { book, status, error, polling, refresh, replacePages } = useBook(bookId);
  const page = book?.pages.find((p) => p.id === pageId);

  const back = book && (
    <Link to={`/books/${encodeURIComponent(book.id)}/subjects`} className="font-semibold text-sky-800 underline">
      ← All pages of {book.title}
    </Link>
  );

  return (
    <>
      <PageHeader title={page ? `Page ${page.number} · choose the subject` : 'Subject editor'} back={back} />
      {status === 'loading' && <Loading label="Loading page…" />}
      {status === 'error' && <ErrorPanel error={error} onRetry={refresh} title="Could not load this page" />}
      {book && !page && <ErrorPanel error={new Error('This page is not in this book.')} title="Page not found" />}
      {page && (
        <Editor
          key={page.id}
          page={page}
          polling={polling}
          refreshError={status === 'success' ? error : null}
          onRetryRefresh={refresh}
          onUpdated={(p) => {
            replacePages([p]);
            refresh();
          }}
        />
      )}
    </>
  );
}

const MODES: { mode: EditorMode; label: string }[] = [
  { mode: 'suggestions', label: 'Suggestions' },
  { mode: 'point', label: 'Tap the object' },
  { mode: 'outline', label: 'Draw an outline' },
];

type Sent = { point?: NormPoint; outline?: NormPoint[] } | null;

function sourceText(source: string): string {
  if (source === 'manual') return 'outlined by teacher';
  if (source === 'click') return 'picked by tapping';
  return 'suggested by the AI';
}

function Editor({
  page,
  polling,
  refreshError,
  onRetryRefresh,
  onUpdated,
}: {
  page: Page;
  polling: boolean;
  refreshError: Error | null;
  onRetryRefresh: () => void;
  onUpdated: (page: Page) => void;
}) {
  const [mode, setMode] = useState<EditorMode>(page.candidates.length > 0 ? 'suggestions' : 'outline');
  const [point, setPoint] = useState<NormPoint | null>(null);
  const [tapHint, setTapHint] = useState<string | null>(null);
  const [outline, setOutline] = useState<NormPoint[]>([]);
  const [label, setLabel] = useState('');
  const [formError, setFormError] = useState<string | null>(null);
  const [sent, setSent] = useState<Sent>(null);
  const [showSent, setShowSent] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const action = useAction();

  const processing = page.state === 'processing';
  const busy = action.pending !== null;
  const selected = page.selected !== null ? page.candidates[page.selected] : undefined;
  const problem = outline.length ? outlineProblem(outline) : null;

  async function submit(name: string, body: Parameters<typeof api.setSubject>[1], after: () => void, message: string) {
    setNotice(null);
    const updated = await action.run(name, (s) => api.setSubject(page.id, body, s));
    if (updated) {
      after();
      onUpdated(updated);
      setNotice(message);
    }
  }

  function pickCandidate(i: number) {
    const name = page.candidates[i]?.label || 'that subject';
    void submit('candidate', { candidate: i }, () => setSent(null), `Subject changed to “${name}”. Check the highlight, then confirm.`);
  }

  function sendPoint() {
    if (!point) return;
    const p = roundPoint(point);
    void submit(
      'point',
      { point: p },
      () => {
        setSent({ point: p });
        setShowSent(true);
        setPoint(null);
      },
      'Cut out where you tapped. Check that the highlight covers the object, then confirm. If it missed, draw an outline instead.',
    );
  }

  function sendOutline() {
    const name = label.trim();
    if (!name) {
      setFormError('Type what the object is, for example “frog”.');
      return;
    }
    const pts = outline.map(roundPoint);
    const why = outlineProblem(pts);
    if (why) {
      setFormError(OUTLINE_PROBLEM_TEXT[why]);
      return;
    }
    setFormError(null);
    void submit(
      'outline',
      { label: name, outline: pts },
      () => {
        setSent({ outline: pts });
        setShowSent(true);
        setOutline([]);
        setLabel('');
      },
      `“${name}” cut out along your outline. The dashed line shows what you drew; check it matches the highlight, then confirm.`,
    );
  }

  async function confirm() {
    setNotice(null);
    const updated = await action.run('confirm', (s) => api.confirmPage(page.id, s));
    if (updated) {
      onUpdated(updated);
      setNotice('Subject confirmed.');
    }
  }

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <PageSurface
        page={page}
        mode={mode}
        disabled={busy || processing}
        onPickCandidate={pickCandidate}
        point={point}
        onPoint={(p, inside) => {
          setPoint(p);
          setTapHint(inside ? null : 'Tap on the picture itself.');
        }}
        outline={outline}
        onOutline={(pts) => {
          setOutline(pts);
          setFormError(null);
        }}
        sent={showSent ? sent : null}
      />

      <aside className="space-y-4">
        <section className="space-y-2 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200" aria-labelledby="current-h">
          <div className="flex flex-wrap items-center gap-2">
            <h2 id="current-h" className="text-lg font-bold">
              Current subject
            </h2>
            <PageStateBadge state={page.state} />
            {page.confirmed && <Badge tone="bg-emerald-700 text-white ring-emerald-800">Confirmed</Badge>}
            {page.omitted && <Badge tone="bg-slate-700 text-white ring-slate-800">Left out</Badge>}
          </div>
          {selected ? (
            <p>
              <span className="font-semibold">{selected.label || 'Unlabeled'}</span>
              <span className="text-slate-600">
                {' '}
                · {sourceText(selected.source)}
                {selected.source === 'auto' && `, confidence ${formatConfidence(selected.confidence)}`}
              </span>
            </p>
          ) : (
            <p className="text-slate-700">{processing ? 'Still processing; this updates every 2 seconds.' : 'None yet.'}</p>
          )}
          {!processing && !page.confirmed && <p className="text-sm text-slate-700">{PAGE_STATE_HINT[page.state]}</p>}
          {page.reason && <p className="text-sm text-slate-600">Reason: {page.reason}</p>}
          {page.omitted && <p className="text-sm text-slate-700">This page is left out of the reader. You can still set its subject.</p>}
          {selected && !page.confirmed && !processing && (
            <Button variant="primary" disabled={busy} onClick={() => void confirm()}>
              {action.pending === 'confirm' ? 'Confirming…' : 'Confirm this subject'}
            </Button>
          )}
          {polling && !refreshError && (
            <p role="status" className="text-sm text-slate-600">
              Updating every 2 seconds.
            </p>
          )}
          {refreshError && (
            <div role="alert" className="text-sm text-amber-950">
              Could not refresh: {errorMessage(refreshError)}{' '}
              <button type="button" className="font-semibold underline" onClick={onRetryRefresh}>
                Try again
              </button>
            </div>
          )}
        </section>

        <section className="space-y-3 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200" aria-label="Change the subject">
          <div className="grid grid-cols-3 gap-1 rounded-lg bg-slate-100 p-1" role="group" aria-label="How to choose">
            {MODES.map((m) => (
              <button
                key={m.mode}
                type="button"
                aria-pressed={mode === m.mode}
                onClick={() => {
                  setMode(m.mode);
                  setFormError(null);
                  setTapHint(null);
                }}
                className={`min-h-11 rounded-md px-2 text-sm font-semibold ${
                  mode === m.mode ? 'bg-white text-sky-900 shadow ring-1 ring-slate-300' : 'text-slate-700 hover:bg-white/60'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {mode === 'suggestions' && (
            <div className="space-y-2">
              {page.candidates.length === 0 ? (
                <p className="text-slate-700">No suggestions for this page. Tap the object, or draw an outline around it.</p>
              ) : (
                <>
                  <p className="text-slate-700">Tap a box on the page, or a name here.</p>
                  <ul className="space-y-2">
                    {page.candidates.map((c, i) => (
                      <li key={`${i}:${c.mask_hash}`}>
                        <button
                          type="button"
                          aria-pressed={page.selected === i}
                          disabled={busy || processing || page.selected === i}
                          onClick={() => pickCandidate(i)}
                          className={`flex min-h-11 w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left ring-1 ring-inset disabled:cursor-default ${
                            page.selected === i ? 'bg-sky-700 text-white ring-sky-800' : 'bg-white ring-slate-300 hover:bg-slate-50 disabled:opacity-60'
                          }`}
                        >
                          <span className="font-semibold">
                            {page.selected === i && '✓ '}
                            {c.label || 'Unlabeled'}
                          </span>
                          <span className={page.selected === i ? 'text-sky-100' : 'text-slate-600'}>
                            {c.source === 'auto' ? formatConfidence(c.confidence) : sourceText(c.source)}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}

          {mode === 'point' && (
            <div className="space-y-2">
              <p className="text-slate-700">Tap the object on the page. A ring marks the spot; then press Cut out.</p>
              {tapHint && (
                <p role="alert" className="text-amber-900">
                  {tapHint}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button variant="primary" disabled={!point || busy || processing} onClick={sendPoint}>
                  {action.pending === 'point' ? 'Cutting out…' : 'Cut out the object here'}
                </Button>
                {point && (
                  <Button disabled={busy} onClick={() => setPoint(null)}>
                    Clear spot
                  </Button>
                )}
              </div>
            </div>
          )}

          {mode === 'outline' && (
            <div className="space-y-2">
              <div>
                <label htmlFor="outline-label" className="font-semibold">
                  What is it?
                </label>
                <input
                  id="outline-label"
                  className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2 text-base focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-600/30"
                  value={label}
                  maxLength={60}
                  placeholder="for example, frog"
                  autoComplete="off"
                  onChange={(e) => {
                    setLabel(e.target.value);
                    setFormError(null);
                  }}
                />
              </div>
              <p className="text-slate-700">
                Draw one line around the object with a finger, pen or mouse. Lift to finish; the ends join up. The cut-out
                follows your line exactly, from the original picture.
              </p>
              {outline.length > 0 && !problem && <p className="text-sm text-slate-600">Outline ready ({outline.length} points).</p>}
              {problem && (
                <p role="alert" className="text-amber-900">
                  {OUTLINE_PROBLEM_TEXT[problem]}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button variant="primary" disabled={outline.length === 0 || problem !== null || busy || processing} onClick={sendOutline}>
                  {action.pending === 'outline' ? 'Cutting out…' : 'Save outline'}
                </Button>
                {outline.length > 0 && (
                  <Button disabled={busy} onClick={() => setOutline([])}>
                    Clear and redraw
                  </Button>
                )}
              </div>
            </div>
          )}

          {formError && (
            <p role="alert" className="font-semibold text-rose-800">
              {formError}
            </p>
          )}
          {action.error && (
            <p role="alert" className="rounded-lg bg-rose-50 p-3 text-rose-900 ring-1 ring-rose-200">
              {errorMessage(action.error)}
              {action.pending === null && mode === 'point' && ' You can draw an outline instead.'}
            </p>
          )}
          {notice && (
            <p role="status" className="rounded-lg bg-emerald-50 p-3 text-emerald-950 ring-1 ring-emerald-200">
              {notice}
            </p>
          )}
          {sent && (
            <label className="flex min-h-11 items-center gap-2 text-sm">
              <input type="checkbox" className="size-5" checked={showSent} onChange={(e) => setShowSent(e.target.checked)} />
              Show what I sent (dashed), to check it lines up
            </label>
          )}
        </section>
      </aside>
    </div>
  );
}
