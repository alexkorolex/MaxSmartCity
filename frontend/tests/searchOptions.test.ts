import assert from 'node:assert/strict';
import test from 'node:test';

import { filterSearchOptions } from '../shared/lib/search/filterSearchOptions.ts';

const OPTIONS = [
  { id: '1', label: 'улица Евдокимова, 10', description: 'Брянская область, Брянск' },
  { id: '2', label: 'улица Мира, 9', description: 'Бахчисарай' },
  { id: '3', label: 'проспект Ленина, 1', keywords: 'центр брянск' },
];

test('filters options without regard to case or surrounding spaces', () => {
  assert.deepEqual(filterSearchOptions(OPTIONS, '  БРЯНСК  ').map((item) => item.id), ['1', '3']);
});

test('searches option descriptions and extra keywords', () => {
  assert.deepEqual(filterSearchOptions(OPTIONS, 'бахчисарай').map((item) => item.id), ['2']);
  assert.deepEqual(filterSearchOptions(OPTIONS, 'центр').map((item) => item.id), ['3']);
});

test('returns all options for an empty query', () => {
  assert.equal(filterSearchOptions(OPTIONS, '').length, OPTIONS.length);
});
