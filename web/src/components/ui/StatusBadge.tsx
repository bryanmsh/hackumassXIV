import type { PageState } from '../../types/api';
import { PAGE_STATE_LABEL, PAGE_STATE_TONE } from '../../utils/display';

export function Badge({ tone, children }: { tone: string; children: React.ReactNode }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-sm font-semibold ring-1 ring-inset ${tone}`}>
      {children}
    </span>
  );
}

export function PageStateBadge({ state }: { state: PageState }) {
  return <Badge tone={PAGE_STATE_TONE[state]}>{PAGE_STATE_LABEL[state]}</Badge>;
}
