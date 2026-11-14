import type { SecondLook } from '../types/api';

/**
 * A server reason that is fit to show a teacher: one short plain sentence.
 * Raw exceptions (JSON, status codes, very long strings) are not.
 */
export function plainReason(detail: string | null | undefined): string | null {
  const d = detail?.trim();
  if (!d) return null;
  if (d.length > 140 || /[{}[\]]|Error:|Traceback|DEADLINE|\b\d{3}\b/.test(d)) return null;
  return d;
}

/** The AI second look in words for the teacher: a weak signal, never proof and never a blocker. */
export function secondLookText(look: SecondLook): string {
  if (look.status === 'pending') return 'still checking.';
  if (look.status === 'pass') return `named the same subject${look.answer?.trim() ? ` (“${look.answer}”)` : ''}.`;
  const why = plainReason(look.detail);
  if (look.answer?.trim()) return `named “${look.answer}”${why ? ` (${why})` : ''}. It can be wrong too; check the picture.`;
  return why ? `${why} Check the picture yourself.` : 'could not run this time. Check the picture yourself.';
}
