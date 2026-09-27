import assert from 'node:assert/strict';
import test from 'node:test';

import { getMaxBridgeInitData } from '../shared/lib/max-bridge/getInitData.ts';

test('returns the signed launch data MAX passes to the mini app', () => {
  const initData = 'auth_date=1790000000&user=%7B%22id%22%3A42%7D&hash=abc';

  assert.equal(getMaxBridgeInitData({ initData }), initData);
});

test('treats a missing bridge or empty launch data as unavailable', () => {
  assert.equal(getMaxBridgeInitData(undefined), null);
  assert.equal(getMaxBridgeInitData(null), null);
  assert.equal(getMaxBridgeInitData({ initData: '' }), null);
  assert.equal(getMaxBridgeInitData({ initData: '   ' }), null);
});
