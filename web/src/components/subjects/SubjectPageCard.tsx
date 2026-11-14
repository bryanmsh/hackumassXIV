import { Link } from 'react-router';
import { api } from '../../api';
import { useAction } from '../../hooks/useAction';
import type { Page } from '../../types/api';
import { PAGE_STATE_HINT, formatConfidence } from '../../utils/display';
import { OverlayImage } from '../books/OverlayImage';
import { Button } from '../ui/Button';
import { errorMessage } from '../ui/LoadState';
import { Badge, PageStateBadge } from '../ui/StatusBadge';

const FLAG_TEXT: Record<string, string> = {
  spread: 'Looks like a two-page spread.',
  low_quality: 'The artwork is low resolution; the cut-out may look rough.',
};

function sourceText(source: string): string | null {
  if (source === 'manual') return 'outlined by teacher';
  if (source === 'click') return 'picked by click';
  return null;
}

/**
 * One page in Subject review: the original page with the subject highlighted,
 * its state, and the teacher's actions. Every action calls the API, then the
 * parent refetches the book (the server stays the authority).
 */
export function SubjectPageCard({ page, onChanged }: { page: Page; onChanged: (pages: Page[]) => void }) {
  const action = useAction();
  const busy = action.pending !== null;
  const processing = page.state === 'processing';
  const selected = page.selected !== null ? page.candidates[page.selected] : undefined;

  async function act(name: string, fn: (signal: AbortSignal) => Promise<Page>) {
    const updated = await action.run(name, fn);
    if (updated) onChanged([updated]);
  }

  return (
    <li className={`flex flex-col overflow-hidden rounded-xl bg-white shadow-sm ring-1 ${page.omitted ? 'ring-slate-300' : 'ring-slate-200'}`}>
      <div className={page.omitted ? 'opacity-60' : ''}>
        <OverlayImage page={page} />
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-bold">Page {page.number}</h2>
          <PageStateBadge state={page.state} />
          {page.confirmed && <Badge tone="bg-emerald-700 text-white ring-emerald-800">Confirmed</Badge>}
          {page.omitted && <Badge tone="bg-slate-700 text-white ring-slate-800">Left out</Badge>}
        </div>

        <p>
          {selected ? (
            <>
              Subject: <span className="font-semibold">{selected.label || 'Unlabeled'}</span>
              {selected.source === 'auto' ? (
                <span className="text-slate-600"> · AI confidence {formatConfidence(selected.confidence)}</span>
              ) : (
                <span className="text-slate-600"> · {sourceText(selected.source)}</span>
              )}
            </>
          ) : (
            <span className="text-slate-700">{processing ? 'Still processing.' : 'No subject chosen yet.'}</span>
          )}
        </p>

        {!page.confirmed && !page.omitted && <p className="text-slate-700">{PAGE_STATE_HINT[page.state]}</p>}
        {page.omitted && <p className="text-slate-700">This page is skipped in the reader.</p>}
        {page.reason && <p className="text-sm text-slate-600">Reason: {page.reason}</p>}
        {page.flags.map((f) => (
          <p key={f} className="text-sm text-amber-900">
            ⚠ {FLAG_TEXT[f] ?? f}
          </p>
        ))}
        {page.second_look && page.confirmed && (
          <p className="text-sm text-slate-700">
            {page.second_look.status === 'pending' && 'Second look: still checking.'}
            {page.second_look.status === 'pass' && 'Second look: named the same subject.'}
            {page.second_look.status === 'warn' &&
              (page.second_look.answer?.trim()
                ? `Second look: named “${page.second_look.answer}”. Worth a glance; it can be wrong too.`
                : `Second look: ${page.second_look.detail ?? 'could not name the subject.'}`)}
          </p>
        )}

        {!processing && !page.omitted && page.candidates.length > 0 && (
          <fieldset>
            <legend className="text-sm font-semibold text-slate-700">
              {page.candidates.length > 1 ? 'Choose the subject' : 'Suggested subject'}
            </legend>
            <div className="mt-1 flex flex-wrap gap-2">
              {page.candidates.map((c, i) => {
                const isSel = page.selected === i;
                return (
                  <button
                    key={`${i}:${c.mask_hash}`}
                    type="button"
                    aria-pressed={isSel}
                    disabled={busy || isSel}
                    onClick={() => void act('candidate', (s) => api.setSubject(page.id, { candidate: i }, s))}
                    className={`inline-flex min-h-11 items-center gap-1 rounded-full px-3 text-base ring-1 ring-inset disabled:cursor-default ${
                      isSel
                        ? 'bg-sky-700 font-semibold text-white ring-sky-800'
                        : 'bg-white text-slate-900 ring-slate-300 hover:bg-slate-100 disabled:opacity-60'
                    }`}
                  >
                    {isSel && <span aria-hidden>✓</span>}
                    {c.label || 'Unlabeled'}
                    {c.source === 'auto' && <span className={isSel ? 'text-sky-100' : 'text-slate-600'}>{formatConfidence(c.confidence)}</span>}
                    {c.source !== 'auto' && <span className={isSel ? 'text-sky-100' : 'text-slate-600'}>({sourceText(c.source)})</span>}
                  </button>
                );
              })}
            </div>
          </fieldset>
        )}

        {action.error && (
          <p role="alert" className="rounded-lg bg-rose-50 p-2 text-rose-900 ring-1 ring-rose-200">
            {errorMessage(action.error)}
          </p>
        )}

        <div className="mt-auto flex flex-wrap gap-2 pt-1">
          {!processing && !page.omitted && selected && !page.confirmed && (
            <Button variant="primary" disabled={busy} onClick={() => void act('confirm', (s) => api.confirmPage(page.id, s))}>
              {action.pending === 'confirm' ? 'Confirming…' : 'Confirm'}
            </Button>
          )}
          {page.state === 'failed' && !page.omitted && (
            <Button disabled={busy} onClick={() => void act('retry', (s) => api.retryPage(page.id, { force: false }, s))}>
              {action.pending === 'retry' ? 'Retrying…' : 'Retry'}
            </Button>
          )}
          {page.state === 'unsupported' && !page.omitted && (
            <Button disabled={busy} onClick={() => void act('force', (s) => api.retryPage(page.id, { force: true }, s))}>
              {action.pending === 'force' ? 'Starting…' : 'Process anyway'}
            </Button>
          )}
          {!processing && (
            <Button
              variant={page.omitted ? 'secondary' : 'ghost'}
              disabled={busy}
              onClick={() => void act('omit', (s) => api.omitPage(page.id, !page.omitted, s))}
            >
              {action.pending === 'omit' ? 'Saving…' : page.omitted ? 'Include again' : 'Leave out'}
            </Button>
          )}
          {!processing && !page.omitted && (
            <Link
              to={`/pages/${encodeURIComponent(page.id)}?book=${encodeURIComponent(page.book_id)}`}
              className="inline-flex min-h-11 items-center rounded-lg px-3 font-semibold text-sky-800 underline hover:bg-sky-50"
            >
              {page.state === 'failed' || page.candidates.length === 0 ? 'Outline by hand' : 'Pick on the page'}
            </Link>
          )}
        </div>
      </div>
    </li>
  );
}
