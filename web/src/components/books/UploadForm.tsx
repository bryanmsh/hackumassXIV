import { useEffect, useId, useRef, useState, type DragEvent, type FormEvent } from 'react';
import { api, isAbortError } from '../../api';
import type { UploadBookResponse } from '../../types/api';
import { CREDIT_FIELDS, EMPTY_CREDITS, creditsFromDraft, formatMegabytes, validatePdf, type CreditsDraft } from '../../utils/upload';
import { Button } from '../ui/Button';
import { errorMessage } from '../ui/LoadState';

const inputClass =
  'mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-base text-slate-900 shadow-sm focus:border-sky-600 focus:outline-none focus:ring-2 focus:ring-sky-600/30';

/**
 * Upload a PDF with its title and credits (POST /books). The browser checks
 * type and size; the server checks everything else, and its answer is shown
 * as it comes back.
 */
export function UploadForm({ onUploaded }: { onUploaded: (res: UploadBookResponse, title: string) => void }) {
  const ids = useId();
  const fileInput = useRef<HTMLInputElement>(null);
  const ctrl = useRef<AbortController | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [credits, setCredits] = useState<CreditsDraft>(EMPTY_CREDITS);
  const [fileError, setFileError] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);

  useEffect(() => () => ctrl.current?.abort(), []);

  function pick(next: File | null) {
    setFile(next);
    setServerError(null);
    setFileError(next ? validatePdf(next) : null);
  }

  function onDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped) pick(dropped);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (uploading) return;
    const problem = validatePdf(file);
    setFileError(problem);
    setServerError(null);
    if (problem || !file) return;

    ctrl.current?.abort();
    const c = new AbortController();
    ctrl.current = c;
    setUploading(true);
    try {
      const res = await api.uploadBook({ file, title: title.trim() || undefined, credits: creditsFromDraft(credits) }, c.signal);
      if (c.signal.aborted) return;
      onUploaded(res, title.trim() || file.name);
      setFile(null);
      setTitle('');
      setCredits(EMPTY_CREDITS);
      if (fileInput.current) fileInput.current.value = '';
    } catch (err) {
      if (isAbortError(err)) return;
      setServerError(errorMessage(err));
    } finally {
      if (ctrl.current === c) setUploading(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate className="rounded-xl bg-white p-5 shadow-sm ring-1 ring-slate-200" aria-labelledby={`${ids}-h`}>
      <h2 id={`${ids}-h`} className="text-xl font-bold">
        Upload a book
      </h2>
      <p className="mt-1 text-slate-700">PDF only, up to 30 pages and 50 MB, one book page per PDF page.</p>
      <p className="mt-2 rounded-lg bg-sky-50 p-3 text-slate-800 ring-1 ring-inset ring-sky-200">
        <strong>Before you upload:</strong> each page is sent to an outside AI service, which suggests the subject of the page.
        You check every suggestion before a child sees anything.
      </p>

      <label
        htmlFor={`${ids}-file`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`mt-4 flex min-h-24 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-4 text-center ${
          dragging ? 'border-sky-600 bg-sky-50' : 'border-slate-300 hover:bg-slate-50'
        }`}
      >
        <span className="font-semibold text-sky-800 underline">Choose a PDF</span>
        <span className="text-slate-600">or drop it here</span>
        {file && (
          <span className="mt-2 font-semibold text-slate-900">
            {file.name} · {formatMegabytes(file.size)}
          </span>
        )}
      </label>
      <input
        ref={fileInput}
        id={`${ids}-file`}
        type="file"
        accept="application/pdf,.pdf"
        className="sr-only"
        aria-describedby={fileError ? `${ids}-file-err` : undefined}
        aria-invalid={fileError ? true : undefined}
        onChange={(e) => pick(e.target.files?.[0] ?? null)}
      />
      {fileError && (
        <p id={`${ids}-file-err`} role="alert" className="mt-2 font-semibold text-rose-800">
          {fileError}
        </p>
      )}

      <div className="mt-4">
        <label htmlFor={`${ids}-title`} className="font-semibold">
          Book title <span className="font-normal text-slate-600">(optional)</span>
        </label>
        <input id={`${ids}-title`} className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} autoComplete="off" />
      </div>

      <fieldset className="mt-4">
        <legend className="font-semibold">Credits</legend>
        <p className="text-slate-600">Shown on the last page of the reader, with a note that the pages were adapted.</p>
        <div className="mt-2 grid gap-3 sm:grid-cols-2">
          {CREDIT_FIELDS.map(({ key, label, hint }) => (
            <div key={key}>
              <label htmlFor={`${ids}-${key}`} className="font-semibold">
                {label}
              </label>
              <input
                id={`${ids}-${key}`}
                className={inputClass}
                value={credits[key]}
                onChange={(e) => setCredits((c) => ({ ...c, [key]: e.target.value }))}
                autoComplete="off"
                aria-describedby={hint ? `${ids}-${key}-hint` : undefined}
              />
              {hint && (
                <p id={`${ids}-${key}-hint`} className="mt-1 text-sm text-slate-600">
                  {hint}
                </p>
              )}
            </div>
          ))}
        </div>
      </fieldset>

      {serverError && (
        <div role="alert" className="mt-4 rounded-lg bg-rose-50 p-3 text-rose-900 ring-1 ring-rose-200">
          <strong>The upload was not accepted.</strong> {serverError}
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Button type="submit" variant="primary" disabled={uploading}>
          {uploading ? 'Uploading…' : 'Upload book'}
        </Button>
        {uploading && <span role="status" className="text-slate-700">Sending the PDF to the server…</span>}
      </div>
    </form>
  );
}
