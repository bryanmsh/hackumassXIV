import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { ApiError, api, isAbortError } from '../api';
import { CreditsPage } from '../components/reader/CreditsPage';
import { TeacherBar } from '../components/reader/TeacherBar';
import { MockBanner } from '../components/ui/MockBanner';
import { errorMessage } from '../components/ui/LoadState';
import { MOCKS_ENABLED } from '../config';
import { useApi } from '../hooks/useApi';
import { useGestures } from '../hooks/useGestures';
import type { Level, ReaderManifest, ReaderPage as ManifestPage, ReaderVersion } from '../types/api';
import { ReaderImageCache, readerKey } from '../utils/readerCache';
import { type Spot, indexOf, sameSpot, spotAt, step } from '../utils/readerNav';

function parseLevel(raw: string | null): Level | null {
  const n = Number(raw);
  return n === 1 || n === 2 || n === 3 || n === 4 ? n : null;
}

const NEXT_KEYS = new Set(['ArrowRight', ' ', 'PageDown']);
const PREV_KEYS = new Set(['ArrowLeft', 'PageUp']);

/** Keys typed into a control in the teacher bar belong to that control. */
function fromControl(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && target.closest('button, a, input, select, textarea, [contenteditable="true"]') !== null;
}

/**
 * Reader: full screen, one approved page at a time, no visible controls.
 *
 * Safety rules this screen keeps:
 * - Pages come only from GET /reader/{book} (the manifest) and image bytes only
 *   from GET /reader/page/{id}?v= with the manifest's own token. Never /render
 *   or /preview, never the original page as a substitute.
 * - A refused image (403) shows no picture, only a message for the teacher.
 * - Single taps and clicks do nothing. Pages turn with → / Space / PageDown and
 *   ← / PageUp (keyboard or clicker). T, or a 1-second press in a corner,
 *   opens the teacher bar. Two-finger gestures are off: they were not tested
 *   on the demo tablet, and the team chose the plan's fallback (2026-11-14).
 * - No timers that move pages, no transitions; a new page replaces the old
 *   one only when it is ready.
 */
