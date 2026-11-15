import { api } from '../../api';
import { useImageBlob } from '../../hooks/useImageBlob';
import type { Page } from '../../types/api';
import { errorMessage } from '../ui/LoadState';

/**
 * Original page with the selected subject highlighted (GET /pages/{id}/overlay).
 * Refetches when the subject changes. Pages still processing show a placeholder.
 */
export function OverlayImage({ page, className = '', compact = false }: { page: Page; className?: string; compact?: boolean }) {
  const key = page.state === 'processing' ? null : `${page.id}:${page.subject_hash ?? 'none'}:${page.state}`;
  const img = useImageBlob((signal) => api.getOverlay(page.id, signal), key);
  const alt = `Page ${page.number}${page.selected !== null ? `, subject highlighted` : ''}`;

  return (
    <div className={`flex aspect-[4/3] items-center justify-center overflow-hidden bg-slate-100 ${className}`}>
      {key === null && <span className={compact ? 'sr-only' : 'text-slate-600'}>Processing…</span>}
      {img.status === 'loading' && <span className={compact ? 'sr-only' : 'text-slate-600'}>Loading image…</span>}
      {img.status === 'error' && (
        <span role="alert" className={compact ? 'sr-only' : 'px-3 text-center text-sm text-rose-800'}>
          Image unavailable: {errorMessage(img.error)}
        </span>
      )}
      {img.url && <img src={img.url} alt={alt} className="h-full w-full object-contain" draggable={false} />}
    </div>
  );
}
