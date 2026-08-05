export function EmptyDataHint() {
  return (
    <div className="flex h-48 flex-col items-center justify-center text-center text-sm text-slate-500">
      <p>Brak danych do wyświetlenia.</p>
      <p className="mt-2 max-w-xs text-xs text-slate-400">
        Wybierz inny okres lub pobierz faktury z KSeF, aby zaktualizować
        dashboard.
      </p>
    </div>
  );
}
