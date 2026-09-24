import assert from 'node:assert/strict';
import test from 'node:test';

import { isValidInn, isValidOgrn } from '../entities/organization/lib/requisites.ts';

test('INN check digits follow the FNS algorithm', () => {
  assert.equal(isValidInn('7707083893'), true);
  assert.equal(isValidInn('500100732259'), true);
  assert.equal(isValidInn('7707083894'), false);
  assert.equal(isValidInn('770708389'), false);
  assert.equal(isValidInn('77070838a3'), false);
});

test('OGRN and OGRNIP check digits', () => {
  assert.equal(isValidOgrn('1027700132195'), true);
  assert.equal(isValidOgrn('304500116000157'), true);
  assert.equal(isValidOgrn('1027700132196'), false);
  assert.equal(isValidOgrn('102770013219'), false);
});
