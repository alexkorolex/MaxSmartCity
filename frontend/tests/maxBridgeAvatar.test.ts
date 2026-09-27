import assert from 'node:assert/strict';
import test from 'node:test';

import { getMaxBridgeUserAvatarUrl } from '../shared/lib/max-bridge/getUserAvatarUrl.ts';

function bridgeWithPhoto(photoUrl?: string) {
  return {
    initDataUnsafe: {
      user: photoUrl === undefined ? undefined : { id: 42, photo_url: photoUrl },
    },
  };
}

test('reads the current user photo supplied by MAX Bridge', () => {
  const url = 'https://i.oneme.ru/i?avatar=resident';

  assert.equal(getMaxBridgeUserAvatarUrl(bridgeWithPhoto(url)), url);
});

test('ignores missing, malformed, and non-HTTPS avatar values', () => {
  assert.equal(getMaxBridgeUserAvatarUrl(bridgeWithPhoto()), null);
  assert.equal(getMaxBridgeUserAvatarUrl(bridgeWithPhoto('not a URL')), null);
  assert.equal(getMaxBridgeUserAvatarUrl(bridgeWithPhoto('http://example.com/avatar.jpg')), null);
});
