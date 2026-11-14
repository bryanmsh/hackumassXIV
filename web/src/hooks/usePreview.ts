import { useCallback, useEffect, useRef, useState } from 'react';
import { api, isAbortError } from '../api';
import type { PreviewInput } from '../types/api';

/** The spec: the live preview asks the server at most once every 300 ms. */
export const PREVIEW_INTERVAL_MS = 300;

export interface PreviewState {
  /** Object URL of the newest preview received (may be for older settings; see `current`). */
  url: string | null;
  /** True when `url` shows exactly the settings asked for now. */
  current: boolean;
  status: 'idle' | 'loading' | 'loaded' | 'error';
  error: Error | null;
  retry: () => void;
}

/**
 * Preview UNSAVED settings with POST /preview. Nothing is stored on the server.
 *
 * - Throttled: at most one request per `intervalMs`; the latest settings are
 *   always sent last (trailing call), so the preview ends on what is chosen.
 * - Stale answers are cancelled and ignored: only the newest request can
 *   update the image.
 * - The previous image stays up (marked not current) while a new one loads.
 * - Object URLs are revoked when replaced and on unmount.
 */
export function usePreview(input: PreviewInput | null, intervalMs = PREVIEW_INTERVAL_MS): PreviewState {
  const key = input ? JSON.stringify(input) : null;
  const [shown, setShown] = useState<{ url: string; key: string } | null>(null);
  const [status, setStatus] = useState<PreviewState['status']>('idle');
  const [error, setError] = useState<Error | null>(null);
  const [nonce, setNonce] = useState(0);
  const lastStart = useRef(Number.NEGATIVE_INFINITY);
  const urlRef = useRef<string | null>(null);

  useEffect(() => {
    if (key === null) {
      setStatus('idle');
      return;
    }
    const ctrl = new AbortController();
    const body = JSON.parse(key) as PreviewInput;
    setStatus('loading');
    setError(null);
    const wait = Math.max(0, lastStart.current + intervalMs - Date.now());
    const timer = setTimeout(() => {
      lastStart.current = Date.now();
      api
        .preview(body, ctrl.signal)
        .then((blob) => {
          if (ctrl.signal.aborted) return;
          const url = URL.createObjectURL(blob);
          if (urlRef.current) URL.revokeObjectURL(urlRef.current);
          urlRef.current = url;
          setShown({ url, key });
          setStatus('loaded');
        })
        .catch((err: unknown) => {
          if (ctrl.signal.aborted || isAbortError(err)) return;
          setError(err instanceof Error ? err : new Error(String(err)));
          setStatus('error');
        });
    }, wait);
    // New settings (or unmount): the pending or in-flight request is stale.
    return () => {
      clearTimeout(timer);
      ctrl.abort();
    };
  }, [key, nonce, intervalMs]);

  useEffect(
    () => () => {
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    },
    [],
  );

  const retry = useCallback(() => setNonce((n) => n + 1), []);
  return { url: shown?.url ?? null, current: shown !== null && shown.key === key, status, error, retry };
}
