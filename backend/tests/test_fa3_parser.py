"""Testy parsera FA(3) – bez połączenia sieciowego."""

from decimal import Decimal
from pathlib import Path

import pytest

from app.services.xml import Fa3XmlParserError, parse_fa3_xml, parse_fa3_xml_file

FIXTURE = Path(__file__).parent / "fixtures" / "sample_fa3_invoice.xml"


def test_parse_sample_fixture():
    result = parse_fa3_xml_file(FIXTURE)
    assert result.namespace == "http://crd.gov.pl/wzor/2025/06/25/13775/"
    assert result.header.invoice_number == "FV/2026/01/001"
    assert result.header.seller_nip == "5265877635"
    assert result.header.buyer_nip == "1234567890"
    assert result.header.seller_name == "Dostawca Testowy Sp. z o.o."
    assert result.header.buyer_name == "Nabywca Testowy Sp. z o.o."
    assert result.header.total_net == Decimal("500.00")
    assert result.header.total_vat == Decimal("115.00")
    assert result.header.total_gross == Decimal("615.00")
    assert len(result.lines) == 2

    line1 = result.lines[0]
    assert line1.product_name == "Elektrody spawalnicze 3.2mm"
    assert line1.quantity == Decimal("10")
    assert line1.unit_price == Decimal("25.50")
    assert line1.line_net_value == Decimal("255.00")


def test_rejects_xxe_entity():
    malicious = b"""<?xml version="1.0"?>
    <Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/">
      <Podmiot1><DaneIdentyfikacyjne><NIP>1111111111</NIP></DaneIdentyfikacyjne></Podmiot1>
      <Podmiot2><DaneIdentyfikacyjne><NIP>2222222222</NIP></DaneIdentyfikacyjne></Podmiot2>
      <Fa>
        <P_1>2026-01-01</P_1><P_2>XX/1</P_2>
        <FaWiersz><P_7>&xxe;</P_7><P_8B>1</P_8B><P_9A>1</P_9A><P_11>1</P_11></FaWiersz>
      </Fa>
    </Faktura>"""
  # Parser nie powinien rozwiązywać encji – &xxe; pozostaje literalny lub błąd składni
    try:
        result = parse_fa3_xml(malicious)
        assert "&xxe;" in result.lines[0].product_name or result.lines[0].product_name == "&xxe;"
    except Fa3XmlParserError:
        pass  # odrzucenie złośliwego XML też jest akceptowalne


def test_missing_lines_raises():
    empty = b"""<?xml version="1.0"?>
    <Faktura xmlns="http://crd.gov.pl/wzor/2025/06/25/13775/">
      <Podmiot1><DaneIdentyfikacyjne><NIP>1111111111</NIP></DaneIdentyfikacyjne></Podmiot1>
      <Podmiot2><DaneIdentyfikacyjne><NIP>2222222222</NIP></DaneIdentyfikacyjne></Podmiot2>
      <Fa><P_1>2026-01-01</P_1><P_2>XX/1</P_2></Fa>
    </Faktura>"""
    with pytest.raises(Fa3XmlParserError, match="Nie znaleziono wierszy"):
        parse_fa3_xml(empty)
