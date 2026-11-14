import { Link } from 'react-router';
import { api } from '../../api';
import { useImageBlob } from '../../hooks/useImageBlob';
import type { Decision, Level, SheetPage } from '../../types/api';
import { levelName, sourceLabel } from '../../utils/display';
import { Button } from '../ui/Button';
import { errorMessage } from '../ui/LoadState';
import { Badge } from '../ui/StatusBadge';
import { ChecksList, SecondLookLine } from './ChecksList';

const APPROVAL_BADGE = {
  approved: <Badge tone="bg-emerald-700 text-white ring-emerald-800">Approved</Badge>,
  rejected: <Badge tone="bg-rose-700 text-white ring-rose-800">Rejected</Badge>,
  none: <Badge tone="bg-slate-100 text-slate-700 ring-slate-300">Not approved</Badge>,
};

/** Why a page has no version to approve, and where to fix it. */
function notReadyText(p: SheetPage): string {
  if (p.omitted) return 'Left out. It is skipped in the reader.';
  if (p.state === 'processing') return 'Still processing.';
  if (!p.confirmed) return 'Confirm a subject in Subject review first.';
  return 'Not ready to approve.';
}

/**
 * One page of the contact sheet: the exact saved version for this child and
 * look (GET /render with the sheet's own `version`, teacher screens only), its
 * checks and second look, and Approve / Reject for that exact version.
 */
export function SheetPageCard({
  page,
  bookId,
  profileId,
  level,
  aspect,
  changed,
  busy,
  onDecide,
}: {
  page: SheetPage;
  bookId: string;
  profileId: string;
  level: Level;
  /** Page width / height, so the preview keeps the page's shape. */
  aspect: string;
  /** This page changed after the teacher last saw it (a 409). */
  changed: boolean;
  busy: boolean;
  onDecide: (page: SheetPage, decision: Decision) => void;
}) {
  const version = page.version;
  const img = useImageBlob(
    (signal) => api.getRender(page.page_id, { profile: profileId, level, v: version ?? '' }, signal),
    version ? `${page.page_id}:${profileId}:${level}:${version}` : null,
  );

  return (
    <li
      className={`flex flex-col overflow-hidden rounded-xl bg-white shadow-sm ring-1 ${
        changed ? 'ring-4 ring-amber-400' : page.approval === 'rejected' ? 'ring-rose-200' : 'ring-slate-200'
      }`}
    >
      <div className="relative bg-slate-900" style={{ aspectRatio: aspect }}>
        {img.url && (
          <img
            src={img.url}
            alt={`Page ${page.number} in ${levelName(level)}${page.label ? `, ${page.label}` : ''}`}
            className="absolute inset-0 h-full w-full object-contain"
            draggable={false}
          />
        )}
        {!version && <Placeholder>{notReadyText(page)}</Placeholder>}
        {img.status === 'loading' && <Placeholder>Loading preview…</Placeholder>}
        {img.status === 'error' && (
          <Placeholder>
            <span role="alert">Preview unavailable: {errorMessage(img.error)}</span>
          </Placeholder>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-lg font-bold">Page {page.number}</h3>
          {version ? APPROVAL_BADGE[page.approval] : page.omitted ? <Badge tone="bg-slate-700 text-white ring-slate-800">Left out</Badge> : null}
          {changed && <Badge tone="bg-amber-300 text-amber-950 ring-amber-500">Changed: look again</Badge>}
        </div>
        {page.label && (
          <p>
            <span className="font-semibold">{page.label}</span>
            {page.source && page.source !== 'auto' && <span className="text-slate-600"> · {sourceLabel(page.source)}</span>}
          </p>
        )}

        {version ? (
          <>
            <ChecksList checks={page.checks} level={level} />
            <SecondLookLine look={page.second_look} />
          </>
        ) : (
          !page.omitted && (
            <Link
              to={`/books/${encodeURIComponent(bookId)}/subjects`}
              className="inline-flex min-h-11 items-center font-semibold text-sky-800 underline"
            >
              Go to Subject review
            </Link>
          )
        )}

        {version && (
          <div className="mt-auto flex flex-wrap gap-2 pt-1">
            {page.approval !== 'approved' && (
              <Button variant={page.approval === 'none' ? 'secondary' : 'primary'} disabled={busy} onClick={() => onDecide(page, 'approve')}>
                {page.approval === 'rejected' ? 'Approve instead' : 'Approve page'}
              </Button>
            )}
            {page.approval !== 'rejected' && (
              <Button variant="danger" disabled={busy} onClick={() => onDecide(page, 'reject')}>
                {page.approval === 'approved' ? 'Reject instead' : 'Reject page'}
              </Button>
            )}
          </div>
        )}
      </div>
    </li>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return <div className="absolute inset-0 flex items-center justify-center p-4 text-center text-slate-200">{children}</div>;
}
