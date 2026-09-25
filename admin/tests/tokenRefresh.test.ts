import assert from 'node:assert/strict';
import test from 'node:test';

import { refreshAuthToken, registerTokenRefresher } from '../shared/api/client/refresh.ts';

test('concurrent 401s share one refresh call', async () => {
  let calls = 0;
  let release: (value: boolean) => void = () => undefined;
  registerTokenRefresher(() => {
    calls += 1;
    return new Promise<boolean>((resolve) => {
      release = resolve;
    });
  });
  const first = refreshAuthToken();
  const second = refreshAuthToken();
  release(true);
  assert.deepEqual(await Promise.all([first, second]), [true, true]);
  assert.equal(calls, 1);

  // Once settled, the next expiry triggers a fresh refresh.
  const third = refreshAuthToken();
  release(true);
  await third;
  assert.equal(calls, 2);
});

test('a failing refresh reports false instead of throwing', async () => {
  registerTokenRefresher(() => Promise.reject(new Error('network down')));
  assert.equal(await refreshAuthToken(), false);
});
