import { Avatar } from '@maxhub/max-ui';

import { getMaxBridgeUserAvatarUrl } from '@/shared/lib';

interface UserAvatarProps {
  name?: string | null;
  size: number;
}

function initialsOf(name: string | null | undefined): string {
  if (!name?.trim()) return '?';
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

/** The signed-in resident's MAX photo with a stable initials fallback. */
export function UserAvatar({ name, size }: UserAvatarProps) {
  const avatarUrl = getMaxBridgeUserAvatarUrl();

  return (
    <Avatar.Container size={size}>
      <Avatar.Image
        src={avatarUrl ?? undefined}
        alt={name?.trim() || 'Аватар пользователя'}
        fallback={initialsOf(name)}
        fallbackGradient="blue"
      />
    </Avatar.Container>
  );
}
