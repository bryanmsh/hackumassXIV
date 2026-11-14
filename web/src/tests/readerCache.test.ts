/** Reader image cache: version-keyed, bounded, expiring, never caching a refusal, never revoking what is on screen. */
import { describe, expect, it } from 'vitest';
import { ApiError } from '../api';
import { ReaderImageCache, readerKey } from '../utils/readerCache';

function setup(max = 3, ttl = 1000) {
  let now = 0;
  let n = 0;
  const revoked: string[] = [];
  const cache = new ReaderImageCache(max, ttl, { create: () => `blob:${++n}`, revoke: (u) => revoked.push(u) }, () => now);
  const loads: string[] = [];
  const ok = (name: string) => () => {
    loads.push(name);
    return Promise.resolve(new Blob([name]));
  };
  return { cache, revoked, loads, ok, tick: (ms: number) => (now += ms) };
}

describe('ReaderImageCache', () => {
  it('keys include profile, level, page and the approval token', () => {
    const a = readerKey({ profileId: 'p1', level: 1, pageId: 'g1', v: 'aaa' });
    expect(a).not.toBe(readerKey({ profileId: 'p1', level: 1, pageId: 'g1', v: 'bbb' }));
    expect(a).not.toBe(readerKey({ profileId: 'p1', level: 2, pageId: 'g1', v: 'aaa' }));
    expect(a).not.toBe(readerKey({ profileId: 'p2', level: 1, pageId: 'g1', v: 'aaa' }));
  });

  it('loads once and reuses the image while fresh', async () => {
    const { cache, loads, ok } = setup();
    const u1 = await cache.get('k', ok('k'));
    const u2 = await cache.get('k', ok('k'));
    expect(u1).toBe(u2);
    expect(loads).toEqual(['k']);
  });

  it('never caches a refusal: the next ask goes back to the server', async () => {
    const { cache, loads } = setup();
    const refuse = () => {
      loads.push('x');
      return Promise.reject(new ApiError('http', 'not approved', 403));
    };
    await expect(cache.get('k', refuse)).rejects.toMatchObject({ status: 403 });
    expect(cache.has('k')).toBe(false);
    await expect(cache.get('k', refuse)).rejects.toMatchObject({ status: 403 });
    expect(loads).toEqual(['x', 'x']);
  });

  it('fetches again after the time limit, so the server re-checks approval', async () => {
    const { cache, loads, ok, tick } = setup(3, 1000);
    await cache.get('k', ok('k'));
    tick(1001);
    await cache.get('k', ok('k'));
    expect(loads).toEqual(['k', 'k']);
  });

  it('drops the least recently used image beyond the limit and revokes its URL', async () => {
    const { cache, revoked, ok } = setup(2);
    const a = await cache.get('a', ok('a'));
    await cache.get('b', ok('b'));
    await cache.get('a', ok('a')); // a is now the most recent
    await cache.get('c', ok('c'));
    expect(revoked).toEqual(['blob:2']); // b went
    expect(cache.has('a')).toBe(true);
    expect(a).toBe('blob:1');
  });

  it('never revokes the image on screen; releases it once the screen moves on', async () => {
    const { cache, revoked, ok, tick } = setup(1, 1000);
    const a = await cache.get('a', ok('a'));
    cache.show('a', a);
    await cache.get('b', ok('b')); // over the limit, but a is on screen
    expect(revoked).not.toContain(a);
    tick(2000);
    const a2 = await cache.get('a', ok('a')); // expired: refetched, old URL still on screen
    expect(revoked).not.toContain(a);
    cache.show('a', a2);
    expect(revoked).toContain(a);
  });

  it('clear() revokes everything', async () => {
    const { cache, revoked, ok } = setup();
    const a = await cache.get('a', ok('a'));
    const b = await cache.get('b', ok('b'));
    cache.show('a', a);
    cache.clear();
    expect(revoked.sort()).toEqual([a, b].sort());
    expect(cache.size).toBe(0);
  });
});
