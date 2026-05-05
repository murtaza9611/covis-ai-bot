/** Shared seed for user profile avatars (TopBar + chat). Override via env in production if needed. */
export const USER_AVATAR_SEED =
  process.env.NEXT_PUBLIC_USER_AVATAR_SEED ?? 'Felix'

export function getUserAvatarUrl(): string {
  return `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(USER_AVATAR_SEED)}`
}
