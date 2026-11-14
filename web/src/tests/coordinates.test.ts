/** Screen ⇄ page fractions: the highest-risk math in the app. */
import { describe, expect, it } from 'vitest';
import type { NormPoint } from '../types/api';
import {
  MAX_OUTLINE_POINTS,
  boxToPercent,
  clientToNorm,
  containRect,
  dedupe,
  isValidBox,
  normToClient,
  outlineProblem,
  polygonArea,
  roundPoint,
  simplifyOutline,
} from '../utils/coordinates';

const close = (a: number, b: number, eps = 1e-9) => expect(Math.abs(a - b)).toBeLessThan(eps);

describe('containRect (object-fit: contain)', () => {
  it('fills the box when the shapes match', () => {
    expect(containRect({ left: 0, top: 0, width: 800, height: 600 }, 1600, 1200)).toEqual({ left: 0, top: 0, width: 800, height: 600 });
  });

  it('letterboxes a wide page in a 4:3 box (bands above and below)', () => {
    const r = containRect({ left: 10, top: 20, width: 800, height: 600 }, 3000, 1000);
    close(r.width, 800);
    close(r.height, 800 / 3);
    close(r.left, 10);
    close(r.top, 20 + (600 - 800 / 3) / 2);
  });

  it('pillarboxes a portrait page in a landscape box (bands left and right)', () => {
    const r = containRect({ left: 0, top: 0, width: 1024, height: 600 }, 2250, 3000);
    close(r.height, 600);
    close(r.width, 450);
    close(r.left, (1024 - 450) / 2);
    close(r.top, 0);
  });

  it('works in percentages too (the frame is positioned this way)', () => {
    const r = containRect({ left: 0, top: 0, width: 4, height: 3 }, 16, 9);
    close((r.top / 3) * 100, ((3 - 4 * (9 / 16)) / 2 / 3) * 100);
  });
});

describe('clientToNorm', () => {
  const image = { left: 100, top: 50, width: 800, height: 600 };

  it('maps the corners and center of the drawn image to 0, 1 and 0.5', () => {
    expect(clientToNorm(100, 50, image)).toEqual({ point: [0, 0], inside: true });
    expect(clientToNorm(900, 650, image)).toEqual({ point: [1, 1], inside: true });
    expect(clientToNorm(500, 350, image)).toEqual({ point: [0.5, 0.5], inside: true });
  });

  it('x runs across the width and y down the height', () => {
    const { point } = clientToNorm(100 + 0.25 * 800, 50 + 0.75 * 600, image);
    close(point[0], 0.25);
    close(point[1], 0.75);
  });

  it('marks touches off the image (letterboxing) as outside, clamped only defensively', () => {
    expect(clientToNorm(99, 300, image).inside).toBe(false);
    expect(clientToNorm(500, 651, image).inside).toBe(false);
    expect(clientToNorm(-500, 2000, image).point).toEqual([0, 1]);
  });

  it('gives the same fraction at any scale, offset or device pixel ratio', () => {
    const target: NormPoint = [0.37, 0.61];
    for (const scale of [0.5, 1, 1.5, 2, 3]) {
      for (const offset of [0, 13.5, 240]) {
        const r = { left: offset, top: offset * 2, width: 800 * scale, height: 600 * scale };
        const c = normToClient(target, r);
        const { point, inside } = clientToNorm(c.x, c.y, r);
        expect(inside).toBe(true);
        close(point[0], target[0], 1e-12);
        close(point[1], target[1], 1e-12);
      }
    }
  });

  it('a page letterboxed inside a laptop-size and a tablet-size box gives the same fraction for the same spot', () => {
    const page = { w: 3000, h: 1000 };
    const spot: NormPoint = [0.8, 0.2];
    const results = [
      { left: 0, top: 0, width: 1280, height: 720 },
      { left: 32, top: 90, width: 760, height: 1000 },
    ].map((box) => {
      const drawn = containRect(box, page.w, page.h);
      const c = normToClient(spot, drawn);
      return clientToNorm(c.x, c.y, drawn).point;
    });
    close(results[0]![0], results[1]![0], 1e-12);
    close(results[0]![1], results[1]![1], 1e-12);
  });

  it('refuses a zero-size rectangle', () => {
    expect(clientToNorm(5, 5, { left: 0, top: 0, width: 0, height: 0 }).inside).toBe(false);
  });
});

