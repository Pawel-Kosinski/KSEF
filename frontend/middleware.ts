import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ACCESS_TOKEN_COOKIE } from "@/lib/auth";
import { isJwtExpired } from "@/lib/jwt";

const PUBLIC_PATHS = ["/login", "/register"];

function redirectToLogin(request: NextRequest, clearCookie: boolean) {
  const loginUrl = new URL("/login", request.url);
  const { pathname } = request.nextUrl;
  if (pathname !== "/") {
    loginUrl.searchParams.set("from", pathname);
  }
  const response = NextResponse.redirect(loginUrl);
  if (clearCookie) {
    response.cookies.delete(ACCESS_TOKEN_COOKIE);
  }
  return response;
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (
    pathname.startsWith("/api/") ||
    pathname.startsWith("/_next/") ||
    pathname === "/favicon.ico"
  ) {
    return NextResponse.next();
  }

  const token = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  const isPublic = PUBLIC_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );

  if (isPublic) {
    if (token && !isJwtExpired(token) && (pathname === "/login" || pathname === "/register")) {
      return NextResponse.redirect(new URL("/", request.url));
    }
    return NextResponse.next();
  }

  if (!token || isJwtExpired(token)) {
    return redirectToLogin(request, Boolean(token));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
