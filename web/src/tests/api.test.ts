import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { ApiError, api, buildApiUrl, createApiClient, messageFromBody, normalizeBase } from '../api';
import { scenarios } from '../mocks/db';
import { server } from '../mocks/node';

describe('URL building', () => {
  it.each([
    ['', '/api/books'],
    ['/', '/api/books'],
    ['/api', '/api/books'],
    ['/api/', '/api/books'],
    ['https://mirai.example.org', 'https://mirai.example.org/api/books'],
    ['https://mirai.example.org/', 'https://mirai.example.org/api/books'],
    ['https://mirai.example.org/api', 'https://mirai.example.org/api/books'],
    ['https://mirai.example.org/api/', 'https://mirai.example.org/api/books'],
    ['https://mirai.example.org/sub/', 'https://mirai.example.org/sub/api/books'],
  ])('base %j -> %s (exactly one /api)', (base, expected) => {
    const url = buildApiUrl(base, '/books');
    expect(url).toBe(expected);
    expect(url).not.toContain('/api/api');
  });

  it('normalizes bases', () => {
    expect(normalizeBase('  https://x.org/API/ ')).toBe('https://x.org');
  });

  it('encodes query params in order and skips empty values', () => {
    expect(buildApiUrl('', '/render/p1', { profile: 'pr 1', level: 2, v: 'abc', skip: undefined })).toBe(
      '/api/render/p1?profile=pr+1&level=2&v=abc',
    );
  });
});

describe('error normalization', () => {
  it('reads FastAPI string and list details', () => {
    expect(messageFromBody(422, { detail: 'Bad file' })).toBe('Bad file');
    expect(messageFromBody(422, { detail: [{ msg: 'a' }, { msg: 'b' }] })).toBe('a; b');
    expect(messageFromBody(500, undefined)).toMatch(/server had a problem/);
    expect(messageFromBody(401, {})).toMatch(/site password/);
  });

  it('turns HTTP errors into ApiError with status and server detail', async () => {
    const err = await api.getBook('nope').catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(404);
    expect((err as ApiError).message).toBe('Book not found.');
  });

  it('reports network failures as kind "network"', async () => {
    scenarios.networkErrorNext = true;
    const err = await api.listBooks().catch((e: unknown) => e);
    expect((err as ApiError).kind).toBe('network');
  });

  it('reports cancellation as kind "aborted"', async () => {
    const ctrl = new AbortController();
    ctrl.abort();
    const err = await api.listBooks(ctrl.signal).catch((e: unknown) => e);
    expect((err as ApiError).kind).toBe('aborted');
  });

  it('passes 401 through as a real server answer', async () => {
    server.use(http.get('*/api/books', () => new HttpResponse(null, { status: 401 })));
    const err = await api.listBooks().catch((e: unknown) => e);
    expect((err as ApiError).status).toBe(401);
  });

  it('sends requests to the configured server without a duplicate /api', async () => {
    const seen: string[] = [];
    server.events.on('request:start', ({ request }) => seen.push(request.url));
    const client = createApiClient('https://mirai.example.org/api/');
    await client.listBooks();
    server.events.removeAllListeners();
    expect(seen).toEqual(['https://mirai.example.org/api/books']);
  });
});
