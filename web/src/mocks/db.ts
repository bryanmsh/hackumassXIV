/**
 * ⚠️ MOCK BACKEND STATE (development and tests only).
 *
 * An in-memory, stateful imitation of Andrew's API so every screen can be
 * built before the real routes exist. Actions mutate this state; nothing here
 * is used when VITE_API_URL is set or in a production build.
 *
 * The hashing below is a MOCK of the server's behavior. Real hashes and
 * approval tokens are produced only by the backend (contracts/hashing.py);
 * the app itself never computes them.
 */
import type {
  ApprovalRecord,
  ApprovalState,
  Book,
  Candidate,
  CheckItem,
  CheckResult,
  Credits,
  Decision,
  Level,
  NormPoint,
  Page,
  Profile,
  ProfileInput,
  ReaderManifest,
  SecondLook,
  Settings,
  Sheet,
  SheetPage,
  SkippedPage,
} from '../types/api';
import { contrastRatio } from '../utils/contrast';
import { BACKUP_PAGES, DEMO_PAGES, PLACEHOLDER_CREDITS, UPLOAD_PAGES, type PageSpec } from './fixtures/seed';

export const MOCK_RENDER_VERSION = 'mock-r1';

// ---------- Mock hashing (imitates contracts/hashing.py, NOT shared with app code) ----------

function fnv1a(input: string, seed: number): number {
  let h = seed >>> 0;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h >>> 0;
}

export function mockHash(input: string): string {
  const a = fnv1a(input, 0x811c9dc5).toString(16).padStart(8, '0');
  const b = fnv1a(input, 0x2f6b1d37).toString(16).padStart(8, '0');
  return (a + b).slice(0, 12);
}

function sortedJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(sortedJson).join(',')}]`;
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b));
    return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${sortedJson(v)}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export function settingsHash(settings: Settings): string {
  return mockHash(sortedJson(settings));
}

// ---------- State ----------

export interface MockPage extends Page {
  /** When processing finishes (ms epoch), or null when settled. */
  resolveAt: number | null;
  /** What processing will produce. */
  outcome: PageSpec['outcome'];
  /** Bumped to simulate a change made elsewhere (forced 409). Part of the mock token. */
  rev: number;
  secondLookAt: number | null;
  /** Retry was requested with {force: true}. */
  forced: boolean;
}

export interface MockBook extends Omit<Book, 'pages'> {
  readyAt: number | null;
  pages: MockPage[];
}

interface MockApproval extends ApprovalRecord {
  seq: number;
}

export interface Scenarios {
  /** Next approve: mark the first sent page as changed, so it returns 409. */
  approveConflictNext: boolean;
  /** Next reader image request returns 403. */
  readerForbiddenNext: boolean;
  /** Next API request fails as a network error. */
  networkErrorNext: boolean;
  /** Next upload is refused as over 30 pages. */
  uploadTooManyPagesNext: boolean;
  /** Artificial latency per request, ms. */
  latencyMs: number;
}

interface State {
  books: MockBook[];
  profiles: Profile[];
  approvals: MockApproval[];
  outlines: Map<string, NormPoint[]>;
  seq: number;
}

let state: State;

export const scenarios: Scenarios = {
  approveConflictNext: false,
  readerForbiddenNext: false,
  networkErrorNext: false,
  uploadTooManyPagesNext: false,
  latencyMs: 250,
};

function nextId(prefix: string): string {
  state.seq += 1;
  return `${prefix}_${state.seq.toString(36).padStart(4, '0')}`;
}

function withHashes(pageId: string, cands: PageSpec['outcome']['candidates']): Candidate[] {
  return cands.map((c, i) => ({ ...c, synonyms: [...c.synonyms], box: [...c.box], mask_hash: mockHash(`${pageId}:${i}:${c.label}`) }));
}

function makePage(bookId: string, number: number, spec: PageSpec, resolveAt: number | null): MockPage {
  const id = nextId('pg');
  const settled = resolveAt === null;
  const candidates = settled ? withHashes(id, spec.outcome.candidates) : [];
  const selected = settled ? spec.outcome.selected : null;
  if (spec.outlines) {
    for (const [idx, pts] of Object.entries(spec.outlines)) {
      const c = candidates[Number(idx)];
      if (c) state.outlines.set(c.mask_hash, pts);
    }
  }
  return {
    id,
    book_id: bookId,
    number,
    state: settled ? spec.outcome.state : 'processing',
    reason: settled ? spec.outcome.reason : null,
    flags: [...spec.flags],
    page_kind: settled ? spec.outcome.page_kind : null,
    candidates,
    selected,
    subject_hash: selected !== null ? (candidates[selected]?.mask_hash ?? null) : null,
    confirmed: false,
    omitted: false,
    second_look: null,
    text: spec.text,
    width: spec.width,
    height: spec.height,
    resolveAt,
    outcome: spec.outcome,
    rev: 0,
    secondLookAt: null,
    forced: false,
  };
}

function makeBook(
  title: string,
  credits: Credits,
  specs: PageSpec[],
  opts: { createdAt: number; readyAt: number | null; pageDelayMs?: number },
): MockBook {
  const id = nextId('bk');
  const settled = opts.readyAt === null;
  const pages = specs.map((spec, i) =>
    makePage(id, i + 1, spec, settled ? null : (opts.readyAt ?? 0) + (i + 1) * (opts.pageDelayMs ?? 1500)),
  );
  return {
    id,
    title,
    credits: { ...credits },
    state: settled ? 'ready' : 'ingesting',
    page_count: settled ? pages.length : null,
    created_at: new Date(opts.createdAt).toISOString(),
    readyAt: opts.readyAt,
    pages,
  };
}

function makeProfile(input: ProfileInput): Profile {
  return {
    id: nextId('pr'),
    name: input.name,
    level: input.level,
    settings: { ...input.settings, colors: [...input.settings.colors] },
    settings_hash: settingsHash(input.settings),
    contrast_override_note: input.contrast_override_note,
  };
}

const BASE_SETTINGS: Omit<Settings, 'colors' | 'background'> = {
  size: 'medium',
  position: 'center',
  text_mode: 'off',
  outline: 'off',
};

export function resetMockDb(now: number = Date.now()): void {
  state = { books: [], profiles: [], approvals: [], outlines: new Map(), seq: 0 };
  scenarios.approveConflictNext = false;
  scenarios.readerForbiddenNext = false;
  scenarios.networkErrorNext = false;
  scenarios.uploadTooManyPagesNext = false;

  const demo = makeBook('Animal Homes (mock)', PLACEHOLDER_CREDITS, DEMO_PAGES, {
    createdAt: now - 60 * 60 * 1000,
    readyAt: null,
  });
  const backup = makeBook('The Duck (mock backup)', PLACEHOLDER_CREDITS, BACKUP_PAGES, {
    createdAt: now - 2 * 60 * 60 * 1000,
    readyAt: null,
  });
  for (const p of backup.pages) {
    p.confirmed = true;
    p.second_look = { status: 'pass', answer: p.candidates[p.selected ?? 0]?.label ?? null, detail: null };
  }
  const processing = makeBook('Busy Bees (mock, processing)', PLACEHOLDER_CREDITS, UPLOAD_PAGES.slice(0, 4), {
    createdAt: now,
    readyAt: now + 1500,
  });
  state.books.push(processing, demo, backup);

  // Fictional demo children. Leo stays centered with text off until P1 lands.
  const maya = makeProfile({
    name: 'Maya',
    level: 1,
    settings: { ...BASE_SETTINGS, colors: ['#E53935'], background: '#000000' },
    contrast_override_note: null,
  });
  const leo = makeProfile({
    name: 'Leo',
    level: 2,
    settings: { ...BASE_SETTINGS, colors: ['#FDD835', '#1E88E5'], background: '#000000' },
    contrast_override_note: null,
  });
  state.profiles.push(maya, leo);

  // The backup book is approved for Maya / Tinted, so the reader has something to show.
  for (const p of backup.pages) recordDecision(p, maya, 1, 'approve', now - 30 * 60 * 1000);
}

// ---------- Time-based progression ----------

/** Advance processing and second-look jobs. Called at the start of every request. */
export function tick(now: number = Date.now()): void {
  for (const book of state.books) {
    if (book.state === 'ingesting' && book.readyAt !== null && now >= book.readyAt) {
      book.state = 'ready';
      book.page_count = book.pages.length;
    }
    if (book.state !== 'ready') continue;
    for (const p of book.pages) {
      if (p.state === 'processing' && p.resolveAt !== null && now >= p.resolveAt) {
        settlePage(p, p.forced);
        p.forced = false;
      }
      if (p.second_look?.status === 'pending' && p.secondLookAt !== null && now >= p.secondLookAt) {
        const label = p.selected !== null ? (p.candidates[p.selected]?.label ?? '') : '';
        // Mock: the hornbill gets a vaguer answer, to show a warning that never blocks approval.
        p.second_look =
          label === 'hornbill'
            ? { status: 'warn', answer: 'toucan', detail: 'Second look named something else.' }
            : { status: 'pass', answer: label, detail: null };
        p.secondLookAt = null;
      }
    }
  }
}

function settlePage(p: MockPage, force = false): void {
  const o = p.outcome;
  p.resolveAt = null;
  if (o.state === 'unsupported' && force) {
    p.state = 'needs_subject';
    p.page_kind = 'several';
    p.reason = 'Processed anyway; pick the subject.';
    const fresh = withHashes(p.id, [
      { label: 'fish', synonyms: ['sea animal'], box: [0.1, 0.4, 0.3, 0.7], confidence: 0.6, source: 'auto' },
      { label: 'cloud', synonyms: ['sky'], box: [0.65, 0.1, 0.9, 0.35], confidence: 0.55, source: 'auto' },
    ]);
    appendCandidates(p, fresh);
    p.selected = null;
  } else {
    p.state = o.state;
    p.page_kind = o.page_kind;
    p.reason = o.reason;
    appendCandidates(p, withHashes(p.id, o.candidates));
    p.selected = o.selected;
  }
  p.subject_hash = p.selected !== null ? (p.candidates[p.selected]?.mask_hash ?? null) : null;
}

/** Candidates are only ever appended (never replaced), so earlier hashes stay reachable. */
function appendCandidates(p: MockPage, cands: Candidate[]): void {
  for (const c of cands) {
    if (!p.candidates.some((x) => x.mask_hash === c.mask_hash)) p.candidates.push(c);
  }
}

// ---------- Queries ----------

export function publicPage(p: MockPage): Page {
  const { resolveAt: _r, outcome: _o, rev: _v, secondLookAt: _s, forced: _f, ...rest } = p;
  return structuredClone(rest);
}

export function publicBook(b: MockBook): Book {
  const { readyAt: _r, pages, ...rest } = b;
  return { ...structuredClone(rest), pages: b.state === 'ingesting' ? [] : pages.map(publicPage) };
}

export function listBooks(): MockBook[] {
  return [...state.books].sort((a, b) => b.created_at.localeCompare(a.created_at));
}

export function findBook(id: string): MockBook | undefined {
  return state.books.find((b) => b.id === id);
}

export function findPage(id: string): MockPage | undefined {
  for (const b of state.books) {
    if (b.state === 'ingesting') continue;
    const p = b.pages.find((x) => x.id === id);
    if (p) return p;
  }
  return undefined;
}

export function outlineFor(maskHash: string): NormPoint[] | undefined {
  return state.outlines.get(maskHash);
}

export function listProfiles(): Profile[] {
  return state.profiles;
}

export function findProfile(id: string): Profile | undefined {
  return state.profiles.find((p) => p.id === id);
}

export function selectedCandidate(p: Page): Candidate | null {
  return p.selected !== null ? (p.candidates[p.selected] ?? null) : null;
}

// ---------- Mutations ----------

export function createBook(title: string, credits: Credits, now: number = Date.now()): MockBook {
  const book = makeBook(title, credits, UPLOAD_PAGES, { createdAt: now, readyAt: now + 1500 });
  state.books.push(book);
  return book;
}

export function retryPage(p: MockPage, force: boolean, now: number = Date.now()): void {
  if (p.outcome.state === 'failed') {
    // Mock: a retry succeeds and finds one clear subject.
    p.outcome = {
      state: 'ready',
      page_kind: 'single',
      candidates: [
        { label: 'termite mound', synonyms: ['mound'], box: [0.35, 0.2, 0.65, 0.85], confidence: 0.81, source: 'auto' },
      ],
      selected: 0,
      reason: null,
    };
  }
  p.state = 'processing';
  p.reason = null;
  p.resolveAt = now + 2000;
  p.forced = force;
}

function selectNew(p: MockPage, cand: Candidate): void {
  appendCandidates(p, [cand]);
  p.selected = p.candidates.findIndex((c) => c.mask_hash === cand.mask_hash);
  p.subject_hash = cand.mask_hash;
  p.confirmed = false;
  p.second_look = null;
}

export function selectCandidate(p: MockPage, index: number): boolean {
  const c = p.candidates[index];
  if (!c) return false;
  if (p.selected !== index) {
    p.selected = index;
    p.subject_hash = c.mask_hash;
    p.confirmed = false;
    p.second_look = null;
  }
  return true;
}

export function subjectFromPoint(p: MockPage, [x, y]: NormPoint): void {
  const r = 0.12;
  const box: Candidate['box'] = [
    Math.max(0, x - r),
    Math.max(0, y - r),
    Math.min(1, x + r),
    Math.min(1, y + r),
  ];
  selectNew(p, {
    label: 'clicked object',
    synonyms: [],
    box,
    confidence: 1,
    source: 'click',
    mask_hash: mockHash(`${p.id}:click:${x.toFixed(4)},${y.toFixed(4)}`),
  });
}

export function subjectFromOutline(p: MockPage, label: string, outline: NormPoint[]): void {
  const xs = outline.map((pt) => pt[0]);
  const ys = outline.map((pt) => pt[1]);
  const hash = mockHash(`${p.id}:manual:${label}:${outline.map((pt) => pt.join(',')).join(';')}`);
  state.outlines.set(hash, outline.map((pt) => [pt[0], pt[1]]));
  selectNew(p, {
    label,
    synonyms: [],
    box: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)],
    confidence: 1,
    source: 'manual',
    mask_hash: hash,
  });
}

export function confirmPage(p: MockPage, now: number = Date.now()): boolean {
  if (p.selected === null || p.state === 'processing') return false;
  p.confirmed = true;
  if (!p.second_look || p.second_look.status !== 'pass') {
    p.second_look = { status: 'pending', answer: null, detail: null } satisfies SecondLook;
    p.secondLookAt = now + 3000;
  }
  return true;
}

export function createProfile(input: ProfileInput): Profile {
  const p = makeProfile(input);
  state.profiles.push(p);
  return p;
}

export function updateProfile(profile: Profile, patch: Partial<ProfileInput>): Profile {
  if (patch.name !== undefined) profile.name = patch.name;
  if (patch.level !== undefined) profile.level = patch.level;
  if (patch.contrast_override_note !== undefined) profile.contrast_override_note = patch.contrast_override_note;
  if (patch.settings !== undefined) {
    profile.settings = { ...patch.settings, colors: [...patch.settings.colors] };
    profile.settings_hash = settingsHash(profile.settings);
  }
  return profile;
}

// ---------- Versions, checks, approvals ----------

/** Mock version token. Null when the page cannot be shown (no confirmed subject). */
export function currentToken(p: MockPage, profile: Profile, level: Level): string | null {
  if (!p.confirmed || p.subject_hash === null || p.omitted) return null;
  return mockHash([p.subject_hash, profile.settings_hash, level, MOCK_RENDER_VERSION, p.rev].join('|'));
}

function recordDecision(p: MockPage, profile: Profile, level: Level, decision: Decision, at: number): ApprovalRecord | null {
  const version = currentToken(p, profile, level);
  if (!version) return null;
  state.seq += 1;
  const rec: MockApproval = {
    page_id: p.id,
    profile_id: profile.id,
    level,
    version,
    decision,
    at: new Date(at).toISOString(),
    seq: state.seq,
  };
  state.approvals.push(rec);
  const { seq: _s, ...pub } = rec;
  return pub;
}

export function approvalState(p: MockPage, profile: Profile, level: Level): ApprovalState {
  const v = currentToken(p, profile, level);
  if (!v) return 'none';
  let newest: MockApproval | undefined;
  for (const a of state.approvals) {
    if (a.page_id === p.id && a.profile_id === profile.id && a.level === level && a.version === v) {
      if (!newest || a.seq > newest.seq) newest = a;
    }
  }
  if (!newest) return 'none';
  return newest.decision === 'approve' ? 'approved' : 'rejected';
}

function item(status: CheckItem['status'], value: number | null, detail: string): CheckItem {
  return { status, value, detail };
}

export function mockChecks(p: MockPage, profile: Profile, level: Level): CheckResult | null {
  const c = selectedCandidate(p);
  if (!c || !p.confirmed) return null;
  const [x0, y0, x1, y1] = c.box;
  const area = (x1 - x0) * (y1 - y0) * (c.source === 'auto' ? 0.7 : 0.8);
  const touches = x0 <= 0.01 || y0 <= 0.01 || x1 >= 0.99 || y1 >= 0.99;
  const main = profile.settings.colors[0] ?? '#E53935';
  const ratio = contrastRatio(main, profile.settings.background) ?? 21;
  const longSide = Math.max(x1 - x0, y1 - y0);
  const enlarge = 0.6 / Math.max(longSide, 0.01);
  return {
    fidelity:
      area >= 0.01 && area <= 0.6
        ? item('pass', Number(area.toFixed(3)), 'Cut from the original page in one piece.')
        : item('fail', Number(area.toFixed(3)), 'The cut-out covers too little or too much of the page.'),
    page_edge: touches
      ? item('warn', 1, 'The cut-out touches the page edge; the artwork may cut it off.')
      : item('pass', 0, 'The cut-out does not touch the page edge.'),
    background:
      level === 4
        ? null
        : item('pass', 0.002, level === 3 ? 'Background detail is under half the original.' : 'The background is plain.'),
    contrast:
      (level === 1 || level === 4) && ratio < 3
        ? item('warn', Number(ratio.toFixed(2)), `Main color against the background is ${ratio.toFixed(1)}:1, below 3:1.`)
        : item('pass', Number(ratio.toFixed(2)), 'The subject stands out from the background.'),
    size:
      level <= 2
        ? enlarge > 2.5
          ? item('warn', Number(enlarge.toFixed(2)), `Enlarged ${enlarge.toFixed(1)} times; it may look soft.`)
          : item('pass', Number(enlarge.toFixed(2)), 'Enlargement is within range.')
        : longSide < 0.15
          ? item('warn', Number(longSide.toFixed(2)), 'The subject is under 15% of the page and may be hard to find.')
          : item('pass', Number(longSide.toFixed(2)), 'The subject is large enough to find.'),
    text_contrast:
      profile.settings.text_mode === 'below' ? item('pass', 21, 'Text contrast is at least 4.5:1.') : null,
  };
}

export function buildSheet(book: MockBook, profile: Profile, level: Level): Sheet {
  const pages: SheetPage[] = book.pages.map((p) => {
    const c = selectedCandidate(p);
    const version = currentToken(p, profile, level);
    return {
      page_id: p.id,
      number: p.number,
      version,
      state: p.state,
      confirmed: p.confirmed,
      omitted: p.omitted,
      label: c?.label ?? null,
      source: c?.source ?? null,
      checks: mockChecks(p, profile, level),
      second_look: p.second_look ? { ...p.second_look } : null,
      approval: approvalState(p, profile, level),
      preview_url: version
        ? `/api/render/${encodeURIComponent(p.id)}?profile=${encodeURIComponent(profile.id)}&level=${level}&v=${version}`
        : null,
    };
  });
  return { book_id: book.id, profile_id: profile.id, level, render_version: MOCK_RENDER_VERSION, pages };
}

export type ApproveResult =
  | { ok: true; approvals: ApprovalRecord[] }
  | { ok: false; changed: { page_id: string; sent: string; current: string | null }[]; recorded: ApprovalRecord[] };

export function approve(
  book: MockBook,
  profile: Profile,
  level: Level,
  items: { page_id: string; version: string; decision: Decision }[],
  now: number = Date.now(),
): ApproveResult {
  if (scenarios.approveConflictNext && items[0]) {
    scenarios.approveConflictNext = false;
    const target = book.pages.find((p) => p.id === items[0]?.page_id);
    if (target) target.rev += 1; // simulate "changed while the sheet was open"
  }
  const recorded: ApprovalRecord[] = [];
  const changed: { page_id: string; sent: string; current: string | null }[] = [];
  for (const it of items) {
    const p = book.pages.find((x) => x.id === it.page_id);
    const current = p ? currentToken(p, profile, level) : null;
    if (!p || current !== it.version) {
      changed.push({ page_id: it.page_id, sent: it.version, current });
      continue;
    }
    const rec = recordDecision(p, profile, level, it.decision, now);
    if (rec) recorded.push(rec);
  }
  return changed.length ? { ok: false, changed, recorded } : { ok: true, approvals: recorded };
}

/** A version is fully approved when every non-omitted page has a current decision and at least one is approved. */
export function isFullyApproved(book: MockBook, profile: Profile, level: Level): boolean {
  const live = book.pages.filter((p) => !p.omitted);
  if (!live.length) return false;
  const states = live.map((p) => approvalState(p, profile, level));
  return states.every((s) => s !== 'none') && states.includes('approved');
}

export function buildManifest(book: MockBook, profile: Profile, level: Level): ReaderManifest {
  const pages: ReaderManifest['pages'] = [];
  const skipped: SkippedPage[] = [];
  for (const p of book.pages) {
    if (p.omitted) {
      skipped.push({ page_id: p.id, number: p.number, reason: 'omitted' });
      continue;
    }
    const st = approvalState(p, profile, level);
    const v = currentToken(p, profile, level);
    if (st === 'approved' && v) {
      pages.push({
        page_id: p.id,
        number: p.number,
        v,
        image_url: `/api/reader/page/${encodeURIComponent(p.id)}?profile=${encodeURIComponent(profile.id)}&level=${level}&v=${v}`,
      });
    } else {
      skipped.push({ page_id: p.id, number: p.number, reason: st === 'rejected' ? 'rejected' : 'not_approved' });
    }
  }
  const versions: ReaderManifest['versions'] = [];
  for (const pr of state.profiles) {
    for (const lv of [1, 2, 3, 4] as const) {
      versions.push({ profile_id: pr.id, profile_name: pr.name, level: lv, fully_approved: isFullyApproved(book, pr, lv) });
    }
  }
  return {
    book_id: book.id,
    title: book.title,
    profile_id: profile.id,
    level,
    pages,
    skipped,
    credits: { ...book.credits },
    adaptation_note: 'These pages were adapted from the original artwork for display. Changes were made.',
    versions,
  };
}

resetMockDb();
