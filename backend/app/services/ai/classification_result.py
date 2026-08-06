"""Wynik kategoryzacji wiersza faktury."""

from dataclasses import dataclass
from typing import Literal

CategorySource = Literal["ai", "rule", "user", "fallback"]


@dataclass(frozen=True)
class ClassificationResult:
    kategoria_glowna: str | None
    kategoria_podrzedna: str | None
    pewnosc_klasyfikacji: int
    source: CategorySource

    @property
    def category_source(self) -> CategorySource:
        return self.source
