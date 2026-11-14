import { Link, useParams, useSearchParams } from 'react-router';
import { api } from '../api';
import { PageHeader } from '../components/ui/AppShell';
import { ErrorPanel, Loading } from '../components/ui/LoadState';
import { Badge } from '../components/ui/StatusBadge';
import { useApi } from '../hooks/useApi';
import type { Level } from '../types/api';
import { LEVELS, levelName } from '../utils/display';

function parseLevel(raw: string | null): Level | null {
  const n = Number(raw);
  return n === 1 || n === 2 || n === 3 || n === 4 ? n : null;
}

// D1 shell: child + look pickers and the sheet from GET /books/{id}/sheet.
// Previews, checks display, approve/reject and the 409 "look again" flow are D5.
export function ContactSheetPage() {
  const { id = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const profileId = params.get('profile');
  const level = parseLevel(params.get('level'));

  const book = useApi((signal) => api.getBook(id, signal), id);
  const profiles = useApi((signal) => api.listProfiles(signal), 'profiles');
  const ready = Boolean(profileId && level);
  const sheet = useApi(
    (signal) => (profileId && level ? api.getSheet(id, { profile: profileId, level }, signal) : Promise.resolve(null)),
    `${id}:${profileId ?? ''}:${level ?? ''}`,
  );

  const update = (key: 'profile' | 'level', value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  return (
    <>
      <PageHeader
        title={book.data ? `Contact sheet · ${book.data.title}` : 'Contact sheet'}
        back={
          <Link to={`/books/${encodeURIComponent(id)}/subjects`} className="font-semibold text-sky-800 underline">
            ← Subject review
          </Link>
        }
      />
      {book.status === 'error' && <ErrorPanel error={book.error} onRetry={book.reload} title="Could not load this book" />}
      {profiles.status === 'error' && <ErrorPanel error={profiles.error} onRetry={profiles.reload} title="Could not load profiles" />}

      <div className="mb-6 flex flex-wrap gap-4">
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
                {p.name}
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
      </div>

      {!ready && <p className="text-slate-700">Choose a child and a look to see this book’s contact sheet.</p>}
      {ready && sheet.status === 'loading' && <Loading label="Loading contact sheet…" />}
      {ready && sheet.status === 'error' && <ErrorPanel error={sheet.error} onRetry={sheet.reload} title="Could not load the contact sheet" />}
      {sheet.data && level && (
        <>
          <h2 className="mb-3 text-xl font-bold">{levelName(level)}</h2>
          <ul className="divide-y divide-slate-200 rounded-xl bg-white ring-1 ring-slate-200">
            {sheet.data.pages.map((p) => (
              <li key={p.page_id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                <span className="font-bold">Page {p.number}</span>
                <span>{p.label ?? 'No subject'}</span>
                {p.source === 'manual' && <span className="text-slate-600">outlined by teacher</span>}
                {p.omitted && <Badge tone="bg-slate-700 text-white ring-slate-800">Left out</Badge>}
                {!p.confirmed && !p.omitted && <Badge tone="bg-amber-50 text-amber-900 ring-amber-200">Subject not confirmed</Badge>}
                <span className="ml-auto">
                  {p.approval === 'approved' && <Badge tone="bg-emerald-50 text-emerald-800 ring-emerald-200">Approved</Badge>}
                  {p.approval === 'rejected' && <Badge tone="bg-rose-50 text-rose-800 ring-rose-200">Rejected</Badge>}
                  {p.approval === 'none' && <Badge tone="bg-slate-100 text-slate-700 ring-slate-300">Not reviewed</Badge>}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  );
}
