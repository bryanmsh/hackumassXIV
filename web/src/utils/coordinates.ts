/**
 * Screen ⇄ page positions for the subject editor.
 *
 * Every position sent over HTTP is a fraction in [0, 1] of the ORIGINAL PAGE
 * IMAGE: origin top-left, x across the width, y down the height (FINAL plan).
 * Andrew's API converts to master pixels exactly once; the browser never does,
 * and never divides by master pixels itself.
 *
 * The only screen geometry used is the bounding rectangle of the element that
 * covers exactly the drawn image (see `containRect`), so letterboxing, CSS
 * scaling, responsive size and device pixel ratio do not leak into positions.
 */
import type { NormBox, NormPoint } from '../types/api';

export interface Rect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/** The most vertices an outline may send (spec: thin to at most 200). */
export const MAX_OUTLINE_POINTS = 200;

export const clampUnit = (n: number): number => (n < 0 ? 0 : n > 1 ? 1 : n);

/**
 * Where an image of natural size (nw × nh) is drawn inside a box under
 * `object-fit: contain` (centered). Returned in the box's own units, so it
 * works for pixels or for percentages (pass width = height = 100).
 */
export function containRect(box: Rect, nw: number, nh: number): Rect {
  if (!(nw > 0 && nh > 0 && box.width > 0 && box.height > 0)) return { ...box };
  const scale = Math.min(box.width / nw, box.height / nh);
  const width = nw * scale;
  const height = nh * scale;
  return { left: box.left + (box.width - width) / 2, top: box.top + (box.height - height) / 2, width, height };
}

/**
 * A pointer position (client px) as a page fraction, measured against the
 * drawn image's rectangle (client px, e.g. from getBoundingClientRect).
 * `inside` is false for touches on letterboxing or outside the image.
 */
export function clientToNorm(clientX: number, clientY: number, image: Rect): { point: NormPoint; inside: boolean } {
  if (!(image.width > 0 && image.height > 0)) return { point: [0, 0], inside: false };
  const x = (clientX - image.left) / image.width;
  const y = (clientY - image.top) / image.height;
  const inside = x >= 0 && x <= 1 && y >= 0 && y <= 1;
  return { point: [clampUnit(x), clampUnit(y)], inside };
}

/** A page fraction back to client px over the same drawn image rectangle. */
export function normToClient([x, y]: NormPoint, image: Rect): { x: number; y: number } {
  return { x: image.left + x * image.width, y: image.top + y * image.height };
}

/** True for a usable box: four finite fractions with x0 < x1 and y0 < y1. */
export function isValidBox(box: readonly number[]): box is NormBox {
  if (box.length !== 4 || !box.every((n) => Number.isFinite(n) && n >= 0 && n <= 1)) return false;
  const [x0, y0, x1, y1] = box as NormBox;
  return x0 < x1 && y0 < y1;
}

/** CSS percentages for drawing a box over the drawn image (never over letterboxing). */
export function boxToPercent([x0, y0, x1, y1]: NormBox): { left: string; top: string; width: string; height: string } {
  const pct = (n: number) => `${(n * 100).toFixed(3)}%`;
  return { left: pct(x0), top: pct(y0), width: pct(x1 - x0), height: pct(y1 - y0) };
}

export const boxArea = ([x0, y0, x1, y1]: NormBox): number => (x1 - x0) * (y1 - y0);

// ---------- Outlines ----------

const dist2 = (a: NormPoint, b: NormPoint) => (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2;

/** Squared distance from p to segment ab. */
function segDist2(p: NormPoint, a: NormPoint, b: NormPoint): number {
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const len2 = dx * dx + dy * dy;
  if (len2 === 0) return dist2(p, a);
  const t = Math.max(0, Math.min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2));
  return dist2(p, [a[0] + t * dx, a[1] + t * dy]);
}

/** Ramer–Douglas–Peucker on an open polyline, iterative. */
function rdp(points: NormPoint[], epsilon: number): NormPoint[] {
  if (points.length < 3) return points.slice();
  const keep = new Uint8Array(points.length);
  keep[0] = 1;
  keep[points.length - 1] = 1;
  const eps2 = epsilon * epsilon;
  const stack: [number, number][] = [[0, points.length - 1]];
  while (stack.length) {
    const [s, e] = stack.pop()!;
    let best = -1;
    let bestD = 0;
    for (let i = s + 1; i < e; i++) {
      const d = segDist2(points[i]!, points[s]!, points[e]!);
      if (d > bestD) {
        bestD = d;
        best = i;
      }
    }
    if (best !== -1 && bestD > eps2) {
      keep[best] = 1;
      stack.push([s, best], [best, e]);
    }
  }
  return points.filter((_, i) => keep[i] === 1);
}

