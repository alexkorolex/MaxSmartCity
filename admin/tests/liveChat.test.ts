import assert from 'node:assert/strict';
import test from 'node:test';

import { latestChatChange } from '../entities/chat/lib/liveChat.ts';

test('the newest message or read receipt is where the long poll resumes', () => {
  assert.equal(latestChatChange([]), null);
  assert.equal(
    latestChatChange([
      { created_at: '2026-09-25T10:00:00Z', read_at: '2026-09-25T10:05:00Z' },
      { created_at: '2026-09-25T10:03:00Z', read_at: null },
    ]),
    '2026-09-25T10:05:00Z',
  );
  assert.equal(
    latestChatChange([{ created_at: '2026-09-25T10:03:00+03:00', read_at: '2026-09-25T07:02:00Z' }]),
    '2026-09-25T10:03:00+03:00',
  );
});
