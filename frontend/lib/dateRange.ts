export interface DateRange {
  dateFrom: string;
  dateTo: string;
}

/** Domyślny rozmiar okresu jednego żądania sync (dni). */
export const SYNC_CHUNK_DAYS = 7;

export function formatDateLocal(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function currentMonthRange(): DateRange {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth(), 1);
  return { dateFrom: formatDateLocal(from), dateTo: formatDateLocal(now) };
}

export function previousMonthRange(): DateRange {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const to = new Date(now.getFullYear(), now.getMonth(), 0);
  return { dateFrom: formatDateLocal(from), dateTo: formatDateLocal(to) };
}

export function lastNDaysRange(days: number): DateRange {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - (days - 1));
  return { dateFrom: formatDateLocal(from), dateTo: formatDateLocal(to) };
}

export function isValidDateRange(range: DateRange): boolean {
  return range.dateFrom <= range.dateTo;
}

export function splitDateRange(
  dateFrom: string,
  dateTo: string,
  chunkDays: number,
): DateRange[] {
  const chunks: DateRange[] = [];
  let current = new Date(`${dateFrom}T12:00:00`);
  const end = new Date(`${dateTo}T12:00:00`);

  while (current <= end) {
    const chunkEnd = new Date(current);
    chunkEnd.setDate(chunkEnd.getDate() + chunkDays - 1);
    const effectiveEnd = chunkEnd > end ? end : chunkEnd;
    chunks.push({
      dateFrom: formatDateLocal(current),
      dateTo: formatDateLocal(effectiveEnd),
    });
    current = new Date(effectiveEnd);
    current.setDate(current.getDate() + 1);
  }

  return chunks;
}

export const DATE_RANGE_PRESETS: Array<{
  id: string;
  label: string;
  range: () => DateRange;
}> = [
  { id: "current-month", label: "Ten miesiąc", range: currentMonthRange },
  { id: "prev-month", label: "Poprzedni miesiąc", range: previousMonthRange },
  { id: "last-30", label: "Ostatnie 30 dni", range: () => lastNDaysRange(30) },
  { id: "last-90", label: "Ostatnie 90 dni", range: () => lastNDaysRange(90) },
];
