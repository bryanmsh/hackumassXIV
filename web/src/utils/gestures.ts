/**
 * Reader input gestures, from raw Pointer Events. Pure and clock-injectable
 * so it can be unit-tested, and shared by the device test page (/gesture-test)
 * and the Reader, so what is proven on the tablet is what ships.
 *
 * Spec: two-finger swipe turns the page; two-finger tap opens the teacher bar.
 * FINAL-plan fallback if those prove unreliable: long-press in a corner opens
 * the teacher bar, and a keyboard/clicker turns pages. A single touch must do
 * nothing, so it is reported only as 'single-tap' for the Reader to ignore.
 */

export type Corner = 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';

export type Gesture =
  | { type: 'swipe-next' } // two fingers moving left, like turning a page forward
  | { type: 'swipe-prev' } // two fingers moving right
  | { type: 'two-finger-tap' }
  | { type: 'corner-long-press'; corner: Corner }
  | { type: 'single-tap' } // the Reader ignores this
  | { type: 'ignored'; reason: string };

export interface GestureOptions {
  /** Horizontal travel (px, average of both fingers) that counts as a swipe. */
  swipeMinPx: number;
  /** Most a finger may move (px) and still count as a tap or a press. */
  tapMaxMovePx: number;
  /** Longest a tap may last (ms). */
  tapMaxMs: number;
  /** The second finger must land within this time of the first (ms). */
  pairWindowMs: number;
  /** How long a corner press must be held (ms). */
  longPressMs: number;
  /** Size of each corner zone (px). */
  cornerPx: number;
}

export const DEFAULT_GESTURE_OPTIONS: GestureOptions = {
  swipeMinPx: 60,
  tapMaxMovePx: 24,
  tapMaxMs: 450,
  pairWindowMs: 250,
  longPressMs: 800,
  cornerPx: 140,
};

export interface PointerSample {
  id: number;
  x: number;
  y: number;
  /** Time in ms (any monotonic clock). */
  t: number;
}

export interface Clock {
  setTimeout: (fn: () => void, ms: number) => unknown;
  clearTimeout: (handle: unknown) => void;
}

interface Track {
  x0: number;
  y0: number;
  x: number;
  y: number;
  t0: number;
  up: boolean;
}

const realClock: Clock = {
  setTimeout: (fn, ms) => globalThis.setTimeout(fn, ms),
  clearTimeout: (h) => globalThis.clearTimeout(h as ReturnType<typeof setTimeout>),
};

export function cornerAt(x: number, y: number, width: number, height: number, size: number): Corner | null {
  const left = x <= size;
  const right = x >= width - size;
  const top = y <= size;
  const bottom = y >= height - size;
  if (top && left) return 'top-left';
  if (top && right) return 'top-right';
  if (bottom && left) return 'bottom-left';
  if (bottom && right) return 'bottom-right';
  return null;
}

export class GestureRecognizer {
  private tracks = new Map<number, Track>();
  private kind: 'none' | 'one' | 'two' | 'invalid' = 'none';
  private reason = '';
  private firstDownAt = 0;
  private lastUpAt = 0;
  private timer: unknown = null;
  private pressFired = false;
  private readonly opts: GestureOptions;

  constructor(
    private readonly emit: (g: Gesture) => void,
    opts: Partial<GestureOptions> = {},
    private readonly clock: Clock = realClock,
  ) {
    this.opts = { ...DEFAULT_GESTURE_OPTIONS, ...opts };
  }

