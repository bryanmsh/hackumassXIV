import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { useGestures } from '../hooks/useGestures';
import type { Gesture } from '../utils/gestures';

/**
 * Hour-4 device check (FINAL plan): before the Reader is built, prove on the
 * actual demo tablet which page-turn and teacher-bar gestures are reliable.
 * Uses the same recognizer the Reader will use. Teacher/developer tool only;
 * it touches no data and calls no API.
 */

const TRIALS: { key: Gesture['type']; label: string; how: string }[] = [
  { key: 'swipe-next', label: 'Next page', how: 'Two-finger swipe to the left' },
  { key: 'swipe-prev', label: 'Previous page', how: 'Two-finger swipe to the right' },
  { key: 'two-finger-tap', label: 'Teacher bar', how: 'Tap with two fingers at once' },
  { key: 'corner-long-press', label: 'Teacher bar (fallback)', how: 'Hold one finger in a corner for 1 second' },
  { key: 'single-tap', label: 'Must do nothing', how: 'Tap with one finger (the Reader ignores it)' },
];

const KEYS: Record<string, string> = { ArrowRight: 'next page', ' ': 'next page', ArrowLeft: 'previous page', t: 'teacher bar', T: 'teacher bar' };

interface LogLine {
  at: string;
  text: string;
  bad?: boolean;
}

function describe(g: Gesture): string {
  if (g.type === 'corner-long-press') return `corner long-press (${g.corner})`;
  if (g.type === 'ignored') return `ignored: ${g.reason}`;
  return g.type;
}

