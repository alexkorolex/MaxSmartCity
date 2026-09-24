import assert from 'node:assert/strict';
import test from 'node:test';

import { formatPhone, websiteLabel } from '../entities/geo/lib/contacts.ts';

test('formats Russian E.164 numbers for reading', () => {
  assert.equal(formatPhone('+79621403018'), '+7 (962) 140-30-18');
  assert.equal(formatPhone('+74832123456'), '+7 (483) 212-34-56');
  assert.equal(formatPhone('+380441234567'), '+380441234567');
});

test('shortens a website to its host', () => {
  assert.equal(websiteLabel('https://www.domplus.bsr-profi.ru/about'), 'domplus.bsr-profi.ru');
  assert.equal(websiteLabel('not a url'), 'not a url');
});
