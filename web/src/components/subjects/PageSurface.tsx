import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react';
import { api } from '../../api';
import { useImageBlob } from '../../hooks/useImageBlob';
import type { Candidate, NormPoint, Page } from '../../types/api';
import {
  boxArea,
  boxToPercent,
  clientToNorm,
  containRect,
  isValidBox,
  simplifyOutline,
  type Rect,
} from '../../utils/coordinates';
import { formatConfidence } from '../../utils/display';
import { subjectNumber, subjectTone } from '../../utils/subjectColors';
import { Button } from '../ui/Button';
import { errorMessage } from '../ui/LoadState';

export type EditorMode = 'suggestions' | 'point' | 'refine' | 'outline';

/** A new stroke vertex is kept only once the pointer has moved this far (page fraction). */
const STROKE_STEP = 0.003;

interface Props {
  page: Page;
  mode: EditorMode;
  disabled?: boolean;
  onPickCandidate: (index: number) => void;
  /** Point mode: the spot the teacher tapped (not sent until they press Cut out). */
  point: NormPoint | null;
  onPoint: (point: NormPoint | null, inside: boolean) => void;
  /** Outline mode: the finished stroke, already thinned to at most 200 points. */
  outline: NormPoint[];
  onOutline: (points: NormPoint[]) => void;
  /** What was last sent, drawn dashed over the new highlight so alignment can be checked by eye. */
  sent: { point?: NormPoint; outline?: NormPoint[] } | null;
  /** Largest height the page may take, in vh. */
  maxHeightVh?: number;
  /** The suggestion the teacher is pointing at, on the page or in the list; the others dim. */
  highlight?: number | null;
  onHighlight?: (index: number | null) => void;
  /** Shown over the page while the server makes a cut-out; clicks wait meanwhile. */
  busyLabel?: string | null;
}

const polyPoints = (pts: NormPoint[]) => pts.map(([x, y]) => `${x},${y}`).join(' ');

/**
 * The original page (via GET /pages/{id}/overlay) with candidate boxes, a tap
 * marker and the outline drawn over it. All overlays live in one "frame"
 * element that covers exactly the drawn image, never the letterboxing, and
 * every pointer position is measured against that frame's bounding rectangle.
 */
