/**
 * The only module that talks to the server. Every Contract 1 route has exactly
 * one function here; screens never call fetch directly.
 *
 * - Routes are built in one place with exactly one `/api` prefix.
 * - Errors are normalized into ApiError (http / network / aborted / invalid_response).
 * - 409 from approve is an expected outcome ("look again"), not an exception.
 * - 401/403 are surfaced as real server answers; there are no bypasses.
 * - Images come back as Blobs with `cache: 'no-store'`, matching the server's
 *   Cache-Control. Callers own the object URLs they create.
 * - Hashes and approval tokens are never generated here; they are only echoed.
 */
import { API_BASE } from './config';
import type {
  ApproveConflictBody,
  ApproveOutcome,
  ApproveRequest,
  ApproveSuccessBody,
  Book,
  ErrorBody,
  EvalSummary,
  Level,
  Page,
  PreviewInput,
  Profile,
  ProfileInput,
  ProfilePatch,
  ReaderManifest,
  RetryInput,
  Sheet,
  SheetQuery,
  SubjectRequest,
  UpdateBookInput,
  UploadBookInput,
  UploadBookResponse,
  VersionQuery,
} from './types/api';

// ---------- Limits shown to the teacher (the backend enforces them) ----------

export const MAX_UPLOAD_BYTES = 50 * 1024 * 1024;
export const MAX_UPLOAD_PAGES = 30;

// ---------- Errors ----------

export type ApiErrorKind = 'http' | 'network' | 'aborted' | 'invalid_response';

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number | null;
  readonly body: unknown;

  constructor(kind: ApiErrorKind, message: string, status: number | null = null, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.body = body;
  }
}

export function isAbortError(err: unknown): boolean {
  return (
    (err instanceof ApiError && err.kind === 'aborted') ||
    (err instanceof DOMException && err.name === 'AbortError')
  );
}

function defaultMessage(status: number): string {
  if (status === 401) return 'The site password is needed. Reload the page and sign in.';
  if (status === 403) return 'The server refused this request.';
  if (status === 404) return 'Not found on the server.';
  if (status === 405) return 'This server does not support that action yet.';
  if (status === 409) return 'Something changed on the server. Look again.';
  if (status === 413) return 'The file is too large for the server.';
  if (status === 422) return 'The server could not accept this request.';
  if (status >= 500) return 'The server had a problem. Try again.';
  return 'The server could not handle this request. Try again.';
}

/** Pull a readable message out of a FastAPI-style `{detail}` body. */
export function messageFromBody(status: number, body: unknown): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as ErrorBody).detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((d) => (d && typeof d === 'object' && typeof d.msg === 'string' ? d.msg : null))
        .filter((m): m is string => Boolean(m));
      if (msgs.length) return msgs.join('; ');
    }
  }
  if (typeof body === 'string' && body.trim() && body.length < 300) return body.trim();
  return defaultMessage(status);
}

// ---------- URL building ----------

/** Strip trailing slashes and a trailing `/api`, so the prefix is added exactly once. */
export function normalizeBase(base: string): string {
  let b = base.trim();
  if (b === '' || b === '/') return '';
  b = b.replace(/\/+$/, '');
  if (b.toLowerCase().endsWith('/api')) b = b.slice(0, -4);
  return b.replace(/\/+$/, '');
}

type QueryValue = string | number | boolean | null | undefined;

export function buildApiUrl(base: string, path: string, query?: Record<string, QueryValue>): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  let url = `${normalizeBase(base)}/api${p}`;
  if (query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null) params.append(k, String(v));
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }
  return url;
}

const seg = (id: string) => encodeURIComponent(id);

// ---------- Core request ----------

type Body = { json: unknown } | { form: FormData } | undefined;

interface RequestOptions {
  query?: Record<string, QueryValue>;
  body?: Body;
  signal?: AbortSignal;
}

