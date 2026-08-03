"""
Bezpieczny parser XML dla schematu FA(3) KSeF.

- defusedxml.ElementTree – ochrona przed XXE / entity expansion
- Iteracja po drzewie z obsługą namespace FA(3)
"""

from decimal import Decimal, InvalidOperation
from datetime import date
from pathlib import Path
from xml.etree.ElementTree import Element

import defusedxml.ElementTree as DefusedET

from app.services.xml.models import Fa3InvoiceHeader, Fa3InvoiceLine, Fa3ParseResult

# Namespace FA(3) z dokumentacji projektu (schemat od 01.02.2026)
FA3_NAMESPACE = "http://crd.gov.pl/wzor/2025/06/25/13775/"

FA3_LINE_FIELDS = ("P_7", "P_8B", "P_9A", "P_11")


class Fa3XmlParserError(Exception):
    """Błąd parsowania faktury FA(3)."""


def _detect_namespace(root: Element) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}")[0].strip("{")
    return FA3_NAMESPACE


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _find_child(parent: Element, local_name: str) -> Element | None:
    for child in parent:
        if _local_name(child.tag) == local_name:
            return child
    return None


def _parse_decimal(value: str | None, field: str) -> Decimal:
    if value is None or not value.strip():
        raise Fa3XmlParserError(f"Brak wymaganego pola {field}")
    normalized = value.strip().replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise Fa3XmlParserError(f"Nieprawidłowa wartość {field}: {value!r}") from exc


def _text_of(parent: Element | None, local_name: str) -> str | None:
    if parent is None:
        return None
    child = _find_child(parent, local_name)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _parse_date(value: str | None, field: str) -> date:
    if not value:
        raise Fa3XmlParserError(f"Brak wymaganego pola daty {field}")
    try:
        return date.fromisoformat(value.strip()[:10])
    except ValueError as exc:
        raise Fa3XmlParserError(f"Nieprawidłowa data {field}: {value!r}") from exc


def _extract_nip(podmiot: Element | None) -> str:
    if podmiot is None:
        raise Fa3XmlParserError("Brak podmiotu na fakturze")
    for el in podmiot.iter():
        if _local_name(el.tag) == "NIP" and el.text and el.text.strip():
            return el.text.strip()
    raise Fa3XmlParserError("Brak NIP podmiotu")


def _extract_party_name(podmiot: Element | None) -> str | None:
    if podmiot is None:
        return None
    dane = _find_child(podmiot, "DaneIdentyfikacyjne")
    if dane is None:
        for el in podmiot.iter():
            if _local_name(el.tag) == "DaneIdentyfikacyjne":
                dane = el
                break
    return _text_of(dane, "Nazwa")


def _sum_decimal_children(parent: Element, prefix: str) -> Decimal | None:
    total = Decimal("0")
    found = False
    for child in parent:
        local = _local_name(child.tag)
        if local.startswith(prefix) and child.text and child.text.strip():
            total += _parse_decimal(child.text, local)
            found = True
    return total if found else None


def _extract_header_totals(fa: Element) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    total_net = _sum_decimal_children(fa, "P_13_")
    total_vat = _sum_decimal_children(fa, "P_14_")
    gross_raw = _text_of(fa, "P_15")
    total_gross = _parse_decimal(gross_raw, "P_15") if gross_raw else None
    if total_gross is None and total_net is not None and total_vat is not None:
        total_gross = total_net + total_vat
    if total_vat is None and total_gross is not None and total_net is not None:
        total_vat = total_gross - total_net
    return total_net, total_vat, total_gross


def _find_fa_element(root: Element) -> Element:
    for el in root.iter():
        if _local_name(el.tag) == "Fa":
            return el
    raise Fa3XmlParserError("Nie znaleziono sekcji Fa")


def _extract_header(root: Element) -> Fa3InvoiceHeader:
    fa = _find_fa_element(root)

    podmiot1_el = next((el for el in root.iter() if _local_name(el.tag) == "Podmiot1"), None)
    podmiot2_el = next((el for el in root.iter() if _local_name(el.tag) == "Podmiot2"), None)

    sale_raw = _text_of(fa, "P_6")
    total_net, total_vat, total_gross = _extract_header_totals(fa)
    return Fa3InvoiceHeader(
        invoice_number=_text_of(fa, "P_2") or "",
        issue_date=_parse_date(_text_of(fa, "P_1"), "P_1"),
        sale_date=_parse_date(sale_raw, "P_6") if sale_raw else None,
        seller_nip=_extract_nip(podmiot1_el),
        buyer_nip=_extract_nip(podmiot2_el),
        seller_name=_extract_party_name(podmiot1_el),
        buyer_name=_extract_party_name(podmiot2_el),
        total_net=total_net,
        total_vat=total_vat,
        total_gross=total_gross,
    )


def _extract_line(row: Element, index: int) -> Fa3InvoiceLine:
    p7 = _find_child(row, "P_7")
    p8b = _find_child(row, "P_8B")
    p9a = _find_child(row, "P_9A")
    p11 = _find_child(row, "P_11")

    if p7 is None or not (p7.text and p7.text.strip()):
        raise Fa3XmlParserError(f"Wiersz {index}: brak P_7 (nazwa towaru)")

    return Fa3InvoiceLine(
        line_number=index,
        product_name=p7.text.strip(),
        quantity=_parse_decimal(p8b.text if p8b is not None else None, "P_8B"),
        unit_price=_parse_decimal(p9a.text if p9a is not None else None, "P_9A"),
        line_net_value=_parse_decimal(p11.text if p11 is not None else None, "P_11"),
    )


def _extract_fa_wiersz_rows(root: Element) -> list[Element]:
    rows: list[Element] = []
    for fa in root.iter():
        if _local_name(fa.tag) != "Fa":
            continue
        for child in fa:
            if _local_name(child.tag) == "FaWiersz":
                rows.append(child)
    return rows


def parse_fa3_xml(xml_content: bytes | str) -> Fa3ParseResult:
    """
    Parsuje surowy XML FA(3) i zwraca listę wierszy faktury.

    Ścieżka logiczna: Fa / FaWiersz (z dynamicznym namespace z dokumentu).
    """
    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8")
    else:
        xml_bytes = xml_content

    try:
        root = DefusedET.fromstring(xml_bytes)
    except DefusedET.ParseError as exc:
        raise Fa3XmlParserError(f"Nieprawidłowy XML: {exc}") from exc

    namespace = _detect_namespace(root)

    rows = _extract_fa_wiersz_rows(root)
    if not rows:
        raise Fa3XmlParserError("Nie znaleziono wierszy faktury (Fa/FaWiersz)")

    header = _extract_header(root)
    if not header.invoice_number:
        raise Fa3XmlParserError("Brak numeru faktury (P_2)")

    lines = [_extract_line(row, idx) for idx, row in enumerate(rows, start=1)]
    return Fa3ParseResult(namespace=namespace, header=header, lines=lines)


def parse_fa3_xml_file(path: str | Path) -> Fa3ParseResult:
    """Wczytuje plik XML z dysku i parsuje go jako FA(3) – tylko do testów/skryptów."""
    file_path = Path(path)
    if not file_path.is_file():
        raise Fa3XmlParserError(f"Plik nie istnieje: {file_path}")
    return parse_fa3_xml(file_path.read_bytes())
