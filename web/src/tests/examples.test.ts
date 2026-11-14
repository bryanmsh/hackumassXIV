/**
 * contracts/examples.json is the request/response example for every route that
 * Andrew and Thomas agreed. These tests keep the web app's types, display maps
 * and mocks in step with it: every object the mocks send must have exactly the
 * keys the example has, at every level of nesting.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { ApiError, api } from '../api';
import { scenarios } from '../mocks/db';
import type { Book } from '../types/api';
import { BOOK_STATE_LABEL, CHECK_TONE, LEVELS, PAGE_STATE_LABEL } from '../utils/display';

type Json = null | boolean | number | string | Json[] | { [k: string]: Json };
interface Example {
  request?: Json;
  request_variants?: Json[];
  response: Json;
  errors?: Record<string, Json>;
}

// Tests run from web/, so the repo root is one level up.
const examples = JSON.parse(readFileSync(resolve(process.cwd(), '..', 'contracts', 'examples.json'), 'utf8')) as Record<string, Example> & { _enums: Record<string, (string | number)[]> };

const ex = (route: string): Example => {
  const e = examples[route];
  if (!e) throw new Error(`No example for ${route}`);
  return e;
};

/** Differences in keys and kinds between an example value and an actual one. Nulls are skipped. */
function diff(expected: unknown, actual: unknown, path = '$'): string[] {
  if (expected === null || actual === null || expected === undefined || actual === undefined) return [];
  if (Array.isArray(expected)) {
    if (!Array.isArray(actual)) return [`${path}: expected an array`];
    const first = expected[0];
    if (first === undefined) return [];
    return actual.flatMap((item, i) => diff(first, item, `${path}[${i}]`));
  }
  if (typeof expected === 'object') {
    if (typeof actual !== 'object' || Array.isArray(actual)) return [`${path}: expected an object`];
    const e = expected as Record<string, unknown>;
    const a = actual as Record<string, unknown>;
    const out: string[] = [];
    for (const k of Object.keys(e)) if (!(k in a)) out.push(`${path}.${k}: missing`);
    for (const k of Object.keys(a)) if (!(k in e)) out.push(`${path}.${k}: not in the example`);
    for (const k of Object.keys(e)) if (k in a) out.push(...diff(e[k], a[k], `${path}.${k}`));
    return out;
  }
  return typeof expected === typeof actual ? [] : [`${path}: expected ${typeof expected}, got ${typeof actual}`];
}

async function demo(): Promise<Book> {
  const b = (await api.listBooks()).find((x) => x.title.startsWith('Animal Homes'));
  if (!b) throw new Error('demo book missing');
  return b;
}
const pageNo = (b: Book, n: number) => b.pages.find((p) => p.number === n)!;

describe('enums match contracts/examples.json', () => {
  const enums = examples._enums;
  const sorted = (xs: (string | number)[]) => [...xs].map(String).sort();

  it('page states, book states, levels and check statuses', () => {
    expect(sorted(Object.keys(PAGE_STATE_LABEL))).toEqual(sorted(enums['page.state']!));
    expect(sorted(Object.keys(BOOK_STATE_LABEL))).toEqual(sorted(enums['book.state']!));
    expect(sorted(LEVELS.map((l) => l.value))).toEqual(sorted(enums.level!));
    expect(sorted(Object.keys(CHECK_TONE))).toEqual(sorted(enums['check.status']!));
  });
});

describe('the example bodies the app sends', () => {
  it('subject request variants are the three the client builds', () => {
    const variants = ex('POST /api/pages/{id}/subject').request_variants!;
    expect(variants.map((v) => Object.keys(v as object).sort().join(','))).toEqual(['candidate', 'point', 'label,outline']);
  });

  it('upload uses multipart fields file, title and credits', () => {
    const req = ex('POST /api/books').request as { multipart: Record<string, string> };
    expect(Object.keys(req.multipart).sort()).toEqual(['credits', 'file', 'title']);
  });
});

