"""Unit tests for the bilingual settlement voucher PDF rendering.

Guard against a regression where Hindi (Devanagari) text renders as blank boxes
(▓▓▓): reportlab's built-in Helvetica has no Devanagari glyphs, so the PDF must
register a bundled Devanagari-capable TrueType font and build its paragraph
styles on top of it.
"""

from __future__ import annotations

import io
import re
import zlib

from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Paragraph, SimpleDocTemplate

from backend.app.services.audit.cash import DEFAULT_DRIVER_BATTA
from backend.app.services.pdf.settlement import (
    BUCKET_LABELS,
    _FONT_NAME,
    _hi_style,
    build_settlement_pdf,
)


def _sample_trip(**kw) -> dict:
    base = {
        "trip_code": "TRIP-101",
        "vehicle_no": "UP32DE1234",
        "driver_name": "Raju",
        "driver_phone": "919999999999",
        "origin": "Delhi",
        "destination": "Lucknow",
        "start_odo": 100000.0,
        "end_odo": 100500.0,
        "current_odo": 100500.0,
        "advance_amount": 10000.0,
        "driver_batta_amount": DEFAULT_DRIVER_BATTA,
    }
    base.update(kw)
    return base


def _sample_expenses() -> list[dict]:
    return [
        {"exp_type": "FUEL", "amount": 2715.0, "liters": 30.0, "manager_status": "APPROVED"},
        {"exp_type": "CHALLAN", "amount": 1200.0, "manager_status": "APPROVED"},
    ]


def _devanagari_in_pdf(pdf: bytes) -> bool:
    """Return True if any FlateDecode stream embeds Devanagari (0x0900-0x097F).

    reportlab writes a font-specific ToUnicode CMap whose ``beginbfchar``
    entries map each used glyph number to its Unicode value (UTF-16 hex), e.g.
    ``<01> <092F>``. We decompress every stream and look for one of those hex
    Unicode values in the Devanagari block.
    """
    dev_hex = {f"{cp:04X}" for cp in range(0x0900, 0x0980)}
    text = pdf.decode("latin1")
    for m in re.finditer(r"stream", text):
        start = text.find("\n", m.start()) + 1
        end = text.find("endstream", start)
        if end < 0:
            continue
        raw = text[start:end]
        try:
            decoded = zlib.decompress(raw.encode("latin1"))
        except zlib.error:
            continue
        # Match bfchar destination hex values: <xxxx> following a <source>.
        seen = set(re.findall(rb"<[0-9A-F]{2}>\s*<([0-9A-F]{4})>", decoded))
        if {v.decode("ascii") for v in seen} & dev_hex:
            return True
    return False


def test_devanagari_font_is_registered() -> None:
    """The bundled Devanagari TTF must be registered under _FONT_NAME."""
    assert _FONT_NAME in pdfmetrics.getRegisteredFontNames()


def test_hi_style_uses_devanagari_for_normal_and_bold() -> None:
    """Inline ``<b>`` markup must not drop Devanagari glyphs."""
    from reportlab.lib.styles import getSampleStyleSheet

    style = _hi_style(getSampleStyleSheet()["Normal"])
    assert style.fontName == _FONT_NAME
    assert style.boldFontName == _FONT_NAME


def test_bucket_labels_contain_hindi() -> None:
    """Every debit bucket carries a non-empty Devanagari Hindi label."""
    for en, hi in BUCKET_LABELS.values():
        assert en, "english label must be non-empty"
        assert hi, "hindi label must be non-empty"
        assert any(0x0900 <= ord(ch) <= 0x097F for ch in hi), f"{en} missing Devanagari"


def test_build_settlement_pdf_embeds_devanagari_glyphs() -> None:
    """The generated PDF must embed Devanagari glyphs (no blank-box regression)."""
    pdf = build_settlement_pdf(_sample_trip(), _sample_expenses())
    assert isinstance(pdf, bytes)
    assert len(pdf) > 5000, "expected a non-trivial PDF body"
    assert _devanagari_in_pdf(pdf), "PDF must embed Devanagari glyphs"


def test_hi_paragraph_builds_to_bytes() -> None:
    """A Paragraph with the registered font + Hindi markup must build cleanly."""
    from reportlab.lib.styles import getSampleStyleSheet

    style = _hi_style(getSampleStyleSheet()["Normal"])
    para = Paragraph("<b>TRIP SETTLEMENT VOUCHER</b> / यात्रा हिसाब पर्ची", style)
    buf = io.BytesIO()
    SimpleDocTemplate(buf).build([para])
    assert len(buf.getvalue()) > 500, "Hindi paragraph should render to bytes"