export function createApiClient(base: string = API_BASE) {
  function absolute(url: string): string {
    // Relative URLs are fine in browsers; resolving them keeps jsdom/Node happy too.
    const origin = typeof window !== 'undefined' ? window.location.href : 'http://localhost/';
    return new URL(url, origin).toString();
  }

  async function send(method: string, path: string, opts: RequestOptions = {}): Promise<Response> {
    const url = absolute(buildApiUrl(base, path, opts.query));
    const headers: Record<string, string> = { Accept: 'application/json, image/*;q=0.9' };
    let payload: BodyInit | undefined;
    if (opts.body && 'json' in opts.body) {
      headers['Content-Type'] = 'application/json';
      payload = JSON.stringify(opts.body.json);
    } else if (opts.body && 'form' in opts.body) {
      payload = opts.body.form; // browser sets the multipart boundary
    }
    try {
      return await fetch(url, {
        method,
        headers,
        body: payload,
        signal: opts.signal,
        cache: 'no-store',
        credentials: 'same-origin',
      });
    } catch (err) {
      if (opts.signal?.aborted || (err instanceof DOMException && err.name === 'AbortError')) {
        throw new ApiError('aborted', 'Request cancelled.');
      }
      throw new ApiError('network', 'Could not reach the server. Check the connection and try again.');
    }
  }

  async function readBody(res: Response): Promise<unknown> {
    const text = await res.text();
    if (!text) return undefined;
    try {
      return JSON.parse(text) as unknown;
    } catch {
      return text;
    }
  }

  async function failure(res: Response): Promise<ApiError> {
    const body = await readBody(res).catch(() => undefined);
    return new ApiError('http', messageFromBody(res.status, body), res.status, body);
  }

  /** A request whose success answer has no body (204, or 200 with nothing to read). */
  async function empty(method: string, path: string, opts: RequestOptions = {}): Promise<void> {
    const res = await send(method, path, opts);
    if (!res.ok) throw await failure(res);
  }

  async function json<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
    const res = await send(method, path, opts);
    if (!res.ok) throw await failure(res);
    const body = await readBody(res);
    if (body === undefined || typeof body === 'string') {
      throw new ApiError('invalid_response', 'The server sent an unexpected response.', res.status, body);
    }
    return body as T;
  }

  async function blob(method: string, path: string, opts: RequestOptions = {}): Promise<Blob> {
    const res = await send(method, path, opts);
    if (!res.ok) throw await failure(res);
    const b = await res.blob();
    const type = res.headers.get('Content-Type') ?? b.type;
    if (type && !type.startsWith('image/')) {
      throw new ApiError('invalid_response', 'The server did not send an image.', res.status);
    }
    return b;
  }

  const versionQuery = (q: VersionQuery) => ({ profile: q.profile, level: q.level, v: q.v });

  return {
    base,
    url: (path: string, query?: Record<string, QueryValue>) => buildApiUrl(base, path, query),

    // ----- Books -----
    listBooks: (signal?: AbortSignal) => json<Book[]>('GET', '/books', { signal }),

    getBook: (bookId: string, signal?: AbortSignal) =>
      json<Book>('GET', `/books/${seg(bookId)}`, { signal }),

    uploadBook: (input: UploadBookInput, signal?: AbortSignal) => {
      const form = new FormData();
      form.append('file', input.file, input.file.name);
      // As agreed in contracts/examples.json: title as its own field, credits as one JSON string.
      if (input.title?.trim()) form.append('title', input.title.trim());
      if (input.credits) form.append('credits', JSON.stringify(input.credits));
      return json<UploadBookResponse>('POST', '/books', { body: { form }, signal });
    },

    /** Remove a book with its pages, checks and approvals (additive route, agreed with Andrew). */
    deleteBook: (bookId: string, signal?: AbortSignal) => empty('DELETE', `/books/${seg(bookId)}`, { signal }),

    updateBook: (bookId: string, input: UpdateBookInput, signal?: AbortSignal) =>
      json<Book>('PATCH', `/books/${seg(bookId)}`, { body: { json: input }, signal }),

    confirmAll: (bookId: string, signal?: AbortSignal) =>
      json<Page[]>('POST', `/books/${seg(bookId)}/confirm-all`, { signal }),
    /** Ask the AI again about every page not left out or processing. Returns those pages. */
    rerunBook: (bookId: string, signal?: AbortSignal) =>
      json<Page[]>('POST', `/books/${seg(bookId)}/rerun`, { signal }),

    // ----- Pages -----
    retryPage: (pageId: string, input: RetryInput = {}, signal?: AbortSignal) =>
      json<Page>('POST', `/pages/${seg(pageId)}/retry`, { body: { json: input }, signal }),

    setSubject: (pageId: string, body: SubjectRequest, signal?: AbortSignal) =>
      json<Page>('POST', `/pages/${seg(pageId)}/subject`, { body: { json: body }, signal }),

    confirmPage: (pageId: string, signal?: AbortSignal) =>
      json<Page>('POST', `/pages/${seg(pageId)}/confirm`, { signal }),

    omitPage: (pageId: string, omitted: boolean, signal?: AbortSignal) =>
      json<Page>('POST', `/pages/${seg(pageId)}/omit`, { body: { json: { omitted } }, signal }),

    // palette=1 asks for every suggestion tinted in its own colour (additive query;
    // a server without it ignores the parameter and sends the one-colour overlay).
    getOverlay: (pageId: string, signal?: AbortSignal) =>
      blob('GET', `/pages/${seg(pageId)}/overlay`, { query: { palette: 1 }, signal }),

    // ----- Profiles and display -----
    listProfiles: (signal?: AbortSignal) => json<Profile[]>('GET', '/profiles', { signal }),

    createProfile: (input: ProfileInput, signal?: AbortSignal) =>
      json<Profile>('POST', '/profiles', { body: { json: input }, signal }),

    updateProfile: (profileId: string, patch: ProfilePatch, signal?: AbortSignal) =>
      json<Profile>('PATCH', `/profiles/${seg(profileId)}`, { body: { json: patch }, signal }),

    /** Unsaved settings only. Stores nothing on the server. */
    preview: (input: PreviewInput, signal?: AbortSignal) =>
      blob('POST', '/preview', { body: { json: input }, signal }),

    /** Teacher screens only. The Reader must never call this. */
    getRender: (pageId: string, q: VersionQuery, signal?: AbortSignal) =>
      blob('GET', `/render/${seg(pageId)}`, { query: versionQuery(q), signal }),

    // ----- Approval -----
    getSheet: (bookId: string, q: SheetQuery, signal?: AbortSignal) =>
      json<Sheet>('GET', `/books/${seg(bookId)}/sheet`, {
        query: { profile: q.profile, level: q.level },
        signal,
      }),

    /** Sends each version exactly as received. A 409 resolves as `{ok: false}`. */
    approve: async (bookId: string, body: ApproveRequest, signal?: AbortSignal): Promise<ApproveOutcome> => {
      const res = await send('POST', `/books/${seg(bookId)}/approve`, { body: { json: body }, signal });
      if (res.status === 409) {
        const raw = (await readBody(res)) as Partial<ApproveConflictBody> | undefined;
        return {
          ok: false,
          conflict: {
            detail: typeof raw?.detail === 'string' ? raw.detail : defaultMessage(409),
            changed: Array.isArray(raw?.changed) ? raw.changed : [],
            recorded: Array.isArray(raw?.recorded) ? raw.recorded : [],
          },
        };
      }
      if (!res.ok) throw await failure(res);
      const ok = (await readBody(res)) as Partial<ApproveSuccessBody> | undefined;
      return { ok: true, approvals: Array.isArray(ok?.approvals) ? ok.approvals : [] };
    },

    // ----- Reader (the only routes the Reader may use) -----
    getReaderManifest: (bookId: string, q: { profile: string; level: Level }, signal?: AbortSignal) =>
      json<ReaderManifest>('GET', `/reader/${seg(bookId)}`, {
        query: { profile: q.profile, level: q.level },
        signal,
      }),

    /** 403 (ApiError status 403) when `v` is stale or not approved. Never fall back. */
    getReaderPage: (pageId: string, q: VersionQuery, signal?: AbortSignal) =>
      blob('GET', `/reader/page/${seg(pageId)}`, { query: versionQuery(q), signal }),

    // ----- P1 -----
    getEvalSummary: (signal?: AbortSignal) => json<EvalSummary>('GET', '/eval/summary', { signal }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;

export const api: ApiClient = createApiClient();
