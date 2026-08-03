"""Wyjątki modułu integracji KSeF."""


class KsefError(Exception):
    """Bazowy wyjątek integracji KSeF."""


class KsefApiError(KsefError):
    def __init__(self, message: str, status_code: int | None = None, details: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class KsefAuthError(KsefError):
    """Błąd procesu uwierzytelniania (challenge → token → redeem)."""


class KsefAuthTimeoutError(KsefAuthError):
    """Przekroczono czas oczekiwania na zakończenie uwierzytelniania."""


class KsefSyncError(KsefError):
    """Błąd synchronizacji paczki faktur z KSeF."""


class KsefExportTimeoutError(KsefSyncError):
    """Przekroczono czas oczekiwania na gotowość eksportu."""


class KsefSyncValidationError(KsefSyncError):
    """Błąd walidacji warunków synchronizacji (kategorie, zakres dat)."""
