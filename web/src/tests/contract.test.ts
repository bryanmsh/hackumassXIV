/**
 * Every Contract 1 route is called through api.ts against the mock server.
 * setup.ts uses onUnhandledRequest: 'error', so a route without a mock fails.
 */
import { http } from 'msw';
import { describe, expect, it } from 'vitest';
import { ApiError, api } from '../api';
import { server } from '../mocks/node';
import type { Book, Profile } from '../types/api';
import { DEFAULT_SETTINGS } from '../utils/display';

async function demo(): Promise<Book> {
  const books = await api.listBooks();
  const b = books.find((x) => x.title.startsWith('Animal Homes'));
  if (!b) throw new Error('demo book missing');
  return b;
}

const pageNo = (b: Book, n: number) => {
  const p = b.pages.find((x) => x.number === n);
  if (!p) throw new Error(`page ${n} missing`);
  return p;
};

/** Record JSON bodies sent to a route, then fall through to the mock handler. */
function captureBodies(method: 'post' | 'patch', path: string): unknown[] {
  const bodies: unknown[] = [];
  server.use(
    http[method](path, async ({ request }) => {
      bodies.push(await request.clone().json());
      return undefined;
    }),
  );
  return bodies;
}

describe('Contract 1 mock coverage', () => {
  it('books: list, get, patch', async () => {
    const b = await demo();
    expect(b.pages).toHaveLength(6);
    expect(new Set(b.pages.map((p) => p.state))).toEqual(
      new Set(['ready', 'needs_subject', 'no_clear_subject', 'failed', 'unsupported']),
    );
    const got = await api.getBook(b.id);
    expect(got.id).toBe(b.id);
    const patched = await api.updateBook(b.id, { title: 'Renamed', credits: { license: 'CC BY 4.0' } });
    expect(patched.title).toBe('Renamed');
  });

  it('upload route exists and returns a book id', async () => {
    // jsdom's FormData cannot be serialized by Node fetch, so stub the transport here
    // and only assert the client's call shape. Upload UI tests come with D2.
    const bodies: string[] = [];
    server.use(
      http.post('*/api/books', ({ request }) => {
        bodies.push(request.headers.get('content-type') ?? '');
        return Response.json({ book_id: 'bk_new', state: 'ingesting' }, { status: 201 });
      }),
    );
    const res = await api.uploadBook({ file: new File(['%PDF-1.4'], 'a.pdf', { type: 'application/pdf' }) });
    expect(res).toEqual({ book_id: 'bk_new', state: 'ingesting' });
    expect(bodies).toHaveLength(1);
  });

  it('pages: subject by candidate, point and outline use the agreed bodies with 0-1 positions', async () => {
    const b = await demo();
    const p3 = pageNo(b, 3);
    const bodies = captureBodies('post', '*/api/pages/:id/subject');

    let page = await api.setSubject(p3.id, { candidate: 1 });
    expect(page.selected).toBe(1);

    page = await api.setSubject(p3.id, { point: [0.25, 0.4] });
    expect(page.candidates[page.selected ?? -1]?.source).toBe('click');

    const outline: [number, number][] = [
      [0.1, 0.1],
      [0.3, 0.1],
      [0.3, 0.4],
      [0.1, 0.4],
    ];
    page = await api.setSubject(p3.id, { label: 'hornbill', outline });
    const sel = page.candidates[page.selected ?? -1];
    expect(sel?.source).toBe('manual');
    expect(sel?.label).toBe('hornbill');
    expect(page.confirmed).toBe(false);

    expect(bodies).toEqual([{ candidate: 1 }, { point: [0.25, 0.4] }, { label: 'hornbill', outline }]);
    for (const n of [...(bodies[1] as { point: number[] }).point, ...outline.flat()]) {
      expect(n).toBeGreaterThanOrEqual(0);
      expect(n).toBeLessThanOrEqual(1);
    }
  });

  it('pages: mock rejects out-of-range points and degenerate outlines', async () => {
    const p3 = pageNo(await demo(), 3);
    await expect(api.setSubject(p3.id, { point: [1.2, 0.5] })).rejects.toMatchObject({ status: 422 });
    await expect(
      api.setSubject(p3.id, { label: 'x', outline: [[0.1, 0.1], [0.2, 0.2]] }),
    ).rejects.toMatchObject({ status: 422 });
  });

  it('pages: confirm, confirm-all, omit, retry (incl. force), overlay', async () => {
    const b = await demo();
    const confirmed = await api.confirmPage(pageNo(b, 1).id);
    expect(confirmed.confirmed).toBe(true);
    expect(confirmed.second_look?.status).toBe('pending');

    const all = await api.confirmAll(b.id);
    expect(all.map((p) => p.number)).toEqual([2]);

    const omitted = await api.omitPage(pageNo(b, 4).id, true);
    expect(omitted.omitted).toBe(true);

    const retried = await api.retryPage(pageNo(b, 5).id);
    expect(retried.state).toBe('processing');

    await expect(api.retryPage(pageNo(b, 6).id)).rejects.toMatchObject({ status: 409 });
    const forced = await api.retryPage(pageNo(b, 6).id, { force: true });
    expect(forced.state).toBe('processing');

    const overlay = await api.getOverlay(pageNo(b, 1).id);
    expect(overlay.type).toMatch(/^image\//);
  });

  it('profiles: list, create, patch, preview; render needs the exact version', async () => {
    const profiles = await api.listProfiles();
    expect(profiles.map((p) => p.name)).toEqual(['Maya', 'Leo']);
    const created: Profile = await api.createProfile({
      name: 'Ana',
      level: 3,
      settings: { ...DEFAULT_SETTINGS, colors: ['#43A047'] },
      contrast_override_note: null,
    });
    expect(created.settings_hash).toMatch(/^[0-9a-f]{12}$/);
    const renamed = await api.updateProfile(created.id, { name: 'Ana B' });
    expect(renamed.settings_hash).toBe(created.settings_hash);

    const b = await demo();
    const img = await api.preview({ page_id: pageNo(b, 1).id, settings: created.settings, level: 1 });
    expect(img.type).toMatch(/^image\//);
  });

  it('sheet + approve echo exact versions; a changed page returns 409 "look again"', async () => {
    const b = await demo();
    const [maya] = await api.listProfiles();
    if (!maya) throw new Error('no Maya');
    await api.confirmPage(pageNo(b, 1).id);
    await api.confirmPage(pageNo(b, 2).id);

    const sheet = await api.getSheet(b.id, { profile: maya.id, level: 1 });
    const live = sheet.pages.filter((p) => p.version);
    expect(live.map((p) => p.number)).toEqual([1, 2]);

    const render = await api.getRender(live[0]!.page_id, { profile: maya.id, level: 1, v: live[0]!.version! });
    expect(render.type).toMatch(/^image\//);

    const bodies = captureBodies('post', '*/api/books/:id/approve');
    const ok = await api.approve(b.id, {
      profile_id: maya.id,
      level: 1,
      pages: live.map((p) => ({ page_id: p.page_id, version: p.version!, decision: 'approve' as const })),
    });
    expect(ok.ok).toBe(true);
    expect((bodies[0] as { pages: { version: string }[] }).pages.map((x) => x.version)).toEqual(live.map((p) => p.version));

    // Change the subject of page 1 after the sheet was loaded, then approve the stale version.
    await api.setSubject(pageNo(b, 1).id, { point: [0.5, 0.5] });
    await api.confirmPage(pageNo(b, 1).id);
    const stale = await api.approve(b.id, {
      profile_id: maya.id,
      level: 1,
      pages: [{ page_id: live[0]!.page_id, version: live[0]!.version!, decision: 'approve' }],
    });
    expect(stale.ok).toBe(false);
    if (!stale.ok) expect(stale.conflict.changed.map((c) => c.page_id)).toEqual([live[0]!.page_id]);
  });

  it('reader: manifest and image for an approved version; 403 for anything else', async () => {
    const books = await api.listBooks();
    const backup = books.find((x) => x.title.startsWith('The Duck'))!;
    const [maya, leo] = await api.listProfiles();
    const manifest = await api.getReaderManifest(backup.id, { profile: maya!.id, level: 1 });
    expect(manifest.pages).toHaveLength(3);
    expect(manifest.credits.license).toBe('CC BY 4.0');
    expect(manifest.versions.find((v) => v.profile_id === leo!.id && v.level === 2)?.fully_approved).toBe(false);

    const first = manifest.pages[0]!;
    const img = await api.getReaderPage(first.page_id, { profile: maya!.id, level: 1, v: first.v });
    expect(img.type).toMatch(/^image\//);

    const wrongV = await api.getReaderPage(first.page_id, { profile: maya!.id, level: 1, v: '000000000000' }).catch((e: unknown) => e);
    expect((wrongV as ApiError).status).toBe(403);
    const otherLook = await api.getReaderPage(first.page_id, { profile: maya!.id, level: 2, v: first.v }).catch((e: unknown) => e);
    expect((otherLook as ApiError).status).toBe(403);
    await expect(api.getReaderManifest(backup.id, { profile: leo!.id, level: 2 })).rejects.toMatchObject({ status: 403 });

    // Profile edit invalidates the approval: same v is now refused.
    await api.updateProfile(maya!.id, { settings: { ...maya!.settings, background: '#FFFFFF' } });
    const afterEdit = await api.getReaderPage(first.page_id, { profile: maya!.id, level: 1, v: first.v }).catch((e: unknown) => e);
    expect((afterEdit as ApiError).status).toBe(403);
    // Switching back restores it.
    await api.updateProfile(maya!.id, { settings: maya!.settings });
    await expect(api.getReaderPage(first.page_id, { profile: maya!.id, level: 1, v: first.v })).resolves.toBeInstanceOf(Blob);
  });

  it('eval summary (P1) has a mock', async () => {
    const s = await api.getEvalSummary();
    expect(s.pages).toBe(20);
  });
});
