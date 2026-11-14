/**
 * ⚠️ MOCK HANDLERS — one per Contract 1 route, backed by the stateful mock db.
 * Shapes follow contracts/examples.json (checked by tests/examples.test.ts).
 * Patterns start with `*` so they match whatever origin the client uses.
 */
import { delay, http, HttpResponse, type HttpResponseResolver } from 'msw';
import type {
  ApproveRequest,
  Credits,
  Level,
  NormPoint,
  PreviewInput,
  ProfileInput,
  Settings,
  UpdateBookInput,
} from '../types/api';
import * as db from './db';
import { overlaySvg, renderSvg } from './images';

const API = '*/api';
const MAX_BYTES = 50 * 1024 * 1024;

type Resolver = HttpResponseResolver<Record<string, string | readonly string[]>, never>;

/** Common behavior for every mock route: latency, forced network errors, clock tick. */
function route(resolver: Resolver): Resolver {
  return async (info) => {
    if (db.scenarios.latencyMs > 0) await delay(db.scenarios.latencyMs);
    if (db.scenarios.networkErrorNext) {
      db.scenarios.networkErrorNext = false;
      return HttpResponse.error();
    }
    db.tick();
    return resolver(info);
  };
}

const fail = (status: number, detail: string) => HttpResponse.json({ detail }, { status });
const notFound = (what: string) => fail(404, `${what} not found.`);

function image(svg: string): Response {
  return new HttpResponse(svg, {
    headers: { 'Content-Type': 'image/svg+xml', 'Cache-Control': 'no-store' },
  });
}

