import type { CheckItem, CheckResult, CheckStatus, SecondLook } from '../../types/api';
import { CHECK_TONE } from '../../utils/display';
import { secondLookText } from '../../utils/secondLook';

export const CHECK_LABEL: Record<keyof CheckResult, string> = {
  fidelity: 'Cut-out',
  page_edge: 'Page edge',
  background: 'Background',
  contrast: 'Contrast',
  size: 'Size',
  text_contrast: 'Text contrast',
};

const STATUS_TEXT: Record<CheckStatus, string> = { pass: 'Pass', warn: 'Warning', fail: 'Failed' };
const ORDER: (keyof CheckResult)[] = ['fidelity', 'page_edge', 'background', 'contrast', 'size', 'text_contrast'];

/** Checks that did not pass, in display order. Never hidden: warnings and failures are listed first. */
export function problems(checks: CheckResult | null): { key: keyof CheckResult; item: CheckItem }[] {
  if (!checks) return [];
  return ORDER.flatMap((key) => {
    const item = checks[key];
    return item && item.status !== 'pass' ? [{ key, item }] : [];
  });
}

/**
 * The automatic checks for one page version. They are measurements, not
 * approval: every warning and failure is shown, and the teacher still decides.
 */
export function ChecksList({ checks, level }: { checks: CheckResult | null; level: number }) {
  if (!checks) return <p className="text-sm text-slate-600">No checks yet.</p>;
  const rows = ORDER.flatMap((key): { key: keyof CheckResult; item: CheckItem | null }[] => {
    const item = checks[key];
    if (item) return [{ key, item }];
    // Background is not checked at Outlined; say so rather than hide the row.
    if (key === 'background' && level === 4) return [{ key, item: null }];
    return [];
  });
  // Problems first, so nothing that needs attention is below the fold.
  rows.sort((a, b) => rank(a.item) - rank(b.item));

  return (
    <ul className="space-y-1.5" aria-label="Checks">
      {rows.map(({ key, item }) => (
        <li key={key} className="flex items-start gap-2 text-sm">
          {item ? (
            <span className={`inline-flex shrink-0 rounded-full px-2 py-0.5 text-xs font-bold ring-1 ring-inset ${CHECK_TONE[item.status]}`}>
              {STATUS_TEXT[item.status]}
            </span>
          ) : (
            <span className="inline-flex shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-bold text-slate-600 ring-1 ring-inset ring-slate-300">
              Not checked
            </span>
          )}
          <span>
            <span className="font-semibold">{CHECK_LABEL[key]}:</span> {item ? item.detail : 'Not checked for Outlined.'}
          </span>
        </li>
      ))}
    </ul>
  );
}

function rank(item: CheckItem | null): number {
  if (!item) return 3;
  return item.status === 'fail' ? 0 : item.status === 'warn' ? 1 : 2;
}

/** The AI's second look: a weak signal, never proof and never a blocker. */
export function SecondLookLine({ look }: { look: SecondLook | null }) {
  if (!look) return null;
  return (
    <p className={`text-sm ${look.status === 'warn' ? 'text-amber-900' : 'text-slate-700'}`}>
      <span className="font-semibold">Second look (AI):</span> {secondLookText(look)}
    </p>
  );
}
