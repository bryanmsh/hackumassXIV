/** Reader gesture recognizer, driven with synthetic pointers and a fake clock. */
import { describe, expect, it } from 'vitest';
import { GestureRecognizer, cornerAt, type Clock, type Gesture } from '../utils/gestures';

const W = 1024;
const H = 768;

function setup() {
  const out: Gesture[] = [];
  let timers: { fn: () => void; at: number; id: number }[] = [];
  let now = 0;
  let next = 1;
  const clock: Clock = {
    setTimeout: (fn, ms) => {
      const id = next++;
      timers.push({ fn, at: now + ms, id });
      return id;
    },
    clearTimeout: (h) => {
      timers = timers.filter((t) => t.id !== h);
    },
  };
  const r = new GestureRecognizer((g) => out.push(g), {}, clock);
  const advance = (ms: number) => {
    now += ms;
    const due = timers.filter((t) => t.at <= now);
    timers = timers.filter((t) => t.at > now);
    due.forEach((t) => t.fn());
  };
  const down = (id: number, x: number, y: number) => r.down({ id, x, y, t: now }, W, H);
  const move = (id: number, x: number, y: number) => r.move({ id, x, y, t: now });
  const up = (id: number, x: number, y: number) => r.up({ id, x, y, t: now });
  return { out, r, advance, down, move, up };
}

describe('GestureRecognizer', () => {
  it('two-finger swipe left = next page', () => {
    const g = setup();
    g.down(1, 600, 300);
    g.advance(30);
    g.down(2, 600, 420);
    g.advance(100);
    g.move(1, 450, 305);
    g.move(2, 455, 425);
    g.up(1, 420, 305);
    g.up(2, 425, 425);
    expect(g.out).toEqual([{ type: 'swipe-next' }]);
  });

  it('two-finger swipe right = previous page', () => {
    const g = setup();
    g.down(1, 300, 300);
    g.down(2, 300, 420);
    g.advance(150);
    g.up(1, 450, 310);
    g.up(2, 440, 430);
    expect(g.out).toEqual([{ type: 'swipe-prev' }]);
  });

  it('two-finger tap = teacher bar', () => {
    const g = setup();
    g.down(1, 500, 300);
    g.advance(20);
    g.down(2, 560, 320);
    g.advance(120);
    g.up(1, 503, 302);
    g.up(2, 561, 318);
    expect(g.out).toEqual([{ type: 'two-finger-tap' }]);
  });

  it('a single tap is reported only as single-tap (the Reader ignores it)', () => {
    const g = setup();
    g.down(1, 500, 300);
    g.advance(100);
    g.up(1, 502, 301);
    expect(g.out).toEqual([{ type: 'single-tap' }]);
  });

  it('a one-finger swipe is never a page turn', () => {
    const g = setup();
    g.down(1, 600, 300);
    g.advance(150);
    g.move(1, 300, 300);
    g.up(1, 300, 300);
    expect(g.out).toEqual([{ type: 'ignored', reason: 'one finger: drag or long touch' }]);
  });

  it('holding a corner for 0.8 s fires the fallback teacher bar once', () => {
    const g = setup();
    g.down(1, 30, 740);
    g.advance(799);
    expect(g.out).toEqual([]);
    g.advance(1);
    expect(g.out).toEqual([{ type: 'corner-long-press', corner: 'bottom-left' }]);
    g.advance(500);
    g.up(1, 30, 740);
    expect(g.out).toHaveLength(1);
  });

  it('a long press away from the corners, or one that moves, does nothing', () => {
    const g = setup();
    g.down(1, 500, 400);
    g.advance(1500);
    g.up(1, 500, 400);
    g.down(2, 20, 20);
    g.advance(200);
    g.move(2, 90, 90);
    g.advance(1000);
    g.up(2, 90, 90);
    expect(g.out.some((x) => x.type === 'corner-long-press')).toBe(false);
  });

  it('a second finger joining a corner press cancels the long press', () => {
    const g = setup();
    g.down(1, 20, 20);
    g.advance(100);
    g.down(2, 200, 200);
    g.advance(1000);
    expect(g.out.some((x) => x.type === 'corner-long-press')).toBe(false);
  });

  it('three fingers, a late second finger, or a browser cancel are ignored', () => {
    const g = setup();
    g.down(1, 500, 300);
    g.down(2, 560, 300);
    g.down(3, 620, 300);
    g.advance(100);
    g.up(1, 400, 300);
    g.up(2, 460, 300);
    g.up(3, 520, 300);
    expect(g.out.pop()).toEqual({ type: 'ignored', reason: 'three or more fingers' });

    g.down(1, 500, 300);
    g.advance(600);
    g.down(2, 560, 300);
    g.up(1, 300, 300);
    g.up(2, 360, 300);
    expect(g.out.pop()).toEqual({ type: 'ignored', reason: 'second finger landed too late' });

    g.down(1, 500, 300);
    g.down(2, 560, 300);
    g.r.cancel({ id: 1 });
    g.up(2, 300, 300);
    expect(g.out.pop()).toEqual({ type: 'ignored', reason: 'browser cancelled the touch (pointercancel)' });
  });

  it('two fingers moving apart (a pinch) is not a swipe', () => {
    const g = setup();
    g.down(1, 500, 300);
    g.down(2, 520, 300);
    g.advance(100);
    g.up(1, 350, 300);
    g.up(2, 700, 300);
    expect(g.out[0]?.type).toBe('ignored');
  });
});

it('cornerAt finds the four corner zones only', () => {
  expect(cornerAt(10, 10, W, H, 140)).toBe('top-left');
  expect(cornerAt(W - 10, 10, W, H, 140)).toBe('top-right');
  expect(cornerAt(10, H - 10, W, H, 140)).toBe('bottom-left');
  expect(cornerAt(W - 10, H - 10, W, H, 140)).toBe('bottom-right');
  expect(cornerAt(W / 2, 10, W, H, 140)).toBeNull();
});