async function readJson(request: Request): Promise<Record<string, unknown> | null> {
  try {
    const body: unknown = await request.json();
    return body && typeof body === 'object' && !Array.isArray(body) ? (body as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

const param = (v: string | readonly string[] | undefined): string => (Array.isArray(v) ? (v[0] ?? '') : ((v as string) ?? ''));

const isUnit = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n) && n >= 0 && n <= 1;
const isPoint = (p: unknown): p is NormPoint => Array.isArray(p) && p.length === 2 && isUnit(p[0]) && isUnit(p[1]);
const isLevel = (n: unknown): n is Level => n === 1 || n === 2 || n === 3 || n === 4;
const isHex = (s: unknown): s is string => typeof s === 'string' && /^#[0-9a-f]{6}$/i.test(s);

function validSettings(s: unknown): s is Settings {
  if (!s || typeof s !== 'object') return false;
  const o = s as Record<string, unknown>;
  return (
    Array.isArray(o.colors) &&
    o.colors.length >= 1 &&
    o.colors.length <= 3 &&
    o.colors.every(isHex) &&
    isHex(o.background) &&
    ['small', 'medium', 'large'].includes(o.size as string) &&
    ['center', 'left', 'right', 'upper', 'lower'].includes(o.position as string) &&
    ['off', 'below'].includes(o.text_mode as string) &&
    ['off', 'thin', 'thick'].includes(o.outline as string)
  );
}

function levelFrom(url: URL): Level | null {
  const n = Number(url.searchParams.get('level'));
  return isLevel(n) ? n : null;
}

function parseCredits(raw: FormDataEntryValue | null): Credits | 'invalid' {
  const empty: Credits = { author: null, illustrator: null, publisher: null, source: null, license: null };
  if (raw === null || raw === '') return empty;
  if (typeof raw !== 'string') return 'invalid';
  try {
    const obj = JSON.parse(raw) as Record<string, unknown>;
    const pick = (k: keyof Credits) => (typeof obj[k] === 'string' && (obj[k] as string).trim() ? (obj[k] as string).trim() : null);
    return {
      author: pick('author'),
      illustrator: pick('illustrator'),
      publisher: pick('publisher'),
      source: pick('source'),
      license: pick('license'),
    };
  } catch {
    return 'invalid';
  }
}

export const handlers = [
  // ---------------- Books ----------------
  http.get(`${API}/books`, route(() => HttpResponse.json(db.listBooks().map(db.publicBook)))),

  http.post(
    `${API}/books`,
    route(async ({ request }) => {
      let form: FormData;
      try {
        form = await request.formData();
      } catch {
        return fail(422, 'Send the book as multipart form data with a "file" field.');
      }
      const file = form.get('file');
      if (!file || typeof file === 'string') return fail(422, 'Choose a PDF file to upload.');
      const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
      if (!isPdf) return fail(415, 'Only PDF files are supported.');
      if (file.size > MAX_BYTES) return fail(413, 'The PDF is larger than 50 MB.');
      if (db.scenarios.uploadTooManyPagesNext) {
        db.scenarios.uploadTooManyPagesNext = false;
        return fail(422, 'The PDF has 34 pages. Mirai supports up to 30.');
      }
      const credits = parseCredits(form.get('credits'));
      if (credits === 'invalid') return fail(422, 'Credits must be a JSON object.');
      const rawTitle = form.get('title');
      const title =
        typeof rawTitle === 'string' && rawTitle.trim() ? rawTitle.trim() : file.name.replace(/\.pdf$/i, '');
      const book = db.createBook(title, credits);
      return HttpResponse.json({ book_id: book.id, state: book.state }, { status: 201 });
    }),
  ),

  http.get(
    `${API}/books/:id`,
    route(({ params }) => {
      const book = db.findBook(param(params.id));
      return book ? HttpResponse.json(db.publicBook(book)) : notFound('Book');
    }),
  ),

  http.patch(
    `${API}/books/:id`,
    route(async ({ params, request }) => {
      const book = db.findBook(param(params.id));
      if (!book) return notFound('Book');
      const body = (await readJson(request)) as UpdateBookInput | null;
      if (!body) return fail(422, 'Send a JSON body.');
      if (typeof body.title === 'string' && body.title.trim()) book.title = body.title.trim();
      if (body.credits && typeof body.credits === 'object') book.credits = { ...book.credits, ...body.credits };
      return HttpResponse.json(db.publicBook(book));
    }),
  ),

  http.post(
    `${API}/books/:id/confirm-all`,
    route(({ params }) => {
      const book = db.findBook(param(params.id));
      if (!book) return notFound('Book');
      const updated = book.pages.filter((p) => !p.omitted && !p.confirmed && db.confirmPage(p));
      return HttpResponse.json(updated.map(db.publicPage));
    }),
  ),

  http.post(
    `${API}/books/:id/rerun`,
    route(({ params }) => {
      const book = db.findBook(param(params.id));
      if (!book) return notFound('Book');
      const updated = book.pages.filter((p) => db.rerunPage(p));
      return HttpResponse.json(updated.map(db.publicPage));
    }),
  ),

  // ---------------- Pages ----------------
  http.post(
    `${API}/pages/:id/retry`,
    route(async ({ params, request }) => {
      const page = db.findPage(param(params.id));
      if (!page) return notFound('Page');
      const body = (await readJson(request)) ?? {};
      const force = body.force === true;
      if (page.state === 'processing') return fail(409, 'This page is already processing.');
      if (page.state === 'unsupported' && !force) {
        return fail(409, 'This page is Unsupported. Send {"force": true} to process it anyway.');
      }
      db.retryPage(page, force);
      return HttpResponse.json(db.publicPage(page));
    }),
  ),

  http.post(
    `${API}/pages/:id/subject`,
    route(async ({ params, request }) => {
      const page = db.findPage(param(params.id));
      if (!page) return notFound('Page');
      if (page.state === 'processing') return fail(409, 'Wait for this page to finish processing.');
      const body = await readJson(request);
      if (!body) return fail(422, 'Send a JSON body.');
      const keys = Object.keys(body).sort().join(',');
      if (keys === 'candidate') {
        const idx = body.candidate;
        if (typeof idx !== 'number' || !Number.isInteger(idx) || !db.selectCandidate(page, idx)) {
          return fail(422, 'Unknown candidate.');
        }
      } else if (keys === 'candidates') {
        const idxs = body.candidates;
        const valid = Array.isArray(idxs) && idxs.length >= 2 && new Set(idxs).size === idxs.length && idxs.every((i) => Number.isInteger(i));
        if (!valid) return fail(422, 'Showing subjects together needs at least 2 different candidates.');
        if (!db.subjectTogether(page, idxs as number[])) return fail(422, 'Unknown candidate.');
      } else if (keys === 'point') {
        if (!isPoint(body.point)) return fail(422, 'point must be [x, y] fractions between 0 and 1.');
        db.subjectFromPoint(page, body.point);
      } else if (keys === 'label,outline') {
        const label = typeof body.label === 'string' ? body.label.trim() : '';
        const outline = body.outline;
        if (!label) return fail(422, 'Type what the object is.');
        if (!Array.isArray(outline) || !outline.every(isPoint)) {
          return fail(422, 'outline must be a list of [x, y] fractions between 0 and 1.');
        }
        if (outline.length < 3) return fail(422, 'An outline needs at least 3 points.');
        if (outline.length > 200) return fail(422, 'An outline may have at most 200 points.');
        db.subjectFromOutline(page, label, outline);
      } else if (keys === 'refine_point') {
        if (!isPoint(body.refine_point)) return fail(422, 'refine_point must be [x, y] fractions between 0 and 1.');
        if (!db.subjectRefine(page, body.refine_point)) return fail(409, 'This page has no subject to add to. Pick one first.');
      } else {
        return fail(422, 'Send exactly one of {candidate}, {candidates}, {point}, {refine_point} or {label, outline}.');
      }
      return HttpResponse.json(db.publicPage(page));
    }),
  ),

  http.post(
    `${API}/pages/:id/confirm`,
    route(({ params }) => {
      const page = db.findPage(param(params.id));
      if (!page) return notFound('Page');
      if (!db.confirmPage(page)) return fail(409, 'Pick a subject before confirming this page.');
      return HttpResponse.json(db.publicPage(page));
    }),
  ),

  http.post(
    `${API}/pages/:id/omit`,
    route(async ({ params, request }) => {
      const page = db.findPage(param(params.id));
      if (!page) return notFound('Page');
      const body = await readJson(request);
      if (!body || typeof body.omitted !== 'boolean') return fail(422, 'Send {"omitted": true|false}.');
      page.omitted = body.omitted;
      return HttpResponse.json(db.publicPage(page));
    }),
  ),

  http.get(
    `${API}/pages/:id/overlay`,
    route(({ params }) => {
      const page = db.findPage(param(params.id));
      return page ? image(overlaySvg(page)) : notFound('Page');
    }),
  ),

  // ---------------- Profiles and display ----------------
  http.get(`${API}/profiles`, route(() => HttpResponse.json(db.listProfiles()))),

  http.post(
    `${API}/profiles`,
    route(async ({ request }) => {
      const body = (await readJson(request)) as Partial<ProfileInput> | null;
      if (!body || typeof body.name !== 'string' || !body.name.trim()) return fail(422, 'Enter the child’s first name.');
      if (!isLevel(body.level)) return fail(422, 'Choose a look.');
      if (!validSettings(body.settings)) return fail(422, 'Settings are not valid.');
      const profile = db.createProfile({
        name: body.name.trim(),
        level: body.level,
        settings: body.settings,
        contrast_override_note: typeof body.contrast_override_note === 'string' ? body.contrast_override_note : null,
      });
      return HttpResponse.json(profile, { status: 201 });
    }),
  ),

  http.patch(
    `${API}/profiles/:id`,
    route(async ({ params, request }) => {
      const profile = db.findProfile(param(params.id));
      if (!profile) return notFound('Profile');
      const body = (await readJson(request)) as Partial<ProfileInput> | null;
      if (!body) return fail(422, 'Send a JSON body.');
      if (body.name !== undefined && (typeof body.name !== 'string' || !body.name.trim())) {
        return fail(422, 'Enter the child’s first name.');
      }
      if (body.level !== undefined && !isLevel(body.level)) return fail(422, 'Choose a look.');
      if (body.settings !== undefined && !validSettings(body.settings)) return fail(422, 'Settings are not valid.');
      return HttpResponse.json(db.updateProfile(profile, body));
    }),
  ),

  http.post(
    `${API}/preview`,
    route(async ({ request }) => {
      const body = (await readJson(request)) as Partial<PreviewInput> | null;
      if (!body || typeof body.page_id !== 'string') return fail(422, 'Send {page_id, settings, level}.');
      if (!isLevel(body.level) || !validSettings(body.settings)) return fail(422, 'Settings are not valid.');
      const page = db.findPage(body.page_id);
      if (!page) return notFound('Page');
      if (page.selected === null) return fail(409, 'This page has no subject yet.');
      return image(renderSvg(page, body.settings, body.level, 'unsaved preview'));
    }),
  ),

  http.get(
    `${API}/render/:pageId`,
    route(({ params, request }) => {
      const url = new URL(request.url);
      const page = db.findPage(param(params.pageId));
      const profile = db.findProfile(url.searchParams.get('profile') ?? '');
      const level = levelFrom(url);
      if (!page || !profile || !level) return notFound('Version');
      const current = db.currentToken(page, profile, level);
      if (!current || current !== url.searchParams.get('v')) {
        return fail(409, 'This page changed. Reload the contact sheet.');
      }
      return image(renderSvg(page, profile.settings, level, `${profile.name} v=${current}`));
    }),
  ),

  // ---------------- Contact sheet and approval ----------------
  http.get(
    `${API}/books/:id/sheet`,
    route(({ params, request }) => {
      const url = new URL(request.url);
      const book = db.findBook(param(params.id));
      const profile = db.findProfile(url.searchParams.get('profile') ?? '');
      const level = levelFrom(url);
      if (!book) return notFound('Book');
      if (!profile) return notFound('Profile');
      if (!level) return fail(422, 'level must be 1, 2, 3 or 4.');
      return HttpResponse.json(db.buildSheet(book, profile, level));
    }),
  ),

  http.post(
    `${API}/books/:id/approve`,
    route(async ({ params, request }) => {
      const book = db.findBook(param(params.id));
      if (!book) return notFound('Book');
      const body = (await readJson(request)) as Partial<ApproveRequest> | null;
      const profile = db.findProfile(typeof body?.profile_id === 'string' ? body.profile_id : '');
      if (!body || !profile) return notFound('Profile');
      if (!isLevel(body.level)) return fail(422, 'level must be 1, 2, 3 or 4.');
      const items = Array.isArray(body.pages) ? body.pages : [];
      const valid = items.every(
        (it) =>
          it &&
          typeof it.page_id === 'string' &&
          typeof it.version === 'string' &&
          (it.decision === 'approve' || it.decision === 'reject'),
      );
      if (!items.length || !valid) return fail(422, 'Send pages as [{page_id, version, decision}].');
      const result = db.approve(book, profile, body.level, items);
      if (!result.ok) {
        return HttpResponse.json(
          { detail: 'Some pages changed since the sheet was loaded. Look again.', changed: result.changed, recorded: result.recorded },
          { status: 409 },
        );
      }
      return HttpResponse.json({ approvals: result.approvals });
    }),
  ),

  // ---------------- Reader ----------------
  http.get(
    `${API}/reader/:bookId`,
    route(({ params, request }) => {
      const url = new URL(request.url);
      const book = db.findBook(param(params.bookId));
      const profile = db.findProfile(url.searchParams.get('profile') ?? '');
      const level = levelFrom(url);
      // As agreed with Andrew: unknown book or profile is 404; otherwise 200 with a
      // PARTIAL manifest (only approved pages; the rest in `skipped` with a reason).
      if (!book) return notFound('Book');
      if (!profile) return notFound('Profile');
      if (!level) return fail(422, 'level must be 1, 2, 3 or 4.');
      return HttpResponse.json(db.buildManifest(book, profile, level));
    }),
  ),

  http.get(
    `${API}/reader/page/:pageId`,
    route(({ params, request }) => {
      const url = new URL(request.url);
      // As agreed with Andrew: every failure on this route is the same 403 body.
      const refused = () => fail(403, 'not approved');
      if (db.scenarios.readerForbiddenNext) {
        db.scenarios.readerForbiddenNext = false;
        return refused();
      }
      const page = db.findPage(param(params.pageId));
      const profile = db.findProfile(url.searchParams.get('profile') ?? '');
      const level = levelFrom(url);
      if (!page || !profile || !level) return refused();
      const current = db.currentToken(page, profile, level);
      const ok = current !== null && current === url.searchParams.get('v') && db.approvalState(page, profile, level) === 'approved';
      if (!ok) return refused();
      return image(renderSvg(page, profile.settings, level, `reader ${profile.name}`));
    }),
  ),

  // ---------------- P1 ----------------
  http.get(
    `${API}/eval/summary`,
    route(() =>
      HttpResponse.json({
        pages: 20,
        correct_subjects: 0,
        correctly_flagged: 0,
        confidently_wrong: 0,
        cutout_defects: 0,
        seconds_per_page: null,
      }),
    ),
  ),
];