export function PageSurface({
  page,
  mode,
  disabled = false,
  onPickCandidate,
  point,
  onPoint,
  outline,
  onOutline,
  sent,
  maxHeightVh = 70,
  highlight = null,
  onHighlight,
  busyLabel = null,
}: Props) {
  const frameRef = useRef<HTMLDivElement>(null);
  const stroke = useRef<{ id: number; points: NormPoint[] } | null>(null);
  const [live, setLive] = useState<NormPoint[] | null>(null);
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const [nonce, setNonce] = useState(0);

  const processing = page.state === 'processing';
  const img = useImageBlob(
    (signal) => api.getOverlay(page.id, signal),
    processing ? null : `${page.id}:${page.subject_hash ?? 'none'}:${page.state}:${nonce}`,
  );

  // A new image may have a different shape; measure it again when it loads.
  useEffect(() => setNatural(null), [img.url]);

  const pw = page.width > 0 ? page.width : 4;
  const ph = page.height > 0 ? page.height : 3;
  const nw = natural?.w ?? pw;
  const nh = natural?.h ?? ph;
  // Container has the page's shape; the frame is where the image is actually drawn inside it.
  const drawn = containRect({ left: 0, top: 0, width: pw, height: ph }, nw, nh);
  const frameStyle = {
    left: `${(drawn.left / pw) * 100}%`,
    top: `${(drawn.top / ph) * 100}%`,
    width: `${(drawn.width / pw) * 100}%`,
    height: `${(drawn.height / ph) * 100}%`,
  };
  const shapeMismatch = natural !== null && Math.abs(nw / nh - pw / ph) / (pw / ph) > 0.02;

  function frameRect(): Rect | null {
    const el = frameRef.current;
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, width: r.width, height: r.height };
  }

  // ----- Point mode -----
  function onTap(e: React.MouseEvent<HTMLDivElement>) {
    if ((mode !== 'point' && mode !== 'refine') || disabled) return;
    const rect = frameRect();
    if (!rect) return;
    const { point: p, inside } = clientToNorm(e.clientX, e.clientY, rect);
    onPoint(inside ? p : null, inside);
  }

  // ----- Outline mode (Pointer Events: mouse or trackpad; pen and touch also work) -----
  function onPointerDown(e: ReactPointerEvent<HTMLDivElement>) {
    if (mode !== 'outline' || disabled || !e.isPrimary || stroke.current) return;
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    const rect = frameRect();
    if (!rect) return;
    const { point: p, inside } = clientToNorm(e.clientX, e.clientY, rect);
    if (!inside) return; // a stroke must start on the page
    e.preventDefault();
    try {
      e.currentTarget.setPointerCapture(e.pointerId);
    } catch {
      // Not supported (or pointer already gone): drawing still works while over the page.
    }
    stroke.current = { id: e.pointerId, points: [p] };
    setLive([p]);
  }

  function onPointerMove(e: ReactPointerEvent<HTMLDivElement>) {
    const s = stroke.current;
    if (!s || e.pointerId !== s.id) return;
    const rect = frameRect();
    if (!rect) return;
    e.preventDefault();
    // Past the edge, the line is held at the edge (clamped) rather than dropped.
    const { point: p } = clientToNorm(e.clientX, e.clientY, rect);
    const last = s.points[s.points.length - 1]!;
    if (Math.hypot(p[0] - last[0], p[1] - last[1]) < STROKE_STEP) return;
    s.points.push(p);
    setLive(s.points.slice());
  }

  function endStroke(e: ReactPointerEvent<HTMLDivElement>) {
    const s = stroke.current;
    if (!s || e.pointerId !== s.id) return;
    stroke.current = null;
    setLive(null);
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      // Already released.
    }
    onOutline(simplifyOutline(s.points));
  }

  // Leaving outline mode mid-stroke drops the stroke.
  useEffect(() => {
    if (mode !== 'outline') {
      stroke.current = null;
      setLive(null);
    }
  }, [mode]);

  const boxes = page.candidates
    .map((c, i) => ({ c, i }))
    .filter(({ c }) => isValidBox(c.box))
    // Bigger boxes first, so smaller ones sit on top and stay clickable.
    .sort((a, b) => boxArea(b.c.box) - boxArea(a.c.box));

  const label =
    mode === 'point'
      ? 'Page. Click the object to choose it.'
      : mode === 'refine'
        ? 'Page. Click the part the cut-out missed.'
      : mode === 'outline'
        ? 'Page. Draw a line around the object.'
        : 'Page with suggested subjects.';

  return (
    <div>
      <div
        className="relative mx-auto overflow-hidden rounded-xl bg-slate-200 ring-1 ring-slate-300"
        style={{ aspectRatio: `${pw} / ${ph}`, width: `min(100%, calc(${maxHeightVh}vh * ${pw / ph}))` }}
      >
        {img.url && (
          <img
            src={img.url}
            alt={`Page ${page.number}${page.selected !== null ? ', current subject highlighted' : ''}`}
            className="absolute inset-0 h-full w-full select-none object-contain"
            draggable={false}
            onLoad={(e) => {
              const el = e.currentTarget;
              if (el.naturalWidth > 0 && el.naturalHeight > 0) setNatural({ w: el.naturalWidth, h: el.naturalHeight });
            }}
          />
        )}
        {processing && <Centered>This page is still processing.</Centered>}
        {img.status === 'loading' && <Centered>Loading the page…</Centered>}
        {img.status === 'error' && (
          <Centered>
            <span role="alert" className="text-rose-900">
              The page image did not load: {errorMessage(img.error)}
            </span>
            <Button className="mt-3" onClick={() => setNonce((n) => n + 1)}>
              Try again
            </Button>
          </Centered>
        )}

        {img.url && (
          <div
            ref={frameRef}
            data-testid="image-frame"
            role="group"
            aria-label={label}
            // Scrolling and zoom are blocked only on this surface, and only in outline mode.
            className={`absolute ${mode === 'outline' ? 'touch-none' : 'touch-manipulation'} ${
              mode !== 'suggestions' && !disabled ? 'cursor-crosshair' : ''
            }`}
            style={frameStyle}
            onClick={onTap}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={endStroke}
            onPointerCancel={endStroke}
          >
            {mode === 'suggestions' &&
              boxes.map(({ c, i }) => (
                <CandidateBox
                  key={`${i}:${c.mask_hash}`}
                  c={c}
                  index={i}
                  selected={page.selected === i}
                  dimmed={highlight !== null && highlight !== i}
                  disabled={disabled}
                  onPick={() => onPickCandidate(i)}
                  onHighlight={onHighlight}
                />
              ))}

            <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 1 1" preserveAspectRatio="none" aria-hidden>
              {sent?.outline && sent.outline.length >= 3 && (
                <polygon
                  data-testid="sent-outline"
                  points={polyPoints(sent.outline)}
                  fill="none"
                  stroke="#FFFFFF"
                  strokeWidth={4}
                  strokeDasharray="6 5"
                  vectorEffect="non-scaling-stroke"
                  style={{ filter: 'drop-shadow(0 0 1px #000)' }}
                />
              )}
              {mode === 'outline' && live && live.length > 1 && (
                <polyline points={polyPoints(live)} fill="none" stroke="#0369A1" strokeWidth={4} vectorEffect="non-scaling-stroke" />
              )}
              {mode === 'outline' && !live && outline.length >= 3 && (
                <polygon
                  data-testid="drawn-outline"
                  points={polyPoints(outline)}
                  fill="rgba(3,105,161,0.15)"
                  stroke="#0369A1"
                  strokeWidth={4}
                  vectorEffect="non-scaling-stroke"
                />
              )}
            </svg>

            {(mode === 'point' || mode === 'refine') && point && <Marker point={point} testId="tap-marker" />}
            {sent?.point && <Marker point={sent.point} testId="sent-marker" dashed />}
          </div>
        )}
        {busyLabel && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/50" data-testid="surface-busy">
            <span role="status" className="rounded-lg bg-white px-4 py-2 font-semibold text-slate-900 shadow ring-1 ring-slate-300">
              {busyLabel}
            </span>
          </div>
        )}
      </div>
      {shapeMismatch && (
        <p role="alert" className="mt-2 text-sm text-amber-900">
          The page image ({natural?.w}×{natural?.h}) is not the shape the server reported ({page.width}×{page.height}).
          Positions may be off; tell the Mirai team before using this page.
        </p>
      )}
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center text-slate-700">{children}</div>;
}

