/** 2-second polling of GET /books/{id}: starts while busy, stops when done, on 4xx, and on unmount. */
import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from '../api';
import { BOOK_POLL_MS, useBook } from '../hooks/useBook';
import type { Book, Page, PageState } from '../types/api';

function page(n: number, state: PageState): Page {
  return {
    id: `p${n}`,
    book_id: 'b1',
    number: n,
    width: 3000,
    height: 2250,
    text: '',
    state,
    reason: null,
    flags: [],
    page_kind: null,
    candidates: [],
    selected: null,
    subject_hash: null,
    confirmed: false,
    omitted: false,
    second_look: null,
  };
}

function book(states: PageState[], state: Book['state'] = 'ready'): Book {
  return {
    id: 'b1',
    title: 'Test',
    credits: { author: null, illustrator: null, publisher: null, source: null, license: null },
    state,
    page_count: states.length,
    created_at: '2026-11-14T00:00:00Z',
    pages: states.map((s, i) => page(i + 1, s)),
  };
}

const busy = book(['ready', 'processing']);
const done = book(['ready', 'failed']);

/** Let resolved promises and React updates settle without moving the clock. */
const flush = () => act(async () => {
  await vi.advanceTimersByTimeAsync(0);
});
const advance = (ms: number) => act(async () => {
  await vi.advanceTimersByTimeAsync(ms);
});

beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

describe('useBook polling', () => {
  it('fetches every 2 seconds while a page is processing, then stops', async () => {
    const get = vi.spyOn(api, 'getBook').mockResolvedValueOnce(busy).mockResolvedValueOnce(busy).mockResolvedValue(done);
    const { result } = renderHook(() => useBook('b1'));
    await flush();
    expect(get).toHaveBeenCalledTimes(1);
    expect(result.current.polling).toBe(true);

    await advance(BOOK_POLL_MS - 1);
    expect(get).toHaveBeenCalledTimes(1);
    await advance(1);
    expect(get).toHaveBeenCalledTimes(2);

    await advance(BOOK_POLL_MS);
    expect(get).toHaveBeenCalledTimes(3);
    expect(result.current.book?.pages[1]?.state).toBe('failed');
    expect(result.current.polling).toBe(false);

    await advance(BOOK_POLL_MS * 5);
    expect(get).toHaveBeenCalledTimes(3);
  });

  it('keeps polling while the book itself is ingesting', async () => {
    const get = vi.spyOn(api, 'getBook').mockResolvedValueOnce(book([], 'ingesting')).mockResolvedValue(done);
    renderHook(() => useBook('b1'));
    await flush();
    await advance(BOOK_POLL_MS);
    expect(get).toHaveBeenCalledTimes(2);
    await advance(BOOK_POLL_MS * 3);
    expect(get).toHaveBeenCalledTimes(2);
  });

  it('does not fetch at all for a settled book handed in by the Library', async () => {
    const get = vi.spyOn(api, 'getBook').mockResolvedValue(done);
    renderHook(() => useBook('b1', { initial: done }));
    await advance(BOOK_POLL_MS * 3);
    expect(get).not.toHaveBeenCalled();
  });

  it('polls a busy book handed in by the Library, starting 2 seconds later', async () => {
    const get = vi.spyOn(api, 'getBook').mockResolvedValue(done);
    const { result } = renderHook(() => useBook('b1', { initial: busy }));
    await flush();
    expect(get).not.toHaveBeenCalled();
    await advance(BOOK_POLL_MS);
    expect(get).toHaveBeenCalledTimes(1);
    expect(result.current.polling).toBe(false);
  });

  it('stops on unmount', async () => {
    const get = vi.spyOn(api, 'getBook').mockResolvedValue(busy);
    const { unmount } = renderHook(() => useBook('b1'));
    await flush();
    unmount();
    await advance(BOOK_POLL_MS * 5);
    expect(get).toHaveBeenCalledTimes(1);
  });

  it('keeps trying through a network blip, keeping the last book on screen', async () => {
    const get = vi
      .spyOn(api, 'getBook')
      .mockResolvedValueOnce(busy)
      .mockRejectedValueOnce(new ApiError('network', 'Could not reach the server.'))
      .mockResolvedValue(done);
    const { result } = renderHook(() => useBook('b1'));
    await flush();
    await advance(BOOK_POLL_MS);
    expect(result.current.error?.message).toMatch(/Could not reach/);
    expect(result.current.book).toBeDefined();
    expect(result.current.polling).toBe(true);
    await advance(BOOK_POLL_MS);
    expect(get).toHaveBeenCalledTimes(3);
    expect(result.current.error).toBeNull();
  });

  it('stops on a 4xx answer, and refresh() starts again', async () => {
    const get = vi
      .spyOn(api, 'getBook')
      .mockResolvedValueOnce(busy)
      .mockRejectedValueOnce(new ApiError('http', 'Not found on the server.', 404))
      .mockResolvedValue(busy);
    const { result } = renderHook(() => useBook('b1'));
    await flush();
    await advance(BOOK_POLL_MS);
    expect(result.current.polling).toBe(false);
    await advance(BOOK_POLL_MS * 3);
    expect(get).toHaveBeenCalledTimes(2);

    act(() => result.current.refresh());
    await flush();
    expect(get).toHaveBeenCalledTimes(3);
    expect(result.current.polling).toBe(true);
  });

  it('replacePages swaps in a mutation result and refresh() fetches at once', async () => {
    const get = vi.spyOn(api, 'getBook').mockResolvedValue(done);
    const { result } = renderHook(() => useBook('b1'));
    await flush();
    const retried = { ...done.pages[1]!, state: 'processing' as const };
    act(() => {
      result.current.replacePages([retried]);
      result.current.refresh();
    });
    expect(result.current.book?.pages[1]?.state).toBe('processing');
    await flush();
    expect(get).toHaveBeenCalledTimes(2);
  });
});