/** Drop points closer than `minDist` to the previous kept point, and a last point that repeats the first. */
export function dedupe(points: NormPoint[], minDist = 0.002): NormPoint[] {
  const out: NormPoint[] = [];
  const min2 = minDist * minDist;
  for (const p of points) {
    const last = out[out.length - 1];
    if (!last || dist2(last, p) > min2) out.push([p[0], p[1]]);
  }
  while (out.length > 1 && dist2(out[0]!, out[out.length - 1]!) <= min2) out.pop();
  return out;
}

/**
 * Thin a drawn stroke to at most `max` vertices, keeping its shape: dedupe,
 * then Douglas–Peucker with a growing tolerance, then even sampling as a last
 * resort. The result is an implicitly closed polygon (the last vertex joins
 * the first; the first is not repeated), every value clamped to [0, 1].
 */
export function simplifyOutline(points: NormPoint[], max = MAX_OUTLINE_POINTS): NormPoint[] {
  let pts = dedupe(points.map(([x, y]) => [clampUnit(x), clampUnit(y)] as NormPoint));
  if (pts.length <= max) return pts;
  let eps = 0.0005;
  for (let i = 0; i < 20 && pts.length > max; i++) {
    pts = rdp(pts, eps);
    eps *= 1.6;
  }
  if (pts.length > max) {
    const step = pts.length / max;
    pts = Array.from({ length: max }, (_, i) => pts[Math.floor(i * step)]!);
  }
  return pts;
}

/** Signed area of a closed polygon in page fractions (shoelace). */
export function polygonArea(points: NormPoint[]): number {
  let a = 0;
  for (let i = 0; i < points.length; i++) {
    const [x0, y0] = points[i]!;
    const [x1, y1] = points[(i + 1) % points.length]!;
    a += x0 * y1 - x1 * y0;
  }
  return a / 2;
}

/** Smallest outline accepted: 0.05 % of the page, about a 2 × 2 cm patch on a tablet page. */
export const MIN_OUTLINE_AREA = 0.0005;

export type OutlineProblem = 'too_few_points' | 'too_many_points' | 'out_of_range' | 'too_small';

/** Why an outline cannot be sent, or null when it is fine. */
export function outlineProblem(points: NormPoint[], max = MAX_OUTLINE_POINTS): OutlineProblem | null {
  if (!points.every(([x, y]) => Number.isFinite(x) && Number.isFinite(y) && x >= 0 && x <= 1 && y >= 0 && y <= 1)) {
    return 'out_of_range';
  }
  const distinct = new Set(points.map(([x, y]) => `${x.toFixed(5)},${y.toFixed(5)}`));
  if (distinct.size < 3) return 'too_few_points';
  if (points.length > max) return 'too_many_points';
  if (Math.abs(polygonArea(points)) < MIN_OUTLINE_AREA) return 'too_small';
  return null;
}

export const OUTLINE_PROBLEM_TEXT: Record<OutlineProblem, string> = {
  too_few_points: 'Draw a line all the way around the object.',
  too_many_points: 'The outline has too many points. Clear it and draw again.',
  out_of_range: 'Part of the outline is off the page. Clear it and draw again.',
  too_small: 'The outline is too small or too flat. Draw around the whole object.',
};

/** Round to 5 decimals (about 0.015 px on a 3,000 px master) to keep request bodies short. */
export const roundPoint = ([x, y]: NormPoint): NormPoint => [Math.round(x * 1e5) / 1e5, Math.round(y * 1e5) / 1e5];

/** The axis-aligned box around an outline, in page fractions. */
export function outlineBox(points: NormPoint[]): NormBox {
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

/**
 * True when two boxes are the same shape, within `tol` of the page. Used to tell
 * whether the server tightened a drawn outline to the object (its box moved) or
 * kept the drawing as it was.
 */
export function sameBox(a: readonly number[], b: readonly number[], tol = 0.005): boolean {
  return a.length === 4 && b.length === 4 && a.every((v, i) => Math.abs(v - b[i]!) <= tol);
}
