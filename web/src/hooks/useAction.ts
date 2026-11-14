import { useCallback, useEffect, useRef, useState } from 'react';
import { isAbortError } from '../api';

export interface ActionState {
  /** Name of the action in flight, or null. One action at a time. */
  pending: string | null;
  error: Error | null;
  clearError: () => void;
  /** Run a mutation; resolves to its result, or undefined if it failed (the error is kept). */
  run: <T>(name: string, fn: (signal: AbortSignal) => Promise<T>) => Promise<T | undefined>;
}

/** Track one mutation at a time for a card or screen, with its error. Cancelled on unmount. */
export function useAction(): ActionState {
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const ctrl = useRef<AbortController | null>(null);
  const busy = useRef(false);

  useEffect(
    () => () => {
      ctrl.current?.abort();
    },
    [],
  );

  const run = useCallback(async <T,>(name: string, fn: (signal: AbortSignal) => Promise<T>) => {
    if (busy.current) return undefined;
    busy.current = true;
    const c = new AbortController();
    ctrl.current = c;
    setPending(name);
    setError(null);
    try {
      return await fn(c.signal);
    } catch (err) {
      if (!c.signal.aborted && !isAbortError(err)) setError(err instanceof Error ? err : new Error(String(err)));
      return undefined;
    } finally {
      busy.current = false;
      if (!c.signal.aborted) setPending(null);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);
  return { pending, error, clearError, run };
}