export function GestureTestPage() {
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [log, setLog] = useState<LogLine[]>([]);
  const [zoomed, setZoomed] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);
  const startScale = useRef(typeof window !== 'undefined' ? (window.visualViewport?.scale ?? 1) : 1);

  function add(text: string, bad = false) {
    const at = new Date().toLocaleTimeString();
    setLog((l) => [{ at, text, bad }, ...l].slice(0, 40));
  }

  const gestures = useGestures((g) => {
    setCounts((c) => ({ ...c, [g.type]: (c[g.type] ?? 0) + 1 }));
    add(describe(g), g.type === 'ignored');
  });

  useEffect(() => {
    const vv = window.visualViewport;
    const onViewport = () => {
      if (vv && Math.abs(vv.scale - startScale.current) > 0.01) setZoomed(true);
    };
    const onScroll = () => {
      if (window.scrollY !== 0 || window.scrollX !== 0) setScrolled(true);
    };
    const onFs = () => setFullscreen(document.fullscreenElement !== null);
    const onKey = (e: KeyboardEvent) => {
      const action = KEYS[e.key];
      if (!action) return;
      e.preventDefault();
      if (e.repeat) return;
      setCounts((c) => ({ ...c, [`key:${action}`]: (c[`key:${action}`] ?? 0) + 1 }));
      add(`key ${e.key === ' ' ? 'Space' : e.key} → ${action}`);
    };
    vv?.addEventListener('resize', onViewport);
    window.addEventListener('scroll', onScroll);
    document.addEventListener('fullscreenchange', onFs);
    window.addEventListener('keydown', onKey);
    return () => {
      vv?.removeEventListener('resize', onViewport);
      window.removeEventListener('scroll', onScroll);
      document.removeEventListener('fullscreenchange', onFs);
      window.removeEventListener('keydown', onKey);
    };
  }, []);

  const canFullscreen = typeof document !== 'undefined' && typeof document.documentElement.requestFullscreen === 'function';

  function summary(): string {
    const lines = [
      `Mirai gesture test, ${new Date().toISOString()}`,
      `Device: ${navigator.userAgent}`,
      `Screen ${window.screen.width}x${window.screen.height}, viewport ${window.innerWidth}x${window.innerHeight}, DPR ${window.devicePixelRatio}, touch points ${navigator.maxTouchPoints}`,
      `Full screen: ${canFullscreen ? (fullscreen ? 'on' : 'supported, off') : 'not supported'}`,
      `Browser zoomed during test: ${zoomed ? 'YES' : 'no'}; page scrolled: ${scrolled ? 'YES' : 'no'}`,
      ...TRIALS.map((t) => `${t.how}: ${counts[t.key] ?? 0}`),
      `Ignored / cancelled: ${counts.ignored ?? 0}`,
      ...Object.entries(counts)
        .filter(([k]) => k.startsWith('key:'))
        .map(([k, n]) => `Keyboard ${k.slice(4)}: ${n}`),
    ];
    return lines.join('\n');
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-white lg:flex-row">
      <div
        {...gestures.handlers}
        aria-label="Gesture test surface"
        className={`relative min-h-[60vh] flex-1 bg-black lg:min-h-screen ${gestures.className}`}
        style={{ WebkitUserSelect: 'none', WebkitTouchCallout: 'none' }}
      >
        {(['top-left', 'top-right', 'bottom-left', 'bottom-right'] as const).map((c) => (
          <div
            key={c}
            aria-hidden
            className={`pointer-events-none absolute size-[140px] border-2 border-dashed border-white/20 ${c.includes('top') ? 'top-0' : 'bottom-0'} ${
              c.includes('left') ? 'left-0' : 'right-0'
            }`}
          />
        ))}
        <p className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 text-center text-xl text-white/40">
          Try gestures here
        </p>
      </div>

      <aside className="w-full space-y-4 overflow-y-auto p-4 lg:max-h-screen lg:w-96">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold">Reader gesture test</h1>
          <Link to="/" className="font-semibold text-sky-300 underline">
            Exit
          </Link>
        </div>
        <p className="text-sm text-slate-300">
          Do each gesture 10 times on the demo tablet, in full screen. A gesture is reliable if every try counts and nothing is
          ignored. Laptop: press → or Space, ←, and T.
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!canFullscreen}
            className="min-h-11 rounded-lg bg-sky-700 px-3 font-semibold disabled:bg-slate-700"
            onClick={() => {
              if (document.fullscreenElement) void document.exitFullscreen();
              else void document.documentElement.requestFullscreen().catch(() => add('Full screen was refused', true));
            }}
          >
            {canFullscreen ? (fullscreen ? 'Leave full screen' : 'Go full screen') : 'Full screen not supported'}
          </button>
          <button type="button" className="min-h-11 rounded-lg bg-slate-700 px-3 font-semibold" onClick={() => {
            setCounts({});
            setLog([]);
            setZoomed(false);
            setScrolled(false);
          }}>
            Reset
          </button>
          <button
            type="button"
            className="min-h-11 rounded-lg bg-slate-700 px-3 font-semibold"
            onClick={() => {
              void navigator.clipboard
                ?.writeText(summary())
                .then(() => setCopied(true))
                .catch(() => add('Copy failed; take a screenshot instead', true));
            }}
          >
            {copied ? 'Copied' : 'Copy results'}
          </button>
        </div>

        <table className="w-full text-left text-sm">
          <tbody>
            {TRIALS.map((t) => (
              <tr key={t.key} className="border-b border-slate-800">
                <td className="py-2 pr-2">
                  <div className="font-semibold">{t.label}</div>
                  <div className="text-slate-400">{t.how}</div>
                </td>
                <td className="py-2 text-right text-2xl font-bold tabular-nums" data-testid={`count-${t.key}`}>
                  {counts[t.key] ?? 0}
                </td>
              </tr>
            ))}
            <tr>
              <td className="py-2 font-semibold text-amber-300">Ignored or cancelled by the browser</td>
              <td className="py-2 text-right text-2xl font-bold tabular-nums text-amber-300" data-testid="count-ignored">
                {counts.ignored ?? 0}
              </td>
            </tr>
          </tbody>
        </table>

        {(zoomed || scrolled) && (
          <p role="alert" className="rounded-lg bg-rose-900 p-3 font-semibold">
            The browser {zoomed ? 'zoomed' : 'scrolled'} during the test. These gestures are not safe on this device.
          </p>
        )}

        <ol className="space-y-1 font-mono text-sm" aria-label="Gesture log">
          {log.map((l, i) => (
            <li key={log.length - i} className={l.bad ? 'text-amber-300' : 'text-slate-200'}>
              {l.at} {l.text}
            </li>
          ))}
        </ol>
      </aside>
    </div>
  );
}
