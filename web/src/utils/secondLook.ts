import type { SecondLook } from '../types/api';

/**
 * A server reason that is fit to show a teacher: one short plain sentence.
 * Raw exceptions (JSON, stack-like text, very long strings) are not.
 */
export function plainReason(detail: string | null | undefined): string | null {
  const d = detail?.trim();
  if (!d) return null;
  if (d.length > 140 || /[{}[\]]|Error:|Traceback|DEADLINE|\b\d{3}\b/.test(d)) return null;
  return d;
}

/**
 * The AI second look in words for the teacher. It is a weak signal, never
 * proof and never a blocker. Returns the sentence and, when the server's raw
 * reason was hidden, that reason for a tooltip.
 */
export function secondLookText(look: SecondLook): { text: string; raw: string | null } {
  if (look.status === 'pending') return { text: 'still checking.', raw: null };
  if (look.status === 'pass') return { text: `named the same subject${look.answer?.trim() ? ` (“${look.answer}”)` : ''}.`, raw: null };
  if (look.answer?.trim()) {
    const why = plainReason(look.detail);
    return { text: `named “${look.answer}”${why ? ` (${why})` : ''}. It can be wrong too; check the picture.`, raw: null };
  }
  const why = plainReason(look.detail);
  return {
    text: why ? `${why} Check the picture yourself.` : 'could not run this time. Check the picture yourself.',
    raw: why ? null : (look.detail ?? null),
  };
}
