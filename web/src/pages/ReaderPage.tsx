import { Link, useParams, useSearchParams } from 'react-router';
import { ApiError, api } from '../api';
import { MockBanner } from '../components/ui/MockBanner';
import { errorMessage } from '../components/ui/LoadState';
import { MOCKS_ENABLED } from '../config';
import { useApi } from '../hooks/useApi';
import type { Level } from '../types/api';

function parseLevel(raw: string | null): Level | null {
  const n = Number(raw);
  return n === 1 || n === 2 || n === 3 || n === 4 ? n : null;
}

/**
 * D1 shell. Loads only the authorized manifest (GET /reader/{book_id}): 200
 * with only approved pages (the rest in `skipped`), 404 for an unknown book or
 * child. It deliberately shows NO page images yet: image display, input,
 * teacher bar, prefetch and credits arrive in D6, using only /reader/page,
 * where every refusal is 403 {"detail": "not approved"}.
 */
export function ReaderPage() {
  const { bookId = '' } = useParams();
  const [params] = useSearchParams();
  const profile = params.get('profile');
  const level = parseLevel(params.get('level'));
  const manifest = useApi(
    (signal) => (profile && level ? api.getReaderManifest(bookId, { profile, level }, signal) : Promise.resolve(null)),
    `${bookId}:${profile ?? ''}:${level ?? ''}`,
  );
  const approveLink = `/books/${encodeURIComponent(bookId)}/approve`;

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black p-8 text-center text-white">
      {MOCKS_ENABLED && <MockBanner compact />}
      <div className="max-w-xl space-y-4">
        {(!profile || !level) && <p>Choose a child and an approved look from the contact sheet to start reading.</p>}
        {manifest.status === 'loading' && profile && level && <p>Loading…</p>}
        {manifest.status === 'error' && (
          <p role="alert">
            {manifest.error instanceof ApiError && manifest.error.status === 404
              ? 'This book or child was not found.'
              : errorMessage(manifest.error)}
          </p>
        )}
        {manifest.data && manifest.data.pages.length === 0 && (
          <p role="alert">No pages are approved for this child and look yet. Approve them on the contact sheet first.</p>
        )}
        {manifest.data && manifest.data.pages.length > 0 && (
          <p>
            {manifest.data.pages.length} approved pages ready. The reader view is not built yet (D6).
          </p>
        )}
        <Link to={approveLink} className="inline-block font-semibold underline">
          Leave the reader and go to contact sheets
        </Link>
      </div>
    </div>
  );
}