  /** `width`/`height`: the gesture surface's size, for the corner zones. */
  down(p: PointerSample, width: number, height: number): void {
    const active = [...this.tracks.values()].filter((t) => !t.up).length;
    this.tracks.set(p.id, { x0: p.x, y0: p.y, x: p.x, y: p.y, t0: p.t, up: false });

    if (this.kind === 'none') {
      this.kind = 'one';
      this.firstDownAt = p.t;
      this.pressFired = false;
      const corner = cornerAt(p.x, p.y, width, height, this.opts.cornerPx);
      if (corner) {
        this.timer = this.clock.setTimeout(() => {
          this.timer = null;
          const t = this.tracks.get(p.id);
          if (this.kind === 'one' && t && !t.up && this.moved(t) <= this.opts.tapMaxMovePx) {
            this.pressFired = true;
            this.emit({ type: 'corner-long-press', corner });
          }
        }, this.opts.longPressMs);
      }
      return;
    }

    this.stopTimer();
    if (this.kind === 'one' && active === 1 && p.t - this.firstDownAt <= this.opts.pairWindowMs) {
      this.kind = 'two';
    } else if (this.kind !== 'invalid') {
      this.invalidate(active >= 2 ? 'three or more fingers' : 'second finger landed too late');
    }
  }

  move(p: PointerSample): void {
    const t = this.tracks.get(p.id);
    if (!t || t.up) return;
    t.x = p.x;
    t.y = p.y;
    if (this.kind === 'one' && this.timer !== null && this.moved(t) > this.opts.tapMaxMovePx) this.stopTimer();
  }

  up(p: PointerSample): void {
    const t = this.tracks.get(p.id);
    if (!t) return;
    t.x = p.x;
    t.y = p.y;
    t.up = true;
    this.lastUpAt = p.t;
    if ([...this.tracks.values()].every((x) => x.up)) this.finish();
  }

  /** The browser took the pointer (scroll, zoom, system gesture): that gesture is void. */
  cancel(p: Pick<PointerSample, 'id'>): void {
    const t = this.tracks.get(p.id);
    if (!t) return;
    t.up = true;
    if (this.kind !== 'invalid') this.invalidate('browser cancelled the touch (pointercancel)');
    if ([...this.tracks.values()].every((x) => x.up)) this.finish();
  }

  reset(): void {
    this.stopTimer();
    this.tracks.clear();
    this.kind = 'none';
    this.reason = '';
    this.pressFired = false;
  }

  private moved(t: Track): number {
    return Math.hypot(t.x - t.x0, t.y - t.y0);
  }

  private invalidate(reason: string) {
    this.stopTimer();
    this.kind = 'invalid';
    this.reason = reason;
  }

  private stopTimer() {
    if (this.timer !== null) {
      this.clock.clearTimeout(this.timer);
      this.timer = null;
    }
  }

  private finish() {
    this.stopTimer();
    const tracks = [...this.tracks.values()];
    const kind = this.kind;
    const reason = this.reason;
    const fired = this.pressFired;
    const duration = this.lastUpAt - this.firstDownAt;
    this.reset();

    if (kind === 'invalid') {
      this.emit({ type: 'ignored', reason });
      return;
    }
    if (kind === 'one') {
      if (fired) return; // already reported as a corner long-press
      const t = tracks[0]!;
      if (this.moved(t) <= this.opts.tapMaxMovePx && duration <= this.opts.tapMaxMs) this.emit({ type: 'single-tap' });
      else this.emit({ type: 'ignored', reason: 'one finger: drag or long touch' });
      return;
    }
    if (kind === 'two' && tracks.length === 2) {
      const [a, b] = tracks as [Track, Track];
      const dxA = a.x - a.x0;
      const dxB = b.x - b.x0;
      const dx = (dxA + dxB) / 2;
      const dy = (a.y - a.y0 + (b.y - b.y0)) / 2;
      const sameWay = Math.sign(dxA) === Math.sign(dxB);
      if (Math.abs(dx) >= this.opts.swipeMinPx && Math.abs(dx) > 1.5 * Math.abs(dy) && sameWay) {
        this.emit({ type: dx < 0 ? 'swipe-next' : 'swipe-prev' });
        return;
      }
      const still = this.moved(a) <= this.opts.tapMaxMovePx && this.moved(b) <= this.opts.tapMaxMovePx;
      if (still && duration <= this.opts.tapMaxMs) {
        this.emit({ type: 'two-finger-tap' });
        return;
      }
      this.emit({ type: 'ignored', reason: 'two fingers: not a clear swipe or tap' });
    }
  }
}
