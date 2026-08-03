"""Wyjątki modułu kategoryzacji AI."""


class AICategorizerError(Exception):
    """Bazowy wyjątek modułu AI."""


class AIInputIsolationError(AICategorizerError):
    """Próba przekazania danych wykraczających poza izolowany product_name (P_7)."""


class AICategorizationError(AICategorizerError):
    """Błąd komunikacji z Ollama lub walidacji odpowiedzi modelu."""
