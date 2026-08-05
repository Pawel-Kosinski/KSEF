export const ACCESS_TOKEN_COOKIE = "access_token";

export const COOKIE_MAX_AGE_SEC = 60 * 60 * 24;

export function backendApiUrl(): string {
  return process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000";
}
