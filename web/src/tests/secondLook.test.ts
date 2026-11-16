/** The AI second look shown to teachers: plain words, never a raw server error. */
import { describe, expect, it } from 'vitest';
import { plainReason, secondLookText } from '../utils/secondLook';

const RAW = "Second look unavailable: ServerError: 504 DEADLINE_EXCEEDED. {'error': {'code': 504, 'message': 'Deadline expired before operation could complete.', 'status': 'DEADLINE_EXCEEDED'}}";

describe('second look text', () => {
  it('never shows a raw server error', () => {
    const t = secondLookText({ status: 'warn', answer: '', detail: RAW });
    expect(t).toBe('could not run this time. Check the picture yourself.');
    expect(t).not.toMatch(/504|DEADLINE|\{/);
  });

  it('shows a short plain reason as is', () => {
    const t = secondLookText({ status: 'warn', answer: '', detail: 'Shown only the adapted page, our model could not name anything.' });
    expect(t).toBe('Shown only the adapted page, our model could not name anything. Check the picture yourself.');
  });

  it('names a different answer as a weak signal', () => {
    expect(secondLookText({ status: 'warn', answer: 'toucan', detail: null })).toBe('named “toucan”. It can be wrong too; check the picture.');
    expect(secondLookText({ status: 'pass', answer: 'rabbit', detail: null })).toBe('named the same subject (“rabbit”).');
    expect(secondLookText({ status: 'pending', answer: null, detail: null })).toBe('still checking.');
  });

  it('plainReason refuses JSON, exceptions and long text', () => {
    expect(plainReason(RAW)).toBeNull();
    expect(plainReason('x'.repeat(200))).toBeNull();
    expect(plainReason('  ')).toBeNull();
    expect(plainReason('Second look named something else.')).toBe('Second look named something else.');
  });
});
