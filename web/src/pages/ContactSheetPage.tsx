import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { api } from '../api';
import { CHECK_LABEL, problems } from '../components/approval/ChecksList';
import { SheetPageCard } from '../components/approval/SheetPageCard';
import { PageHeader } from '../components/ui/AppShell';
import { Button } from '../components/ui/Button';
import { ErrorPanel, Loading, errorMessage } from '../components/ui/LoadState';
import { useAction } from '../hooks/useAction';
import { useApi } from '../hooks/useApi';
import type { ApproveRequest, Decision, Level, Sheet, SheetPage } from '../types/api';
import { LEVELS, levelName } from '../utils/display';

/** While a second look is pending, refetch the sheet this often so it lands on screen. */
export const SHEET_POLL_MS = 3000;

function parseLevel(raw: string | null): Level | null {
  const n = Number(raw);
  return n === 1 || n === 2 || n === 3 || n === 4 ? n : null;
}

interface LookAgain {
  numbers: number[];
  recorded: number;
}

/**
 * Contact sheet: the exact version of every page for one child and look, its
 * checks, and the teacher's approval. Approve sends each page's `version`
 * exactly as this sheet received it. On 409 the sheet reloads and the changed
 * pages must be looked at again; nothing is ever re-sent automatically.
 */
export function ContactSheetPage() {
  const { id = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const profileId = params.get('profile');
  const level = parseLevel(params.get('level'));

  const book = useApi((signal) => api.getBook(id, signal), id);
  const profiles = useApi((signal) => api.listProfiles(signal), 'profiles');
  const ready = profileId !== null && level !== null;
  const selKey = `${id}:${profileId ?? ''}:${level ?? ''}`;
  const sheet = useApi(
    (signal) => (profileId && level ? api.getSheet(id, { profile: profileId, level }, signal) : Promise.resolve(null)),
    selKey,
  );

  const action = useAction();
  // After any decision the sheet reloads. Until the fresh sheet arrives, the cards
  // still hold the versions that were just sent (or refused), so decisions wait.
  const [staleSheet, setStaleSheet] = useState<Sheet | null>(null);
  const [asking, setAsking] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [lookAgain, setLookAgain] = useState<LookAgain | null>(null);
  const [changedIds, setChangedIds] = useState<Set<string>>(new Set());

  // A different child, look or book is a different sheet: drop per-sheet messages.
  useEffect(() => {
    setAsking(false);
    setNotice(null);
    setLookAgain(null);
    setChangedIds(new Set());
    setStaleSheet(null);
  }, [selKey]);

  // Second look runs in the background after Confirm; keep the sheet fresh until it lands.
  const pending = sheet.data?.pages.some((p) => p.second_look?.status === 'pending') ?? false;
  const { reload } = sheet;
  useEffect(() => {
    if (!pending || sheet.status !== 'success') return;
    const t = setTimeout(reload, SHEET_POLL_MS);
    return () => clearTimeout(t);
  }, [pending, sheet.data, sheet.status, reload]);

  const waitingForFresh = staleSheet !== null && sheet.data === staleSheet && sheet.status !== 'error';
  const deciding = action.pending !== null || waitingForFresh;
  const profile = profiles.data?.find((p) => p.id === profileId);
  const pages = useMemo(() => sheet.data?.pages ?? [], [sheet.data]);
  const aspectOf = (pageId: string) => {
    const pg = book.data?.pages.find((p) => p.id === pageId);
    return pg && pg.width > 0 && pg.height > 0 ? `${pg.width} / ${pg.height}` : '4 / 3';
  };

  const withVersion = pages.filter((p) => p.version !== null);
  const toApprove = withVersion.filter((p) => p.approval === 'none');
  const counts = {
    approved: withVersion.filter((p) => p.approval === 'approved').length,
    rejected: withVersion.filter((p) => p.approval === 'rejected').length,
    open: toApprove.length,
    notReady: pages.filter((p) => p.version === null && !p.omitted).length,
    omitted: pages.filter((p) => p.omitted).length,
  };
  const flagged = toApprove.filter((p) => problems(p.checks).length > 0);

  function update(key: 'profile' | 'level', value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    // Picking a child starts on that child's own look; the teacher can change it.
    if (key === 'profile' && value && !next.get('level')) {
      const p = profiles.data?.find((x) => x.id === value);
      if (p) next.set('level', String(p.level));
    }
    setParams(next, { replace: true });
  }

  async function send(items: SheetPage[], decision: Decision, success: string) {
    if (!profileId || !level) return;
    setNotice(null);
    // Each version exactly as the sheet sent it. Pages without one are never sent.
    const body: ApproveRequest = {
      profile_id: profileId,
      level,
      pages: items.flatMap((p) => (p.version ? [{ page_id: p.page_id, version: p.version, decision }] : [])),
    };
    if (!body.pages.length) return;
    const outcome = await action.run('approve', (s) => api.approve(id, body, s));
    setAsking(false);
    if (!outcome) return;

    const sentIds = new Set(body.pages.map((p) => p.page_id));
    if (outcome.ok) {
      setChangedIds((prev) => new Set([...prev].filter((x) => !sentIds.has(x))));
      setLookAgain(null);
      setNotice(success);
    } else {
      const changed = new Set(outcome.conflict.changed.map((c) => c.page_id));
      setChangedIds((prev) => new Set([...[...prev].filter((x) => !sentIds.has(x)), ...changed]));
      setLookAgain({
        numbers: pages.filter((p) => changed.has(p.page_id)).map((p) => p.number),
        recorded: outcome.conflict.recorded.length,
      });
    }
    setStaleSheet(sheet.data ?? null);
    reload();
  }

  const who = profile ? `${profile.name} · ${level ? levelName(level) : ''}` : '';

  return (
    <>
      <PageHeader
        title={book.data ? `Contact sheet · ${book.data.title}` : 'Contact sheet'}
        back={
          <Link to={`/books/${encodeURIComponent(id)}/subjects`} className="font-semibold text-sky-800 underline">
            ← Subject review
          </Link>
        }
      >
        {ready && counts.approved > 0 && (
          <Link
            to={`/read/${encodeURIComponent(id)}?profile=${encodeURIComponent(profileId)}&level=${level}`}
            className="inline-flex min-h-11 items-center rounded-lg px-4 font-semibold text-sky-800 ring-1 ring-inset ring-slate-300 hover:bg-slate-100"
          >
            Read with {who}
          </Link>
        )}
      </PageHeader>
      {book.status === 'error' && <ErrorPanel error={book.error} onRetry={book.reload} title="Could not load this book" />}
      {profiles.status === 'error' && <ErrorPanel error={profiles.error} onRetry={profiles.reload} title="Could not load profiles" />}

      <div className="mb-5 flex flex-wrap items-end gap-4">
        <label className="flex flex-col gap-1 font-semibold">
          Child
          <select
            className="min-h-11 min-w-48 rounded-lg border border-slate-300 bg-white px-3 font-normal"
            value={profileId ?? ''}
            onChange={(e) => update('profile', e.target.value)}
          >
            <option value="">Choose a child…</option>
            {profiles.data?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({levelName(p.level)})
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 font-semibold">
          Look
          <select
            className="min-h-11 min-w-48 rounded-lg border border-slate-300 bg-white px-3 font-normal"
            value={level ?? ''}
            onChange={(e) => update('level', e.target.value)}
          >
            <option value="">Choose a look…</option>
            {LEVELS.map((l) => (
              <option key={l.value} value={l.value}>
                {l.name}
              </option>
            ))}
          </select>
        </label>
        {profiles.data && profiles.data.length === 0 && (
          <p className="text-slate-700">
            No child profiles yet.{' '}
            <Link to="/profiles" className="font-semibold text-sky-800 underline">
              Create one
            </Link>
            .
          </p>
        )}
      </div>

      {!ready && <p className="text-slate-700">Choose a child and a look to see this book’s contact sheet.</p>}
      {ready && sheet.status === 'loading' && <Loading label="Loading contact sheet…" />}
      {ready && sheet.status === 'error' && (
        <ErrorPanel error={sheet.error} onRetry={reload} title="Could not load the contact sheet" />
      )}

      {ready && sheet.data && level && (
        <>
          <div className="mb-5 space-y-2 rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-lg">
                <strong>{counts.approved}</strong> approved · <strong>{counts.rejected}</strong> rejected ·{' '}
                <strong>{counts.open}</strong> to review
                {counts.notReady > 0 && <> · {counts.notReady} not ready</>}
                {counts.omitted > 0 && <> · {counts.omitted} left out</>}
              </p>
              <Button
                variant="primary"
                disabled={toApprove.length === 0 || deciding}
                onClick={() => {
                  setNotice(null);
                  setAsking(true);
                }}
              >
                Approve sheet…
              </Button>
            </div>
            <p className="text-slate-700">
              Each preview is the exact version {profile?.name ?? 'this child'} would see in {levelName(level)}. The checks are
              automatic measurements; they do not replace your review. Approving records this exact version: if the subject,
              the colors or the display change later, the page needs approval again.
            </p>
            {pending && (
              <p role="status" className="text-sm text-slate-600">
                A second look is still running; this sheet updates every few seconds.
              </p>
            )}
            {sheet.refreshing && <p className="text-sm text-slate-600">Refreshing…</p>}
          </div>

          {lookAgain && (
            <div role="alert" className="mb-5 rounded-xl bg-amber-50 p-4 text-amber-950 ring-2 ring-amber-400">
              <h2 className="text-lg font-bold">Look again</h2>
              <p className="mt-1">
                {lookAgain.numbers.length === 1 ? `Page ${lookAgain.numbers[0]} changed` : `Pages ${lookAgain.numbers.join(', ')} changed`}{' '}
                since this sheet was loaded, so {lookAgain.numbers.length === 1 ? 'it was' : 'they were'} not approved. The new
                version is shown below, marked “Changed”. Look at it and decide again.
                {lookAgain.recorded > 0 && ` Your other ${lookAgain.recorded} ${lookAgain.recorded === 1 ? 'decision was' : 'decisions were'} saved.`}
              </p>
            </div>
          )}

          {asking && (
            <div role="dialog" aria-modal="false" aria-labelledby="approve-h" className="mb-5 rounded-xl bg-sky-50 p-4 ring-1 ring-sky-300">
              <h2 id="approve-h" className="text-lg font-bold">
                Approve {toApprove.length} {toApprove.length === 1 ? 'page' : 'pages'} for {who}?
              </h2>
              <p className="mt-1">
                {toApprove.length === 1 ? 'Page' : 'Pages'} {toApprove.map((p) => p.number).join(', ')}, exactly as shown. Pages you
                rejected, pages not ready, and pages left out are not changed.
              </p>
              {flagged.length > 0 && (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-amber-950">
                  {flagged.map((p) => (
                    <li key={p.page_id}>
                      Page {p.number}:{' '}
                      {problems(p.checks)
                        .map(({ key, item }) => `${CHECK_LABEL[key]} ${item.status === 'fail' ? 'failed' : 'warning'}`)
                        .join(', ')}
                    </li>
                  ))}
                </ul>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                <Button
                  variant="primary"
                  disabled={action.pending !== null}
                  onClick={() =>
                    void send(toApprove, 'approve', `Approved ${toApprove.length} ${toApprove.length === 1 ? 'page' : 'pages'} for ${who}.`)
                  }
                >
                  {action.pending ? 'Approving…' : `Approve ${toApprove.length}`}
                </Button>
                <Button disabled={action.pending !== null} onClick={() => setAsking(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {action.error && (
            <p role="alert" className="mb-5 rounded-lg bg-rose-50 p-3 text-rose-900 ring-1 ring-rose-200">
              Nothing was recorded: {errorMessage(action.error)}
            </p>
          )}
          {notice && (
            <p role="status" className="mb-5 rounded-lg bg-emerald-50 p-3 text-emerald-950 ring-1 ring-emerald-200">
              {notice}
            </p>
          )}

          {pages.length === 0 ? (
            <p className="text-slate-700">This book has no pages yet.</p>
          ) : (
            <ul className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3" aria-label="Pages">
              {pages.map((p) => (
                <SheetPageCard
                  key={p.page_id}
                  page={p}
                  bookId={id}
                  profileId={profileId}
                  level={level}
                  aspect={aspectOf(p.page_id)}
                  changed={changedIds.has(p.page_id)}
                  busy={deciding}
                  onDecide={(page, decision) =>
                    void send([page], decision, `Page ${page.number} ${decision === 'approve' ? 'approved' : 'rejected'} for ${who}.`)
                  }
                />
              ))}
            </ul>
          )}
          <p className="mt-6 text-sm text-slate-500">Display version {sheet.data.render_version}</p>
        </>
      )}
    </>
  );
}
