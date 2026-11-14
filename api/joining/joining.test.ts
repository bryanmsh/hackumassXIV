/**
 * The joining check: Thomas's real typed client (web/src/api.ts, imported, never edited) drives the
 * whole demo against a running API. Start it with `bash api/joining/run.sh`.
 */
import { readFileSync } from 'node:fs';
import { ApiError, createApiClient } from '../../web/src/api';

const API = process.env.JOINING_API ?? 'http://127.0.0.1:8765';
const PDF = process.env.JOINING_PDF ?? '';

const MAYA = {
  name: 'Maya',
  level: 1 as const,
  contrast_override_note: null,
  settings: {
    colors: ['#E53935'],
    background: '#000000',
    size: 'medium' as const,
    position: 'center' as const,
    text_mode: 'off' as const,
    outline: 'off' as const,
  },
};
const LEO = {
  ...MAYA,
  name: 'Leo',
  level: 2 as const,
  settings: { ...MAYA.settings, colors: ['#FDD835', '#1E88E5'] },
};

const isImage = (b: unknown) => b instanceof Blob && b.type.startsWith('image/') && b.size > 0;

describe('the demo, step by step, through the web client', () => {
  it('upload, review, profiles, approval and reader', async () => {
    const api = createApiClient(API);

    // 1. Upload
    const file = new File([readFileSync(PDF)], 'book.pdf', { type: 'application/pdf' });
    const upload = await api.uploadBook({ file });
    expect(upload.state).toBe('ingesting');

    // 2. Wait for the pages
    let book = await api.getBook(upload.book_id);
    for (let i = 0; i < 50 && (book.state === 'ingesting' || book.pages.some((p) => p.state === 'processing')); i++) {
      await new Promise((r) => setTimeout(r, 200));
      book = await api.getBook(upload.book_id);
    }
    expect(book.pages.map((p) => p.state)).toEqual(['ready', 'needs_subject', 'failed']);

    // 3. Click a subject on page 2
    const clicked = await api.setSubject(book.pages[1].id, { point: [0.5, 0.5] });
    expect(clicked.state).toBe('ready');
    expect(clicked.candidates[clicked.selected as number].source).toBe('click');

    // 4. Outline a subject on page 3
    const outlined = await api.setSubject(book.pages[2].id, {
      label: 'frog',
      outline: [[0.1, 0.1], [0.5, 0.1], [0.5, 0.4], [0.1, 0.4]],
    });
    expect(outlined.candidates[outlined.selected as number].box).toEqual([0.1, 0.1, 0.5, 0.4]);

    // 5. Overlay
    expect(isImage(await api.getOverlay(book.pages[0].id))).toBe(true);

    // 6. Confirm all
    expect(await api.confirmAll(book.id)).toHaveLength(3);

    // 7. Profiles and an unsaved preview
    const maya = await api.createProfile(MAYA);
    const leo = await api.createProfile(LEO);
    expect(isImage(await api.preview({ page_id: book.pages[0].id, settings: leo.settings, level: 2 }))).toBe(true);

    // 8. The contact sheet and one render
    const sheet = await api.getSheet(book.id, { profile: maya.id, level: 1 });
    expect(sheet.pages).toHaveLength(3);
    sheet.pages.forEach((row) => expect(row.version).toBeTruthy());
    const row = sheet.pages[0];
    expect(isImage(await api.getRender(row.page_id, { profile: maya.id, level: 1, v: row.version as string }))).toBe(true);

    // 9. A stale approval is refused with "look again"
    await api.updateProfile(maya.id, { settings: { ...maya.settings, colors: ['#FDD835'] } });
    const decisions = (s: typeof sheet) =>
      s.pages.map((r) => ({ page_id: r.page_id, version: r.version as string, decision: 'approve' as const }));
    const stale = await api.approve(book.id, { profile_id: maya.id, level: 1, pages: decisions(sheet) });
    expect(stale.ok).toBe(false);
    if (!stale.ok) expect(stale.conflict.changed).toHaveLength(3);

    // 10. Reload and approve
    const fresh = await api.getSheet(book.id, { profile: maya.id, level: 1 });
    const approved = await api.approve(book.id, { profile_id: maya.id, level: 1, pages: decisions(fresh) });
    expect(approved.ok).toBe(true);
    if (approved.ok) expect(approved.approvals).toHaveLength(3);

    // 11. The reader
    const manifest = await api.getReaderManifest(book.id, { profile: maya.id, level: 1 });
    expect(manifest.pages).toHaveLength(3);
    const byName = (name: string) => manifest.versions.find((v) => v.profile_name === name);
    expect(byName('Maya')?.fully_approved).toBe(true);
    expect(byName('Leo')?.fully_approved).toBe(false);
    const first = manifest.pages[0];
    expect(isImage(await api.getReaderPage(first.page_id, { profile: maya.id, level: 1, v: first.v }))).toBe(true);

    // 12. Maya's token does not open Leo's look
    const refused = await api
      .getReaderPage(first.page_id, { profile: leo.id, level: 2, v: first.v })
      .catch((e: unknown) => e);
    expect(refused).toBeInstanceOf(ApiError);
    expect((refused as ApiError).status).toBe(403);
  });
});
