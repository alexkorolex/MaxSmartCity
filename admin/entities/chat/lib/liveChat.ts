
interface ChatChange {
  created_at: string;
  read_at: string | null;
}

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
