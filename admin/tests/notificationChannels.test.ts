import assert from 'node:assert/strict';
import test from 'node:test';

import { CHANNEL_META, channelTargetError } from '../entities/notification-channel/lib/channels.ts';

test('channel targets are validated like the backend strategies do', () => {
  assert.equal(channelTargetError('MAX_CHAT', '-100123456789'), null);
  assert.notEqual(channelTargetError('MAX_CHAT', 'диспетчерская'), null);
  assert.equal(channelTargetError('EMAIL', 'dispatch@uk.ru'), null);
  assert.notEqual(channelTargetError('EMAIL', 'dispatch'), null);
  assert.equal(channelTargetError('WEBHOOK', 'https://crm.uk.ru/hook'), null);
  assert.notEqual(channelTargetError('WEBHOOK', 'http://crm.uk.ru/hook'), null);
  assert.equal(channelTargetError('MAX_MEMBERS', ''), null);
});

test('only the webhook channel is reserved for the admin', () => {
  const adminOnly = Object.entries(CHANNEL_META).filter(([, meta]) => meta.adminOnly).map(([type]) => type);
  assert.deepEqual(adminOnly, ['WEBHOOK']);
});
