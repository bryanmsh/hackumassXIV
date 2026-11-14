import { useState } from 'react';
import { Link } from 'react-router';
import { api } from '../../api';
import { useAction } from '../../hooks/useAction';
import type { Page } from '../../types/api';
import { PAGE_STATE_HINT, formatConfidence, sourceLabel } from '../../utils/display';
import { subjectTone } from '../../utils/subjectColors';
import { plainReason, secondLookText } from '../../utils/secondLook';
import { OverlayImage } from '../books/OverlayImage';
import { Button } from '../ui/Button';
import { errorMessage } from '../ui/LoadState';
import { Badge, PageStateBadge } from '../ui/StatusBadge';
import { SubjectMarker } from './SubjectMarker';

const FLAG_TEXT: Record<string, string> = {
  spread: 'Looks like a two-page spread.',
  low_quality: 'The artwork is low resolution; the cut-out may look rough.',
};


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
  /**
   * The suggestions the teacher tapped to show together, and the subject that made. It only
   * counts while that is still the page's subject; a change made anywhere else drops it.
   */
  const [joined, setJoined] = useState<{ parts: number[]; hash: string | null } | null>(null);
  const parts = joined && joined.hash === page.subject_hash ? joined.parts : page.selected !== null ? [page.selected] : [];
  const hiddenChip = (i: number) => parts.length > 1 && page.selected === i; // the joined subject shows as its ticked parts

  /** Tapping a suggestion adds it to the subject or takes it out; the result is saved at once. */
  async function toggle(i: number) {
    const next = (parts.includes(i) ? parts.filter((x) => x !== i) : [...parts, i]).sort((a, b) => a - b);
    if (next.length === 0) return;
    const body = next.length === 1 ? { candidate: next[0]! } : { candidates: next };
    const updated = await action.run('candidate', (s) => api.setSubject(page.id, body, s));
    if (updated) {
      setJoined(next.length > 1 ? { parts: next, hash: updated.subject_hash } : null);
      onChanged([updated]);
    }
  }

  async function act(name: string, fn: (signal: AbortSignal) => Promise<Page>) {
    const updated = await action.run(name, fn);
    if (updated) onChanged([updated]);
  }

  return (
    <li className={`flex flex-col overflow-hidden rounded-xl bg-white shadow-sm ring-1 ${page.omitted ? 'ring-slate-300' : 'ring-slate-200'}`}>
      <div className={`relative ${page.omitted ? 'opacity-60' : ''}`}>
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
                <span className="text-slate-600"> · the AI’s guess, confidence {formatConfidence(selected.confidence)}</span>
              ) : (
                <span className="text-slate-600"> · {sourceLabel(selected.source)}</span>
              )}
            </>
          ) : (
            <span className="text-slate-700">{processing ? 'Still processing.' : 'No subject chosen yet.'}</span>
          )}
        </p>

        {!page.confirmed && !page.omitted && <p className="text-slate-700">{PAGE_STATE_HINT[page.state]}</p>}
        {page.omitted && <p className="text-slate-700">This page is skipped in the reader.</p>}
        {plainReason(page.reason) && <p className="text-sm text-slate-600">Reason: {plainReason(page.reason)}</p>}
        {page.flags.map((f) => (
          <p key={f} className="text-sm text-amber-900">
            ⚠ {FLAG_TEXT[f] ?? f}
          </p>
        ))}
        {page.second_look && page.confirmed && (
          <p className="text-sm text-slate-700">
            Second look: {secondLookText(page.second_look)}
          </p>
        )}

        {!processing && !page.omitted && page.candidates.length > 0 && (
          <fieldset>
            <legend className="text-sm font-semibold text-slate-700">
              {page.candidates.length > 1 ? 'Choose the subject' : 'Suggested subject'}
            </legend>
            {page.candidates.length > 1 && (
              <p className="text-sm text-slate-700">
                Each suggestion is tinted in its own colour on the page. Click more than one to show them together; click again to take one out.
              </p>
            )}
            <div className="mt-1 flex flex-wrap gap-2">
              {page.candidates.map((c, i) => {
                // The joined subject is shown by its ticked parts, not as a chip of its own.
                if (hiddenChip(i)) return null;
                const isSel = parts.includes(i);
                const tone = subjectTone(i);
                return (
                  <button
                    key={`${i}:${c.mask_hash}`}
                    type="button"
                    aria-pressed={isSel}
                    disabled={busy || (isSel && parts.length === 1)}
                    onClick={() => void toggle(i)}
                    className={`inline-flex min-h-11 items-center gap-2 rounded-full py-1 pl-1 pr-3 text-base ring-inset disabled:cursor-default ${
                      isSel
                        ? `${tone.tint} font-semibold text-slate-900 ring-2 ${tone.ring}`
                        : 'bg-white text-slate-900 ring-1 ring-slate-300 hover:bg-slate-100 disabled:opacity-60'
                    }`}
                  >
                    <SubjectMarker index={i} size="sm" />
                    {isSel && <span aria-hidden>●</span>}
                    <span className={isSel ? '' : 'font-medium'}>{c.label || 'Unlabeled'}</span>
                    <span className="text-sm text-slate-600">{c.source === 'auto' ? formatConfidence(c.confidence) : `(${sourceLabel(c.source)})`}</span>
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
