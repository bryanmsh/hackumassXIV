import { useEffect, useState } from 'react';
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
import { SubjectMarker } from '../components/subjects/SubjectMarker';
import { OUTLINE_PROBLEM_TEXT, outlineBox, outlineProblem, roundPoint, sameBox } from '../utils/coordinates';
import { PAGE_STATE_HINT, formatConfidence, sourceLabel } from '../utils/display';
import { plainReason } from '../utils/secondLook';
import { subjectTone } from '../utils/subjectColors';

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
  { mode: 'point', label: 'Click the object' },
  { mode: 'refine', label: 'Add a missing part' },
  { mode: 'outline', label: 'Draw an outline' },
];

type Sent = { point?: NormPoint; outline?: NormPoint[] } | null;

/** What the last saved outline became, so the teacher can fall back to her own drawing or redraw. */
interface OutlineResult {
  label: string;
  outline: NormPoint[];
  /** The server tightened the drawing to the object (its box moved). */
  tightened: boolean;
  /** The subject this belongs to; a change made elsewhere drops the offer. */
  hash: string | null;
}

/** What the page shows over the picture while the server works. */
const BUSY_LABEL: Record<string, string> = {
  outline: 'Finding the object’s edges…',
  'outline-raw': 'Cutting out along your outline…',
  point: 'Cutting out…',
  refine: 'Adding the part…',
};


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
  const [together, setTogether] = useState<number[]>([]);
  const [highlight, setHighlight] = useState<number | null>(null);
  const [outlineResult, setOutlineResult] = useState<OutlineResult | null>(null);
  const action = useAction();
  // Ticks belong to the subject they were made against: a new subject (picked, tapped,
  // outlined, joined, or changed elsewhere) or another tool clears them.
  useEffect(() => setTogether([]), [page.subject_hash, mode]);

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

  function showTogether() {
    const picked = [...together].sort((a, b) => a - b);
    const names = picked.map((i) => page.candidates[i]?.label || 'object').join(' and ');
    void submit(
      'together',
      { candidates: picked },
      () => {
        setSent(null);
        setTogether([]);
      },
      `Now showing ${names} together. Check the highlight covers each one, then confirm.`,
    );
  }

  function sendRefine() {
    if (!point) return;
    const p = roundPoint(point);
    void submit(
      'refine',
      { refine_point: p },
      () => {
        setSent({ point: p });
        setShowSent(true);
        setPoint(null);
      },
      'Added the part you clicked to the cut-out. Check the highlight now covers it, then confirm.',
    );
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
      'Cut out where you clicked. Check that the highlight covers the object, then confirm. If it missed, draw an outline instead.',
    );
  }

  async function sendOutline() {
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
    setNotice(null);
    // The drawing is a hint: the cut-out tool may tighten it to the object (tidy). A server
    // without that option answers 422, and then the drawing is used exactly as it is.
    let tidyTried = true;
    const updated = await action.run('outline', async (s) => {
      try {
        return await api.setSubject(page.id, { label: name, outline: pts, tidy: true }, s);
      } catch (err) {
        if (err instanceof ApiError && err.status === 422) {
          tidyTried = false;
          return api.setSubject(page.id, { label: name, outline: pts }, s);
        }
        throw err;
      }
    });
    if (!updated) return;
    const chosen = updated.selected !== null ? updated.candidates[updated.selected] : undefined;
    const tightened = tidyTried && chosen !== undefined && !sameBox(chosen.box, outlineBox(pts));
    setSent({ outline: pts });
    setShowSent(true);
    setOutline([]);
    setLabel('');
    setOutlineResult({ label: name, outline: pts, tightened, hash: updated.subject_hash });
    onUpdated(updated);
    setNotice(
      tightened
        ? `The cut-out tool tightened your outline to “${name}”. The dashed line is what you drew; check that the highlight hugs the object, then confirm.`
        : tidyTried
          ? `Couldn’t find the object’s edges. Using your outline for “${name}” as drawn. Check the highlight, then confirm.`
          : `“${name}” cut out along your outline. The dashed line shows what you drew; check it matches the highlight, then confirm.`,
    );
  }

  /** Back to exactly what the teacher drew, with no tightening. */
  async function useMyOutline() {
    const r = outlineResult;
    if (!r) return;
    setNotice(null);
    const updated = await action.run('outline-raw', (s) => api.setSubject(page.id, { label: r.label, outline: r.outline }, s));
    if (!updated) return;
    setSent({ outline: r.outline });
    setShowSent(true);
    setOutlineResult({ ...r, tightened: false, hash: updated.subject_hash });
    onUpdated(updated);
    setNotice(`Using your outline for “${r.label}” exactly as drawn. Check the highlight, then confirm.`);
  }

  function redraw() {
    const r = outlineResult;
    setMode('outline');
    setOutline([]);
    setLabel(r?.label ?? '');
    setSent(null);
    setOutlineResult(null);
    setNotice(null);
    setFormError(null);
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
          setTapHint(inside ? null : 'Click on the picture itself.');
        }}
        outline={outline}
        onOutline={(pts) => {
          setOutline(pts);
          setFormError(null);
        }}
        sent={showSent ? sent : null}
        highlight={highlight}
        onHighlight={setHighlight}
        busyLabel={action.pending ? (BUSY_LABEL[action.pending] ?? null) : null}
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
                · {sourceLabel(selected.source)}
                {selected.source === 'auto' && `, confidence ${formatConfidence(selected.confidence)}`}
              </span>
            </p>
          ) : (
            <p className="text-slate-700">{processing ? 'Still processing; this updates every 2 seconds.' : 'None yet.'}</p>
          )}
          {!processing && !page.confirmed && <p className="text-sm text-slate-700">{PAGE_STATE_HINT[page.state]}</p>}
          {plainReason(page.reason) && <p className="text-sm text-slate-600">Reason: {plainReason(page.reason)}</p>}
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
          <div className="grid grid-cols-2 gap-1 rounded-lg bg-slate-100 p-1" role="group" aria-label="How to choose">
            {MODES.map((m) => (
              <button
                key={m.mode}
                type="button"
                aria-pressed={mode === m.mode}
                onClick={() => {
                  setMode(m.mode);
                  setFormError(null);
                  setTapHint(null);
                  setPoint(null);
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
                <p className="text-slate-700">No suggestions for this page. Click the object, or draw an outline around it.</p>
              ) : (
                <>
                  <p className="text-slate-700">
                    Each suggestion has a number and colour, the same on the page and here. Click a box on the page, or a name here.
                    When the story needs more than one, tick each and show them together.
                  </p>
                  <ul className="space-y-2">
                    {page.candidates.map((c, i) => (
                      <li key={`${i}:${c.mask_hash}`} className="flex items-center gap-2">
                        {/* The whole 44 px square is clickable, not just the box. */}
                        <label className="flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-lg hover:bg-slate-100">
                          <input
                            type="checkbox"
                            className="size-6 cursor-pointer"
                            aria-label={`Include ${c.label || 'this object'}`}
                            disabled={busy || processing}
                            checked={together.includes(i)}
                            onChange={(e) => setTogether((t) => (e.target.checked ? [...t, i] : t.filter((x) => x !== i)))}
                          />
                        </label>
                        <button
                          type="button"
                          aria-pressed={page.selected === i}
                          disabled={busy || processing || page.selected === i}
                          onClick={() => pickCandidate(i)}
                          onMouseEnter={() => setHighlight(i)}
                          onMouseLeave={() => setHighlight(null)}
                          onFocus={() => setHighlight(i)}
                          onBlur={() => setHighlight(null)}
                          className={`flex min-h-11 w-full items-center gap-2 rounded-lg px-3 py-2 text-left ring-inset disabled:cursor-default ${
                            page.selected === i
                              ? `${subjectTone(i).tint} font-semibold ring-2 ${subjectTone(i).ring}`
                              : 'bg-white ring-1 ring-slate-300 hover:bg-slate-50 disabled:opacity-60'
                          } ${highlight !== null && highlight !== i ? 'opacity-50' : ''}`}
                        >
                          <SubjectMarker index={i} size="sm" />
                          <span className={`min-w-0 flex-1 truncate ${page.selected === i ? '' : 'font-medium'}`}>
                            {page.selected === i && '● '}
                            {c.label || 'Unlabeled'}
                          </span>
                          <span className="shrink-0 text-sm text-slate-600">
                            {c.source === 'auto' ? formatConfidence(c.confidence) : sourceLabel(c.source)}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                  {together.length >= 2 && (
                    <Button variant="primary" disabled={busy || processing} onClick={showTogether}>
                      {action.pending === 'together' ? 'Joining…' : `Show these ${together.length} together`}
                    </Button>
                  )}
                  {together.length === 1 && <p className="text-sm text-slate-600">Tick one more to show them together.</p>}
                </>
              )}
            </div>
          )}

          {mode === 'refine' && (
            <div className="space-y-2">
              {selected ? (
                <p className="text-slate-700">
                  Click a part of <span className="font-semibold">{selected.label || 'the subject'}</span> that the cut-out missed, such as
                  a tail or an ear. It is added to the current cut-out; the subject keeps its name.
                </p>
              ) : (
                <p className="text-slate-700">Pick a subject first. Then this adds any part the cut-out missed.</p>
              )}
              {tapHint && (
                <p role="alert" className="text-amber-900">
                  {tapHint}
                </p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button variant="primary" disabled={!point || !selected || busy || processing} onClick={sendRefine}>
                  {action.pending === 'refine' ? 'Adding…' : 'Add this part'}
                </Button>
                {point && (
                  <Button disabled={busy} onClick={() => setPoint(null)}>
                    Clear spot
                  </Button>
                )}
              </div>
            </div>
          )}

          {mode === 'point' && (
            <div className="space-y-2">
              <p className="text-slate-700">Click the object on the page. A ring marks the spot; then press Cut out.</p>
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
                Hold the mouse button down and draw one line around the object. Let go to finish; the ends join up. The cut-out
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
              {action.pending === null && (mode === 'point' || mode === 'refine') && ' You can draw an outline instead.'}
            </p>
          )}
          {notice && (
            <p role="status" className="rounded-lg bg-emerald-50 p-3 text-emerald-950 ring-1 ring-emerald-200">
              {notice}
            </p>
          )}
          {outlineResult && outlineResult.hash === page.subject_hash && (
            <div className="flex flex-wrap gap-2">
              {outlineResult.tightened && (
                <Button disabled={busy} onClick={() => void useMyOutline()}>
                  {action.pending === 'outline-raw' ? 'Saving…' : 'Use my outline'}
                </Button>
              )}
              <Button variant="ghost" disabled={busy} onClick={redraw}>
                Redraw
              </Button>
            </div>
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
