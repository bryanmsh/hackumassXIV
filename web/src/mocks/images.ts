/**
 * ⚠️ MOCK IMAGES. Labeled SVG placeholders standing in for the server's WebP
 * page, overlay, preview, render and reader images. Every image carries a
 * visible "MOCK" watermark so it can never be mistaken for real output.
 */
import type { Candidate, Level, Settings } from '../types/api';
import { levelName } from '../utils/display';
import { outlineFor, type MockPage } from './db';

const NATURAL = ['#8D6E63', '#F9A825', '#7CB342', '#5D4037', '#00897B', '#6D4C41'];

function esc(s: string): string {
  return s.replace(/[&<>"']/g, (ch) => `&#${ch.charCodeAt(0)};`);
}

function naturalColor(label: string): string {
  let h = 0;
  for (let i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) >>> 0;
  return NATURAL[h % NATURAL.length] ?? '#8D6E63';
}

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** SVG markup for a candidate's shape in page pixel space, plus its bounding box. */
function subjectShape(page: MockPage, c: Candidate, attrs: string): { svg: string; box: Box } {
  const W = page.width;
  const H = page.height;
  const outline = outlineFor(c.mask_hash);
  const [x0, y0, x1, y1] = c.box;
  const box = { x: x0 * W, y: y0 * H, w: (x1 - x0) * W, h: (y1 - y0) * H };
  if (outline && outline.length >= 3) {
    const pts = outline.map(([x, y]) => `${(x * W).toFixed(1)},${(y * H).toFixed(1)}`).join(' ');
    return { svg: `<polygon points="${pts}" ${attrs}/>`, box };
  }
  return {
    svg: `<ellipse cx="${box.x + box.w / 2}" cy="${box.y + box.h / 2}" rx="${box.w / 2}" ry="${box.h / 2}" ${attrs}/>`,
    box,
  };
}

function watermark(W: number, H: number, text: string, fill: string): string {
  const size = Math.round(Math.min(W, H) * 0.035);
  return `<text x="${W - size * 0.6}" y="${H - size * 0.6}" text-anchor="end" font-family="sans-serif" font-size="${size}" font-weight="700" fill="${fill}" opacity="0.85">${esc(text)}</text>`;
}

/** The "original page": paper, some clutter, every auto candidate drawn as a shape, page text. */
function pageBody(page: MockPage): string {
  const W = page.width;
  const H = page.height;
  const parts: string[] = [];
  parts.push(`<rect width="${W}" height="${H}" fill="#F4ECD8"/>`);
  // Clutter: hills, sun and grass strokes, so "background detail" is visible.
  parts.push(`<path d="M0 ${H * 0.78} Q ${W * 0.25} ${H * 0.62} ${W * 0.5} ${H * 0.76} T ${W} ${H * 0.72} V ${H} H 0 Z" fill="#C5E1A5"/>`);
  parts.push(`<circle cx="${W * 0.9}" cy="${H * 0.12}" r="${Math.min(W, H) * 0.06}" fill="#FFE082"/>`);
  for (let i = 0; i < 14; i++) {
    const x = (W / 14) * i + 20;
    parts.push(`<line x1="${x}" y1="${H * 0.95}" x2="${x + 18}" y2="${H * 0.86}" stroke="#7CB342" stroke-width="6"/>`);
  }
  for (const c of page.candidates) {
    if (c.source !== 'auto') continue;
    const { svg, box } = subjectShape(page, c, `fill="${naturalColor(c.label)}" stroke="#3E2723" stroke-width="4"`);
    parts.push(svg);
    parts.push(
      `<text x="${box.x + box.w / 2}" y="${box.y + box.h / 2}" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" font-size="${Math.max(18, Math.min(W, H) * 0.035)}" fill="#fff">${esc(c.label)}</text>`,
    );
  }
  const fs = Math.round(Math.min(W, H) * 0.04);
  parts.push(`<text x="${W * 0.04}" y="${H * 0.08}" font-family="serif" font-size="${fs}" fill="#3E2723">${esc(page.text ?? '')}</text>`);
  return parts.join('');
}

function wrap(W: number, H: number, inner: string): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${inner}</svg>`;
}

/** GET /pages/{id}/overlay — original page with the selected subject highlighted. */
export function overlaySvg(page: MockPage): string {
  const W = page.width;
  const H = page.height;
  const parts = [pageBody(page)];
  const c = page.selected !== null ? page.candidates[page.selected] : undefined;
  if (c) {
    parts.push(`<rect width="${W}" height="${H}" fill="#fff" opacity="0.45"/>`);
    parts.push(subjectShape(page, c, `fill="#E53935" fill-opacity="0.45" stroke="#E53935" stroke-width="8"`).svg);
  }
  parts.push(watermark(W, H, `MOCK page ${page.number}${c ? ` · ${c.label}` : ' · no subject'}`, '#B71C1C'));
  return wrap(W, H, parts.join(''));
}

/** POST /preview, GET /render and GET /reader/page — a mock of the four looks. */
export function renderSvg(page: MockPage, settings: Settings, level: Level, tag: string): string {
  const W = page.width;
  const H = page.height;
  const bg = settings.background;
  const main = settings.colors[0] ?? '#E53935';
  const c = page.selected !== null ? page.candidates[page.selected] : undefined;
  const parts: string[] = [];
  const markFill = bg.toUpperCase() === '#FFFFFF' ? '#B71C1C' : '#FFFFFF';
  if (!c) {
    parts.push(`<rect width="${W}" height="${H}" fill="${bg}"/>`);
  } else if (level === 1 || level === 2) {
    parts.push(`<rect width="${W}" height="${H}" fill="${bg}"/>`);
    const fill = level === 1 ? main : naturalColor(c.label);
    const { svg, box } = subjectShape(page, c, `fill="${fill}"`);
    const text = settings.text_mode === 'below' && page.text?.trim() ? page.text.trim() : null;
    const pictureH = text ? H * 0.84 : H; // bottom 16% is the text band
    const frac = { small: 0.4, medium: 0.6, large: 0.8 }[settings.size];
    const [ax, ay] = { center: [0.5, 0.5], left: [0.3, 0.5], right: [0.7, 0.5], upper: [0.5, 0.3], lower: [0.5, 0.7] }[settings.position] as [number, number];
    const target = frac * Math.min(W, pictureH);
    const s = target / Math.max(box.w, box.h, 1);
    const tx = ax * W - (box.x + box.w / 2) * s;
    const ty = ay * pictureH - (box.y + box.h / 2) * s;
    parts.push(`<g transform="translate(${tx.toFixed(1)} ${ty.toFixed(1)}) scale(${s.toFixed(4)})">${svg}</g>`);
    if (text) {
      const fs = Math.round(H * 0.07);
      parts.push(`<text x="${W / 2}" y="${H * 0.93}" text-anchor="middle" font-family="sans-serif" font-size="${fs}" fill="${markFill}">${esc(text)}</text>`);
    }
  } else if (level === 3) {
    parts.push(`<rect width="${W}" height="${H}" fill="${bg}"/>`);
    parts.push(`<g opacity="0.3">${pageBody(page)}</g>`);
    parts.push(subjectShape(page, c, `fill="${naturalColor(c.label)}" stroke="#3E2723" stroke-width="4"`).svg);
  } else {
    parts.push(pageBody(page));
    parts.push(subjectShape(page, c, `fill="none" stroke="${main}" stroke-width="16"`).svg);
  }
  parts.push(watermark(W, H, `MOCK · ${levelName(level)} · ${tag}`, level >= 3 ? '#B71C1C' : markFill));
  return wrap(W, H, parts.join(''));
}