export function ReaderPage() {
  const { bookId = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const profileId = params.get('profile');
  const level = parseLevel(params.get('level'));

  const switchTo = useCallback(
    (v: ReaderVersion) => {
      const next = new URLSearchParams(params);
      next.set('profile', v.profile_id);
      next.set('level', String(v.level));
      setParams(next, { replace: true });
    },
    [params, setParams],
  );

  if (!profileId || !level) {
    return (
      <Notice bookId={bookId}>
        <p>Choose a child and an approved look from the contact sheet to start reading.</p>
      </Notice>
    );
  }
  return <Reader key={bookId} bookId={bookId} profileId={profileId} level={level} onSwitch={switchTo} />;
}

function Reader({
  bookId,
  profileId,
  level,
  onSwitch,
}: {
  bookId: string;
  profileId: string;
  level: Level;
  onSwitch: (v: ReaderVersion) => void;
}) {
  const cache = useMemo(() => new ReaderImageCache(), []);
  useEffect(() => () => cache.clear(), [cache]);

  // The manifest for the chosen child and look. While a switch loads, the
  // previous manifest stays in `data`; everything below reads profile, level
  // and tokens from the manifest itself, so the two are never mixed.
  const current = useApi(
    (signal) => api.getReaderManifest(bookId, { profile: profileId, level }, signal),
    `${bookId}|${profileId}|${level}`,
  );
  const manifest = current.data;
  const profiles = useApi((signal) => api.listProfiles(signal), 'reader-profiles');
  const background = profiles.data?.find((p) => p.id === manifest?.profile_id)?.settings.background ?? '#000000';

  const [spot, setSpot] = useState<Spot | null>(null);
  const [shown, setShown] = useState<{ key: string; url: string; number: number } | 'credits' | null>(null);
  const [imageError, setImageError] = useState<Error | null>(null);
  const [barOpen, setBarOpen] = useState(false);
  const [others, setOthers] = useState<Record<string, ReaderManifest>>({});
  const [fsActive, setFsActive] = useState(false);

  // Start on the first approved page; after a version switch, stay on the same
  // page if this version has it, else the next approved one.
  const index = manifest && spot ? indexOf(manifest, spot) : 0;
  const normalized = manifest ? spotAt(manifest, index) : null;
  useEffect(() => {
    if (manifest && manifest.pages.length > 0 && !sameSpot(spot, normalized)) setSpot(normalized);
  }, [manifest, spot, normalized]);

  const target: ManifestPage | 'credits' | null = manifest && spot ? (manifest.pages[index] ?? 'credits') : null;
  const targetKey =
    manifest && target && target !== 'credits'
      ? readerKey({ profileId: manifest.profile_id, level: manifest.level, pageId: target.page_id, v: target.v })
      : null;

  const loadImage = useCallback(
    (m: ReaderManifest, p: ManifestPage) => () => api.getReaderPage(p.page_id, { profile: m.profile_id, level: m.level, v: p.v }),
    [],
  );

  // Show the target page once its image is ready (from the cache if prefetched).
  useEffect(() => {
    if (!manifest || !target) return;
    if (target === 'credits') {
      cache.show(null, null);
      setShown('credits');
      setImageError(null);
      return;
    }
    let live = true;
    const key = targetKey!;
    cache
      .get(key, loadImage(manifest, target))
      .then((url) => {
        if (!live) return;
        cache.show(key, url);
        setShown({ key, url, number: target.number });
        setImageError(null);
      })
      .catch((err: unknown) => {
        if (!live || isAbortError(err)) return;
        // Refused or failed: show NO picture, never an older or original one.
        cache.show(null, null);
        setShown(null);
        setImageError(err instanceof Error ? err : new Error(String(err)));
      });
    return () => {
      live = false;
    };
    // targetKey captures the manifest's profile, level, page and token, so it is the whole identity.
  }, [targetKey, target === 'credits', manifest?.book_id]);

  // Manifests of the other fully approved versions, for fast switching.
  const versionsKey = manifest ? JSON.stringify(manifest.versions) + manifest.profile_id + manifest.level : '';
  const [recheck, setRecheck] = useState(0);
  useEffect(() => {
    if (!manifest) return;
    const ctrl = new AbortController();
    const wanted = manifest.versions.filter((v) => v.fully_approved && !(v.profile_id === manifest.profile_id && v.level === manifest.level));
    for (const v of wanted) {
      api
        .getReaderManifest(bookId, { profile: v.profile_id, level: v.level }, ctrl.signal)
        .then((m) => setOthers((o) => ({ ...o, [`${v.profile_id}|${v.level}`]: m })))
        .catch(() => undefined);
    }
    return () => ctrl.abort();
    // versionsKey stands for the manifest's version list; recheck forces a refetch.
  }, [versionsKey, recheck, bookId]);

  // Prefetch: the next page in this version, and this page in every other approved version.
  useEffect(() => {
    if (!manifest || !shown || shown === 'credits' || imageError) return;
    const next = manifest.pages[index + 1];
    if (next) cache.prefetch(readerKey({ profileId: manifest.profile_id, level: manifest.level, pageId: next.page_id, v: next.v }), loadImage(manifest, next));
    const here = manifest.pages[index];
    if (!here) return;
    for (const m of Object.values(others)) {
      if (m.profile_id === manifest.profile_id && m.level === manifest.level) continue;
      const same = m.pages.find((p) => p.page_id === here.page_id);
      if (same) cache.prefetch(readerKey({ profileId: m.profile_id, level: m.level, pageId: same.page_id, v: same.v }), loadImage(m, same));
    }
  }, [shown, manifest, index, others, imageError, cache, loadImage]);

  const go = useCallback(
    (delta: 1 | -1) => {
      if (!manifest || !spot) return;
      setSpot(step(manifest, spot, delta));
    },
    [manifest, spot],
  );

  /** Ask the server again whether what we show is still approved. */
  const { reload } = current;
  const revalidate = useCallback(() => {
    reload();
    setRecheck((n) => n + 1);
  }, [reload]);

  const openBar = useCallback(() => {
    setBarOpen(true);
    revalidate();
  }, [revalidate]);

  // Keyboard and clickers. Held keys (repeat) are ignored; nothing moves on its own.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === 't' || e.key === 'T') {
        e.preventDefault();
        if (e.repeat) return;
        if (barOpen) setBarOpen(false);
        else openBar();
        return;
      }
      if (e.key === 'Escape') {
        setBarOpen(false);
        return;
      }
      if (fromControl(e.target)) return;
      const delta = NEXT_KEYS.has(e.key) ? 1 : PREV_KEYS.has(e.key) ? -1 : 0;
      if (!delta) return;
      e.preventDefault();
      if (e.repeat) return;
      go(delta);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go, barOpen, openBar]);

  // Touch: only a 1-second press in a corner does anything (opens the teacher bar).
  const gestures = useGestures((g) => {
    if (g.type === 'corner-long-press') openBar();
  });

  // Full screen (the teacher bar has the button; browsers require a user action).
  useEffect(() => {
    const onFs = () => setFsActive(Boolean(document.fullscreenElement));
    document.addEventListener('fullscreenchange', onFs);
    return () => document.removeEventListener('fullscreenchange', onFs);
  }, []);
  const root = typeof document !== 'undefined' ? (document.documentElement as HTMLElement & { webkitRequestFullscreen?: () => void }) : null;
  const fsSupported = Boolean(root && (root.requestFullscreen || root.webkitRequestFullscreen));
  const toggleFs = () => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else if (root?.requestFullscreen) void root.requestFullscreen().catch(() => undefined);
    else root?.webkitRequestFullscreen?.();
  };

  const surface = useRef<HTMLDivElement>(null);
  const total = manifest?.pages.length ?? 0;
  const position = target === 'credits' ? 'Credits' : target ? `Page ${target.number} · ${index + 1} of ${total}` : '';

  // ---------- Teacher-directed states (never a page image) ----------
  if (current.status === 'error' && !manifest) {
    const notFound = current.error instanceof ApiError && current.error.status === 404;
    return (
      <Notice bookId={bookId}>
        <p role="alert">{notFound ? 'This book or child was not found.' : `The reader could not load: ${errorMessage(current.error)}`}</p>
        {!notFound && (
          <button type="button" className="font-semibold underline" onClick={current.reload}>
            Try again
          </button>
        )}
      </Notice>
    );
  }
  if (manifest && manifest.pages.length === 0) {
    return (
      <Notice bookId={bookId} profileId={manifest.profile_id} level={manifest.level}>
        <p role="alert">No pages are approved for this child and look yet. Approve them on the contact sheet first.</p>
      </Notice>
    );
  }

  return (
    <div className="fixed inset-0 overflow-hidden" style={{ backgroundColor: background }}>
      {MOCKS_ENABLED && <MockBanner compact />}
      <div
        ref={surface}
        {...gestures.handlers}
        data-testid="reader-surface"
        className={`absolute inset-0 ${gestures.className}`}
        style={{ WebkitTouchCallout: 'none', WebkitUserSelect: 'none' }}
      >
        {shown === 'credits' && manifest && <CreditsPage manifest={manifest} background={background} />}
        {shown && shown !== 'credits' && (
          <img
            src={shown.url}
            alt={`Page ${shown.number}`}
            className="pointer-events-none h-full w-full object-contain"
            draggable={false}
          />
        )}
        {imageError && (
          <div role="alert" className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-black p-8 text-center text-xl text-white">
            <p>
              {imageError instanceof ApiError && imageError.status === 403
                ? 'This page is not approved for this child and look any more, so nothing is shown.'
                : `This page could not be shown: ${errorMessage(imageError)}`}
            </p>
            <p className="text-base text-slate-300">Press T (or hold a corner) for the teacher bar, or check the contact sheet.</p>
            <Link
              to={`/books/${encodeURIComponent(bookId)}/approve?profile=${encodeURIComponent(manifest?.profile_id ?? profileId)}&level=${manifest?.level ?? level}`}
              className="font-semibold underline"
            >
              Leave the reader and open the contact sheet
            </Link>
          </div>
        )}
      </div>

      {barOpen && manifest && (
        <TeacherBar
          manifest={manifest}
          position={position}
          canPrev={index > 0}
          canNext={target !== 'credits'}
          onPrev={() => go(-1)}
          onNext={() => go(1)}
          onSwitch={(v) => {
            setBarOpen(false);
            onSwitch(v);
          }}
          onClose={() => setBarOpen(false)}
          fullscreen={{ supported: fsSupported, active: fsActive, toggle: toggleFs }}
          checking={current.refreshing}
          checkError={current.status === 'error' ? errorMessage(current.error) : null}
        />
      )}
    </div>
  );
}

function Notice({ bookId, profileId, level, children }: { bookId: string; profileId?: string; level?: number; children: React.ReactNode }) {
  const q = profileId && level ? `?profile=${encodeURIComponent(profileId)}&level=${level}` : '';
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black p-8 text-center text-white">
      {MOCKS_ENABLED && <MockBanner compact />}
      <div className="max-w-xl space-y-4 text-xl">
        {children}
        <Link to={`/books/${encodeURIComponent(bookId)}/approve${q}`} className="inline-block font-semibold underline">
          Leave the reader and go to the contact sheet
        </Link>
      </div>
    </div>
  );
}
