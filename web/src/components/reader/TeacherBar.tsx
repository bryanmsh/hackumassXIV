import { useEffect, useRef } from 'react';
import { Link } from 'react-router';
import type { Level, ReaderManifest, ReaderVersion } from '../../types/api';
import { levelName } from '../../utils/display';
import { SKIP_REASON_TEXT } from '../../utils/readerNav';

interface Props {
  manifest: ReaderManifest;
  /** "Page 3 · 2 of 5" or "Credits". */
  position: string;
  canPrev: boolean;
  canNext: boolean;
  onPrev: () => void;
  onNext: () => void;
  onSwitch: (v: ReaderVersion) => void;
  onClose: () => void;
  fullscreen: { supported: boolean; active: boolean; toggle: () => void };
  /** True while the manifests are being re-checked with the server. */
  checking: boolean;
  /** The last re-check or switch failed; what is shown is still the last approved version. */
  checkError: string | null;
  /** The current page could not be shown (e.g. 403). Explained here, never in front of the child. */
  pageProblem: string | null;
}

const btn = 'min-h-12 rounded-lg px-4 text-base font-semibold disabled:cursor-not-allowed';

/**
 * Teacher-only controls, hidden until the teacher asks for them (the T key). Lists only versions the server says are fully
 * approved as choices; the rest are greyed "not approved". Approving happens
 * outside the reader.
 */
export function TeacherBar({ manifest, position, canPrev, canNext, onPrev, onNext, onSwitch, onClose, fullscreen, checking, checkError, pageProblem }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => closeRef.current?.focus(), []);

  const isCurrent = (v: ReaderVersion) => v.profile_id === manifest.profile_id && v.level === manifest.level;
  const sheetLink = `/books/${encodeURIComponent(manifest.book_id)}/approve?profile=${encodeURIComponent(manifest.profile_id)}&level=${manifest.level}`;
  const current = manifest.versions.find(isCurrent);
  const partial = manifest.skipped.some((s) => s.reason !== 'omitted');

  return (
    <div
      role="dialog"
      aria-label="Teacher controls"
      className="fixed inset-x-0 bottom-0 z-40 max-h-[80vh] overflow-y-auto bg-white p-4 text-slate-900 shadow-[0_-4px_24px_rgba(0,0,0,0.4)] sm:p-6"
      onPointerDown={(e) => e.stopPropagation()}
    >
      <div className="mx-auto max-w-5xl space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold">{manifest.title}</h2>
            <p className="text-slate-700">
              {current ? `${current.profile_name} · ${levelName(manifest.level as Level)}` : levelName(manifest.level as Level)} · {position}
              {checking && <span className="ml-2 text-sm text-slate-500">checking approvals…</span>}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className={`${btn} bg-slate-100 ring-1 ring-slate-300`} disabled={!canPrev} onClick={onPrev}>
              ← Previous page
            </button>
            <button type="button" className={`${btn} bg-slate-100 ring-1 ring-slate-300`} disabled={!canNext} onClick={onNext}>
              Next page →
            </button>
            {fullscreen.supported && (
              <button type="button" className={`${btn} bg-slate-100 ring-1 ring-slate-300`} onClick={fullscreen.toggle}>
                {fullscreen.active ? 'Leave full screen' : 'Full screen'}
              </button>
            )}
            <button ref={closeRef} type="button" className={`${btn} bg-sky-700 text-white`} onClick={onClose}>
              Close
            </button>
          </div>
        </div>

        {pageProblem && (
          <div role="alert" className="rounded-lg bg-rose-50 p-3 text-rose-900 ring-1 ring-rose-200">
            <p>{pageProblem}</p>
            <Link to={sheetLink} className="font-semibold underline">
              Leave the reader and open the contact sheet
            </Link>
          </div>
        )}
        {checkError && (
          <p role="alert" className="rounded-lg bg-amber-50 p-3 text-amber-950 ring-1 ring-amber-300">
            Could not check with the server: {checkError}. The pages shown are still the last version the server approved.
          </p>
        )}

        <section aria-labelledby="tb-versions">
          <h3 id="tb-versions" className="font-semibold">
            Child and look
          </h3>
          <ul className="mt-2 flex flex-wrap gap-2">
            {manifest.versions.map((v) => {
              const cur = isCurrent(v);
              const label = `${v.profile_name} · ${levelName(v.level)}`;
              return (
                <li key={`${v.profile_id}|${v.level}`}>
                  <button
                    type="button"
                    aria-current={cur ? 'true' : undefined}
                    disabled={cur || !v.fully_approved}
                    onClick={() => onSwitch(v)}
                    className={`${btn} ring-1 ring-inset ${
                      cur
                        ? 'bg-sky-700 text-white ring-sky-800'
                        : v.fully_approved
                          ? 'bg-white ring-slate-300 hover:bg-slate-50'
                          : 'bg-slate-100 text-slate-400 ring-slate-200'
                    }`}
                  >
                    {label}
                    {!v.fully_approved && !cur && <span className="ml-1 text-sm font-normal"> (not approved)</span>}
                  </button>
                </li>
              );
            })}
          </ul>
          <p className="mt-2 text-sm text-slate-600">
            Only fully approved versions can be chosen here. To approve another,{' '}
            <Link to={sheetLink} className="font-semibold text-sky-800 underline">
              leave the reader and open the contact sheet
            </Link>
            .
          </p>
        </section>

        {manifest.skipped.length > 0 && (
          <section aria-labelledby="tb-skipped">
            <h3 id="tb-skipped" className="font-semibold">
              Skipped pages
            </h3>
            <p className="text-slate-700">
              {manifest.skipped.map((s) => `page ${s.number} (${SKIP_REASON_TEXT[s.reason] ?? s.reason})`).join(', ')}
            </p>
            {partial && <p className="text-sm text-slate-600">Pages that are not approved are never shown; approve them on the contact sheet.</p>}
          </section>
        )}

        <p className="text-sm text-slate-600">
          Keys: → or Space next page, ← previous page, T or Esc to hide this bar. A clicker that sends the arrow or Page keys works
          too.
        </p>
      </div>
    </div>
  );
}
