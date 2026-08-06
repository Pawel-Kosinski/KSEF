"use client";

import { useApiQuery } from "@/hooks/useApiQuery";
import type { AuthUser } from "@/lib/types";

export function useCurrentUser() {
  return useApiQuery<AuthUser>("/auth/me", undefined, []);
}

export function isAdminUser(user: AuthUser | null | undefined): boolean {
  return user?.role === "admin";
}
