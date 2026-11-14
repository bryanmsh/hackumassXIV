import { ApiError } from '../../api';
import { Button } from './Button';

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-3 py-10 text-slate-600">
      <span className="size-5 animate-spin rounded-full border-2 border-slate-300 border-t-sky-700" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message || 'Something went wrong.';
  return 'Something went wrong.';
}

export function ErrorPanel({ error, onRetry, title = 'Could not load this' }: { error: unknown; onRetry?: () => void; title?: string }) {
  const status = error instanceof ApiError && error.status ? ` (HTTP ${error.status})` : '';
  return (
    <div role="alert" className="my-6 rounded-xl bg-rose-50 p-5 ring-1 ring-rose-200">
      <p className="font-semibold text-rose-900">
        {title}
        {status}
      </p>
      <p className="mt-1 text-rose-900">{errorMessage(error)}</p>
      {onRetry && (
        <Button className="mt-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-8 text-center">
      <p className="text-lg font-semibold">{title}</p>
      {children && <div className="mt-2 text-slate-600">{children}</div>}
    </div>
  );
}
