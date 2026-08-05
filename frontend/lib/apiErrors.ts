export function parseApiErrorMessage(
  payload: unknown,
  status?: number,
  fallback = "Operacja nie powiodła się",
): string {
  if (typeof payload === "object" && payload !== null && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" && item !== null && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : String(item),
        )
        .join(", ");
    }
  }

  if (status === 500) {
    return "Błąd serwera podczas rejestracji. Sprawdź, czy backend działa poprawnie.";
  }

  if (status === 0 || status === undefined) {
    return "Brak połączenia z serwerem. Uruchom backend i spróbuj ponownie.";
  }

  return fallback;
}
