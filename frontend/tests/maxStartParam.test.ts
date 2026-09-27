import assert from 'node:assert/strict';
import test from 'node:test';

import { routeFromStartParam, safeNextPath } from '../shared/routes/startParam.ts';

const ID = '22222222-2222-2222-2222-222222222222';

test('maps bot notification start params to app screens', () => {
  assert.equal(routeFromStartParam(`report_${ID}_chat`), `/reports/${ID}/chat`);
  assert.equal(routeFromStartParam(`report_${ID}`), `/reports/${ID}`);
  assert.equal(routeFromStartParam(`incident_${ID}_resolution`), `/incidents/${ID}/resolution`);
  assert.equal(routeFromStartParam(`incident_${ID}`), `/incidents/${ID}`);
});

test('leaves login codes and unknown params alone', () => {
  assert.equal(routeFromStartParam('Zx9_k-2LqPq0aBcDeFgHiJkLmNoPqRsT'), null);
  assert.equal(routeFromStartParam(`report_${ID}_delete`), null);
  assert.equal(routeFromStartParam('report_../../admin'), null);
  assert.equal(routeFromStartParam(''), null);
  assert.equal(routeFromStartParam(null), null);
});

test('accepts only same-origin paths as the post-login destination', () => {
  assert.equal(safeNextPath(`/reports/${ID}/chat`), `/reports/${ID}/chat`);
  assert.equal(safeNextPath('https://evil.example'), null);
  assert.equal(safeNextPath('//evil.example'), null);
  assert.equal(safeNextPath('/\\evil.example'), null);
  assert.equal(safeNextPath(null), null);
});
