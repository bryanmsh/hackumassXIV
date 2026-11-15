import { MAX_UPLOAD_BYTES } from '../api';
import type { Credits } from '../types/api';

export const CREDIT_FIELDS: readonly { key: keyof Credits; label: string; hint?: string }[] = [
  { key: 'author', label: 'Author' },
  { key: 'illustrator', label: 'Illustrator' },
  { key: 'publisher', label: 'Publisher' },
  { key: 'source', label: 'Source', hint: 'Where the book came from, such as a web address.' },
  { key: 'license', label: 'License', hint: 'For example, CC BY 4.0.' },
];

export function isPdf(file: File): boolean {
  return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
}

export function formatMegabytes(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return `${mb < 10 ? mb.toFixed(1) : Math.round(mb)} MB`;
}

/**
 * What the browser can check before sending: the file type and size. The page
 * count (30 at most) is only known once the server reads the PDF, so it is
 * never claimed here.
 */
export function validatePdf(file: File | null): string | null {
  if (!file) return 'Choose a PDF file.';
  if (!isPdf(file)) return `“${file.name}” is not a PDF. Choose a PDF file.`;
  if (file.size === 0) return `“${file.name}” is empty.`;
  if (file.size > MAX_UPLOAD_BYTES) {
    return `“${file.name}” is ${formatMegabytes(file.size)}. Miraai accepts PDFs up to 50 MB.`;
  }
  return null;
}

export type CreditsDraft = Record<keyof Credits, string>;

export const EMPTY_CREDITS: CreditsDraft = { author: '', illustrator: '', publisher: '', source: '', license: '' };

/** All five keys, trimmed, empty as null; undefined when nothing was typed (credits are optional). */
export function creditsFromDraft(draft: CreditsDraft): Credits | undefined {
  const credits: Credits = { author: null, illustrator: null, publisher: null, source: null, license: null };
  let any = false;
  for (const { key } of CREDIT_FIELDS) {
    const v = draft[key].trim();
    if (v) {
      credits[key] = v;
      any = true;
    }
  }
  return any ? credits : undefined;
}