function Marker({ point: [x, y], testId, dashed = false }: { point: NormPoint; testId: string; dashed?: boolean }) {
  return (
    <span
      data-testid={testId}
      aria-hidden
      className={`pointer-events-none absolute size-8 -translate-x-1/2 -translate-y-1/2 rounded-full border-4 ${
        dashed ? 'border-dashed border-white' : 'border-sky-700 bg-white/40'
      } shadow-[0_0_0_2px_rgba(0,0,0,0.6)]`}
      style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
    />
  );
}

function CandidateBox({
  c,
  index,
  selected,
  dimmed,
  disabled,
  onPick,
  onHighlight,
}: {
  c: Candidate;
  index: number;
  selected: boolean;
  dimmed: boolean;
  disabled: boolean;
  onPick: () => void;
  onHighlight?: (index: number | null) => void;
}) {
  const name = c.label || 'Unlabeled';
  const tone = subjectTone(index);
  const conf = c.source === 'auto' ? `, the AI’s guess with confidence ${formatConfidence(c.confidence)}` : '';
  return (
    <button
      type="button"
      disabled={disabled || selected}
      aria-pressed={selected}
      aria-label={`${selected ? 'Current subject' : 'Pick'} ${name}, number ${subjectNumber(index)}${conf}`}
      onClick={(e) => {
        e.stopPropagation();
        onPick();
      }}
      onMouseEnter={() => onHighlight?.(index)}
      onMouseLeave={() => onHighlight?.(null)}
      onFocus={() => onHighlight?.(index)}
      onBlur={() => onHighlight?.(null)}
      // The box takes the suggestion's colour, with a white edge so it shows on any artwork.
      className={`absolute rounded-sm text-left shadow-[0_0_0_2px_#fff] disabled:cursor-default ${tone.border} ${
        selected ? 'border-4' : 'border-[3px] border-dashed hover:border-solid'
      } ${dimmed ? 'opacity-40' : ''}`}
      style={boxToPercent(c.box)}
    >
    </button>
  );
}
