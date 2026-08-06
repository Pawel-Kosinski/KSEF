import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ACCESS_TOKEN_COOKIE, backendApiUrl } from "@/lib/auth";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxyRequest(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const targetPath = `/api/v1/${path.join("/")}`;
  const url = new URL(targetPath, backendApiUrl());
  url.search = request.nextUrl.search;

  const token = (await cookies()).get(ACCESS_TOKEN_COOKIE)?.value;
  const headers = new Headers();
  headers.set("Accept", "application/json");

  const contentType = request.headers.get("content-type");
  if (contentType) {
    headers.set("Content-Type", contentType);
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  const body = hasBody ? await request.arrayBuffer() : undefined;

  const backendRes = await fetch(url.toString(), {
    method: request.method,
    headers,
    body,
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  const backendContentType = backendRes.headers.get("content-type");
  if (backendContentType) {
    responseHeaders.set("content-type", backendContentType);
  }

  const response = new NextResponse(backendRes.body, {
    status: backendRes.status,
    headers: responseHeaders,
  });

  if (backendRes.status === 401) {
    response.cookies.delete(ACCESS_TOKEN_COOKIE);
  }

  return response;
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyRequest(request, context);
}
