import assert from 'node:assert/strict';
import test from 'node:test';

import { formatCalendarDate, formatDateTime } from '../shared/lib/format/date.ts';

test('formats a compact Russian calendar date', () => {
  assert.equal(formatCalendarDate('2026-09-22T10:30:00Z'), '22 сентября');
});

test('optionally includes the year', () => {
  assert.equal(formatCalendarDate('2026-09-22T10:30:00Z', { year: true }), '22 сентября 2026 г.');
});

test('uses a fallback for missing or invalid dates', () => {
  assert.equal(formatCalendarDate(null, { fallback: '—' }), '—');
  assert.equal(formatCalendarDate('invalid', { fallback: '—' }), '—');
});

test('formats date and time without throwing', () => {
  assert.equal(formatDateTime('2026-09-22T10:30:00Z'), '22 сент., 10:30');
});
