"""Mapowanie role faktury ↔ subjectType KSeF."""

INVOICE_ROLE_COST = "cost"
INVOICE_ROLE_SALES = "sales"

KSEF_SUBJECT_TO_ROLE: dict[str, str] = {
    "Subject1": INVOICE_ROLE_SALES,
    "Subject2": INVOICE_ROLE_COST,
}


def ksef_subject_to_role(subject_type: str) -> str:
    role = KSEF_SUBJECT_TO_ROLE.get(subject_type)
    if role is None:
        raise ValueError(f"Nieobsługiwany subjectType: {subject_type}")
    return role


def resolve_contractor_name(
    invoice_role: str,
    seller_name: str | None,
    buyer_name: str | None,
) -> str | None:
    """Koszt: sprzedawca (Podmiot1); sprzedaż: nabywca (Podmiot2)."""
    if invoice_role == INVOICE_ROLE_SALES:
        return buyer_name
    return seller_name
