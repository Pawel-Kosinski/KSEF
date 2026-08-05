import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import {
  ACCESS_TOKEN_COOKIE,
  COOKIE_MAX_AGE_SEC,
  backendApiUrl,
} from "@/lib/auth";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const backendRes = await fetch(`${backendApiUrl()}/api/v1/auth/register`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  const payload = await backendRes.json().catch(() => ({}));

  if (!backendRes.ok) {
    return NextResponse.json(payload, { status: backendRes.status });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(ACCESS_TOKEN_COOKIE, payload.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: COOKIE_MAX_AGE_SEC,
  });

  return response;
}