describe('mock responses have the example shapes', () => {
  it('books: upload, list, get, patch', async () => {
    const up = await api.uploadBook({ file: new File(['%PDF-1.4'], 'new.pdf', { type: 'application/pdf' }) });
    expect(diff(ex('POST /api/books').response, up)).toEqual([]);

    const list = await api.listBooks();
    expect(diff(ex('GET /api/books').response, list)).toEqual([]);

    const b = await demo();
    expect(diff(ex('GET /api/books/{id}').response, await api.getBook(b.id))).toEqual([]);
    expect(diff(ex('PATCH /api/books/{id}').response, await api.updateBook(b.id, { title: 'X' }))).toEqual([]);
  });

  it('pages: retry, subject, confirm, confirm-all, omit', async () => {
    const b = await demo();
    expect(diff(ex('POST /api/pages/{id}/retry').response, await api.retryPage(pageNo(b, 5).id))).toEqual([]);
    const outline: [number, number][] = [
      [0.1, 0.1],
      [0.4, 0.1],
      [0.4, 0.5],
    ];
    expect(diff(ex('POST /api/pages/{id}/subject').response, await api.setSubject(pageNo(b, 3).id, { label: 'bird', outline }))).toEqual(
      [],
    );
    expect(diff(ex('POST /api/pages/{id}/confirm').response, await api.confirmPage(pageNo(b, 1).id))).toEqual([]);
    expect(diff(ex('POST /api/books/{id}/confirm-all').response, await api.confirmAll(b.id))).toEqual([]);
    expect(diff(ex('POST /api/pages/{id}/omit').response, await api.omitPage(pageNo(b, 4).id, true))).toEqual([]);
  });

  it('profiles: list, create, patch', async () => {
    const list = await api.listProfiles();
    expect(diff(ex('GET /api/profiles').response, list)).toEqual([]);
    const created = await api.createProfile(ex('POST /api/profiles').request as never);
    expect(diff(ex('POST /api/profiles').response, created)).toEqual([]);
    expect(diff(ex('PATCH /api/profiles/{id}').response, await api.updateProfile(created.id, { name: 'Ana' }))).toEqual([]);
  });

  it('sheet, approve and its 409 body', async () => {
    const b = await demo();
    const [maya] = await api.listProfiles();
    await api.confirmPage(pageNo(b, 1).id);
    const sheet = await api.getSheet(b.id, { profile: maya!.id, level: 1 });
    expect(diff(ex('GET /api/books/{id}/sheet').response, sheet)).toEqual([]);

    const p1 = sheet.pages.find((p) => p.version)!;
    const body = { profile_id: maya!.id, level: 1 as const, pages: [{ page_id: p1.page_id, version: p1.version!, decision: 'approve' as const }] };
    const ok = await api.approve(b.id, body);
    expect(ok.ok).toBe(true);
    if (ok.ok) expect(diff(ex('POST /api/books/{id}/approve').response, { approvals: ok.approvals })).toEqual([]);

    scenarios.approveConflictNext = true;
    const conflict = await api.approve(b.id, body);
    expect(conflict.ok).toBe(false);
    if (!conflict.ok) expect(diff(ex('POST /api/books/{id}/approve').errors!['409'], conflict.conflict)).toEqual([]);
  });

  it('reader manifest and the 403 body', async () => {
    const backup = (await api.listBooks()).find((x) => x.title.startsWith('The Duck'))!;
    const [maya] = await api.listProfiles();
    const manifest = await api.getReaderManifest(backup.id, { profile: maya!.id, level: 1 });
    expect(diff(ex('GET /api/reader/{book_id}').response, manifest)).toEqual([]);

    const refused = await api
      .getReaderPage(manifest.pages[0]!.page_id, { profile: maya!.id, level: 1, v: '000000000000' })
      .catch((e: unknown) => e);
    expect(refused).toBeInstanceOf(ApiError);
    expect(diff(ex('GET /api/reader/page/{page_id}').errors!['403'], (refused as ApiError).body)).toEqual([]);
  });
});
