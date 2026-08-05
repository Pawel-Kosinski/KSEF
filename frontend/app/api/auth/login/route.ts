import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import {
  ACCESS_TOKEN_COOKIE,
  COOKIE_MAX_AGE_SEC,
  backendApiUrl,
} from "@/lib/auth";

export async function POST(request: NextRequest) {
  const body = (await request.json()) as { email?: string; password?: string };

  if (!body.email || !body.password) {
    return NextResponse.json(
      { detail: "Podaj e-mail i hasło" },
      { status: 400 },
    );
  }

  const form = new URLSearchParams();
  form.set("username", body.email.trim().toLowerCase());
  form.set("password", body.password);

  const backendRes = await fetch(`${backendApiUrl()}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
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
