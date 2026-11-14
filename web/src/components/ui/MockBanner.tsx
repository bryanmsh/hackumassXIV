import { useState } from 'react';

type Flag = 'approveConflictNext' | 'readerForbiddenNext' | 'networkErrorNext' | 'uploadTooManyPagesNext';

const FLAGS: { flag: Flag; label: string }[] = [
  { flag: 'approveConflictNext', label: 'Next approve → 409 “look again”' },
  { flag: 'readerForbiddenNext', label: 'Next reader image → 403' },
  { flag: 'networkErrorNext', label: 'Next request → network error' },
  { flag: 'uploadTooManyPagesNext', label: 'Next upload → over 30 pages' },
];

/**
 * Unmistakable dev-only banner shown whenever Mock Service Worker answers API
 * calls. Scenario switches talk to window.__miraiMock, so no mock code is
 * imported here (and none ships in production builds).
 */
export function MockBanner({ compact = false }: { compact?: boolean }) {
  const [, force] = useState(0);
  const controls = typeof window !== 'undefined' ? window.__miraiMock : undefined;

  if (compact) {
    return (
      <div className="pointer-events-none fixed left-2 top-2 z-50 rounded bg-amber-400 px-2 py-0.5 text-xs font-bold text-black">
        MOCK DATA
      </div>
    );
  }

  return (
    <div className="border-b-4 border-amber-500 bg-amber-300 text-black">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2 text-sm sm:px-6">
        <strong className="tracking-wide">MOCK DATA</strong>
        <span>Not the real server. Shapes follow contracts/examples.json; data and images are fake.</span>
        {controls && (
          <details className="ml-auto">
            <summary className="cursor-pointer select-none font-semibold underline">Mock scenarios</summary>
            <div className="absolute right-4 z-50 mt-2 w-80 space-y-2 rounded-lg bg-white p-3 text-slate-900 shadow-lg ring-1 ring-slate-300">
              {FLAGS.map(({ flag, label }) => (
                <label key={flag} className="flex min-h-9 cursor-pointer items-center gap-2">
                  <input
                    type="checkbox"
                    className="size-5"
                    checked={controls.scenarios[flag]}
                    onChange={(e) => {
                      controls.scenarios[flag] = e.target.checked;
                      force((n) => n + 1);
                    }}
                  />
                  {label}
                </label>
              ))}
              <label className="flex items-center gap-2">
                Latency
                <select
                  className="rounded border border-slate-300 px-2 py-1"
                  value={controls.scenarios.latencyMs}
                  onChange={(e) => {
                    controls.scenarios.latencyMs = Number(e.target.value);
                    force((n) => n + 1);
                  }}
                >
                  <option value={0}>0 ms</option>
                  <option value={250}>250 ms</option>
                  <option value={1500}>1.5 s (slow Wi-Fi)</option>
                </select>
              </label>
              <button
                type="button"
                className="w-full rounded-md bg-slate-900 px-3 py-2 font-semibold text-white"
                onClick={() => {
                  controls.reset();
                  window.location.reload();
                }}
              >
                Reset mock data
              </button>
              <p className="text-xs text-slate-600">Flags reset after they fire once.</p>
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
