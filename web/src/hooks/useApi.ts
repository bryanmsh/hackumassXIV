import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, isAbortError } from '../api';

export type LoadStatus = 'loading' | 'success' | 'error';

export interface ApiState<T> {
  status: LoadStatus;
  data: T | undefined;
  error: ApiError | Error | null;
  /** True while a reload runs and older data is still shown. */
  refreshing: boolean;
  reload: () => void;
}

/**
 * Run one API call, cancel it on unmount or when `key` changes, and expose
 * loading / error / retry. Older data stays visible during a reload.
 */
export function useApi<T>(load: (signal: AbortSignal) => Promise<T>, key: string): ApiState<T> {
  const loadRef = useRef(load);
  loadRef.current = load;
  const [nonce, setNonce] = useState(0);
  const [state, setState] = useState<Omit<ApiState<T>, 'reload'>>({
    status: 'loading',
    data: undefined,
    error: null,
    refreshing: false,
  });

  useEffect(() => {
    const ctrl = new AbortController();
    setState((s) => ({ ...s, status: s.data === undefined ? 'loading' : s.status, refreshing: s.data !== undefined }));
    loadRef
      .current(ctrl.signal)
      .then((data) => {
        if (!ctrl.signal.aborted) setState({ status: 'success', data, error: null, refreshing: false });
      })
      .catch((err: unknown) => {
        if (ctrl.signal.aborted || isAbortError(err)) return;
        const error = err instanceof Error ? err : new Error(String(err));
        setState((s) => ({ ...s, status: 'error', error, refreshing: false }));
      });
    return () => ctrl.abort();
  }, [key, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { ...state, reload };
}