describe('boxes', () => {
  it('validates order x0 < x1, y0 < y1 within 0..1', () => {
    expect(isValidBox([0.3, 0.4, 0.6, 0.8])).toBe(true);
    expect(isValidBox([0.6, 0.4, 0.3, 0.8])).toBe(false);
    expect(isValidBox([0.3, 0.4, 0.6, 1.2])).toBe(false);
    expect(isValidBox([0.3, 0.4, 0.6])).toBe(false);
  });

  it('turns a box into CSS percentages of the drawn image', () => {
    expect(boxToPercent([0.3, 0.4, 0.6, 0.8])).toEqual({ left: '30.000%', top: '40.000%', width: '30.000%', height: '40.000%' });
  });
});

function circle(n: number, cx = 0.5, cy = 0.5, r = 0.25): NormPoint[] {
  return Array.from({ length: n }, (_, i) => {
    const a = (i / n) * Math.PI * 2;
    return [cx + r * Math.cos(a), cy + r * Math.sin(a)] as NormPoint;
  });
}

describe('simplifyOutline', () => {
  it('thins a long stroke to at most 200 points and keeps its shape', () => {
    const out = simplifyOutline(circle(1500));
    expect(out.length).toBeLessThanOrEqual(MAX_OUTLINE_POINTS);
    expect(out.length).toBeGreaterThanOrEqual(3);
    for (const [x, y] of out) {
      expect(Math.abs(Math.hypot(x - 0.5, y - 0.5) - 0.25)).toBeLessThan(0.005);
    }
    close(Math.abs(polygonArea(out)), Math.PI * 0.25 ** 2, 0.01);
  });

  it('does not repeat the first point at the end (the polygon closes implicitly)', () => {
    const pts = circle(100);
    const out = simplifyOutline([...pts, pts[0]!]);
    expect(out[0]).not.toEqual(out[out.length - 1]);
  });

  it('keeps short strokes as they are, minus near-duplicates', () => {
    expect(dedupe([[0.1, 0.1], [0.1, 0.1005], [0.5, 0.1], [0.5, 0.5]])).toEqual([[0.1, 0.1], [0.5, 0.1], [0.5, 0.5]]);
  });

  it('clamps to 0..1', () => {
    const out = simplifyOutline([[-0.2, 0.5], [0.5, 1.4], [0.9, 0.2]]);
    expect(out).toEqual([[0, 0.5], [0.5, 1], [0.9, 0.2]]);
  });

  it('caps even a jagged stroke that Douglas–Peucker cannot simplify', () => {
    const zigzag: NormPoint[] = Array.from({ length: 2000 }, (_, i) => [(i / 2000) * 0.9 + 0.05, i % 2 ? 0.2 : 0.8]);
    expect(simplifyOutline(zigzag).length).toBeLessThanOrEqual(MAX_OUTLINE_POINTS);
  });
});

describe('outlineProblem', () => {
  it('accepts a real shape', () => {
    expect(outlineProblem(circle(40))).toBeNull();
  });
  it('rejects fewer than three distinct points', () => {
    expect(outlineProblem([[0.1, 0.1], [0.5, 0.5]])).toBe('too_few_points');
    expect(outlineProblem([[0.1, 0.1], [0.1, 0.1], [0.5, 0.5]])).toBe('too_few_points');
  });
  it('rejects a straight line or a tiny scribble', () => {
    expect(outlineProblem([[0.1, 0.1], [0.5, 0.5], [0.9, 0.9]])).toBe('too_small');
    expect(outlineProblem(circle(30, 0.5, 0.5, 0.005))).toBe('too_small');
  });
  it('rejects more than 200 points and anything outside 0..1', () => {
    expect(outlineProblem(circle(201))).toBe('too_many_points');
    expect(outlineProblem([[0.1, 0.1], [1.1, 0.5], [0.5, 0.9]])).toBe('out_of_range');
  });
});

it('roundPoint keeps 5 decimals', () => {
  expect(roundPoint([0.123456789, 0.987654321])).toEqual([0.12346, 0.98765]);
});
