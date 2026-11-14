import { useEffect, useRef, useState } from 'react';
import { ApiError, isAbortError } from '../api';

export interface ImageBlobState {
  url: string | null;
  status: 'idle' | 'loading' | 'loaded' | 'error';
  error: ApiError | Error | null;
}

/**
 * Fetch an image through api.ts as a Blob and expose an object URL.
 * Refetches when `key` changes (e.g. a new subject_hash); revokes object URLs
 * on change and unmount. Pass key = null to show nothing.
 */
export function useImageBlob(load: (signal: AbortSignal) => Promise<Blob>, key: string | null): ImageBlobState {
  const loadRef = useRef(load);
  loadRef.current = load;
  const [state, setState] = useState<ImageBlobState>({ url: null, status: key ? 'loading' : 'idle', error: null });

  useEffect(() => {
    if (key === null) {
      setState({ url: null, status: 'idle', error: null });
      return;
    }
    const ctrl = new AbortController();
    let objectUrl: string | null = null;
    setState({ url: null, status: 'loading', error: null });
    loadRef
      .current(ctrl.signal)
      .then((blob) => {
        if (ctrl.signal.aborted) return;
        objectUrl = URL.createObjectURL(blob);
        setState({ url: objectUrl, status: 'loaded', error: null });
      })
      .catch((err: unknown) => {
        if (ctrl.signal.aborted || isAbortError(err)) return;
        setState({ url: null, status: 'error', error: err instanceof Error ? err : new Error(String(err)) });
      });
    return () => {
      ctrl.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [key]);

  return state;
}
