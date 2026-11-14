/**
 * In-memory cache of reader page images (Blobs as object URLs).
 *
 * The server sends `Cache-Control: no-store`, so the browser cache cannot make
 * page turns fast; this cache does, within limits that keep it safe:
 * - Keys are profile + level + page + approval token `v`. A changed or revoked
 *   approval gets a new `v` (or none), so an old image is never reused for it.
 * - Entries expire after `ttlMs`; after that the image is fetched again, which
 *   makes the server re-check the approval.
 * - A failed fetch (e.g. 403) is never cached.
 * - At most `max` entries; the least recently used is dropped and its object
 *   URL revoked. The on-screen image is never revoked while shown.
 */

export interface ReaderKeyParts {
  profileId: string;
  level: number;
  pageId: string;
  v: string;
}

export const readerKey = ({ profileId, level, pageId, v }: ReaderKeyParts): string => `${profileId}|${level}|${pageId}|${v}`;

interface Entry {
  promise: Promise<string>;
  url: string | null;
  at: number;
}

export interface UrlApi {
  create: (b: Blob) => string;
  revoke: (url: string) => void;
}

const browserUrls: UrlApi = {
  create: (b) => URL.createObjectURL(b),
  revoke: (u) => URL.revokeObjectURL(u),
};

export class ReaderImageCache {
  private entries = new Map<string, Entry>();
  /** Object URLs no longer in the cache that may still be on screen; revoked once replaced. */
  private retired = new Set<string>();
  private pinnedKey: string | null = null;
  private shownUrl: string | null = null;
  /** Bumped by clear(); loads started before it are released when they land. */
  private generation = 0;

  constructor(
    private readonly max = 16,
    private readonly ttlMs = 120_000,
    private readonly urls: UrlApi = browserUrls,
    private readonly now: () => number = () => Date.now(),
  ) {}

  /** The object URL for `key`, fetching with `load` if missing or expired. Rejects on any load error. */
  get(key: string, load: () => Promise<Blob>): Promise<string> {
    const hit = this.entries.get(key);
    if (hit && this.now() - hit.at < this.ttlMs) {
      this.entries.delete(key); // refresh recency
      this.entries.set(key, hit);
      return hit.promise;
    }
    if (hit) this.drop(key, true); // expired: fetch again so the server re-checks approval

    const entry: Entry = { promise: Promise.resolve(''), url: null, at: this.now() };
    const generation = this.generation;
    entry.promise = load().then(
      (blob) => {
        const url = this.urls.create(blob);
        if (generation !== this.generation) {
          // Cleared while loading (unmount, or React's development double mount): nobody shows this.
          this.urls.revoke(url);
          return url;
        }
        if (this.entries.get(key) === entry) entry.url = url;
        else this.retired.add(url); // evicted while loading; released at the next swap
        return url;
      },
      (err: unknown) => {
        if (this.entries.get(key) === entry) this.entries.delete(key);
        throw err;
      },
    );
    this.entries.set(key, entry);
    this.trim();
    return entry.promise;
  }

  /** Fetch ahead without caring about the result. */
  prefetch(key: string, load: () => Promise<Blob>): void {
    this.get(key, load).catch(() => undefined);
  }

  /**
   * Tell the cache what is on screen now (or nothing). That entry is never
   * evicted, and URLs that were waiting for the screen to move on are revoked.
   */
  show(key: string | null, url: string | null): void {
    this.pinnedKey = key;
    this.shownUrl = url;
    for (const u of [...this.retired]) {
      if (u !== url) {
        this.urls.revoke(u);
        this.retired.delete(u);
      }
    }
  }

  has(key: string): boolean {
    const e = this.entries.get(key);
    return e !== undefined && this.now() - e.at < this.ttlMs;
  }

  get size(): number {
    return this.entries.size;
  }

  /**
   * Drop everything and revoke every object URL (on unmount). The cache stays
   * usable afterwards, because React's development mode mounts twice.
   */
  clear(): void {
    this.generation += 1;
    for (const e of this.entries.values()) if (e.url) this.urls.revoke(e.url);
    for (const u of this.retired) this.urls.revoke(u);
    this.entries.clear();
    this.retired.clear();
    this.pinnedKey = null;
    this.shownUrl = null;
  }

  private trim() {
    for (const key of this.entries.keys()) {
      if (this.entries.size <= this.max) break;
      if (key !== this.pinnedKey) this.drop(key);
    }
  }

  private drop(key: string, evenIfPinned = false) {
    const e = this.entries.get(key);
    if (!e || (!evenIfPinned && key === this.pinnedKey)) return;
    this.entries.delete(key);
    if (!e.url) return;
    if (e.url === this.shownUrl) this.retired.add(e.url);
    else this.urls.revoke(e.url);
  }
}
