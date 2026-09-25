// No `@/` imports - unit-tested with plain node.

interface ChatChange {
  created_at: string;
  read_at: string | null;
}

/** The newest thing the client has seen in the chat - a message or a read receipt - which
 * the server's long poll compares against to tell whether anything happened since. */
export function latestChatChange(messages: ChatChange[]): string | null {
  let latest: string | null = null;
  let latestTime = Number.NEGATIVE_INFINITY;
  for (const message of messages) {
    for (const value of [message.created_at, message.read_at]) {
      if (!value) continue;
      const time = Date.parse(value);
      if (time > latestTime) {
        latestTime = time;
        latest = value;
      }
    }
  }
  return latest;
}
