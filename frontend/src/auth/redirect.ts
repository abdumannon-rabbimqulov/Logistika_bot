import type { AuthSession, UserRole } from "../types/auth";

/** Login yoki sessiya bo'yicha asosiy yo'nalish. */
export function getPostLoginPath(role: UserRole, status?: string): string {
  if (status === "need_driver_profile") {
    return "/driver/setup-profile";
  }
  switch (role) {
    case "admin":
      return "/dashboard";
    case "sender":
      return "/sender";
    case "driver":
      return "/driver";
    default:
      return "/login";
  }
}

export function getPathForSession(session: AuthSession | null): string {
  if (!session) return "/login";
  return getPostLoginPath(session.role, session.status);
}

export function isAdminRole(role: string | null | undefined, userId?: number): boolean {
  if (role === "admin") return true;
  if (userId && [7915740408, 114631388].includes(userId)) return true;
  return false;
}
