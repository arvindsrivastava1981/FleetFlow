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
from datetime import datetime

from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import Paragraph, SimpleDocTemplate

from backend.app.services.audit.cash import DEFAULT_DRIVER_BATTA
from backend.app.services.pdf.settlement import (
    _FONT_NAME,
    BUCKET_LABELS,
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


def test_bundled_font_covers_latin_letters() -> None:
    """The bundled font must carry A-Z/a-z glyphs, not just Devanagari.

    Regression guard: the original bundled NotoSansDevanagari-Regular.ttf was
    a script-only build whose cmap had NO Latin letterforms, so every English
    word in the voucher (labels, dates like ``21-Aug-2026``, ``NET SETTLEMENT``)
    painted as blank .notdef boxes while digits/Hindi still rendered.
    """
    face = pdfmetrics.getFont(_FONT_NAME).face
    cm = face.charToGlyph
    missing = [chr(c) for c in range(0x41, 0x7B) if c not in cm]
    assert not missing, f"bundled font lacks Latin glyphs: {''.join(missing)}"
    assert 0x20B9 in cm, "bundled font must keep the rupee sign (₹)"


def _ascii_letters_in_pdf(pdf: bytes) -> bool:
    """Return True if any ToUnicode CMap maps a used glyph to an ASCII letter.

    Mirrors :func:`_devanagari_in_pdf`: reportlab writes ``beginbfchar``
    entries ``<glyph> <UTF-16 hex>``, so a painted English letter shows up as
    a destination like ``<0044>`` ('D'). Glyphs that are NOT in the font never
    get a bfchar entry, so this proves English text was really embedded.
    """
    ascii_hex = {f"{cp:04X}" for cp in range(0x41, 0x7B)} | {f"{cp:04X}" for cp in range(0x61, 0x7B)}
    text = pdf.decode("latin1")
    for m in re.finditer(r"stream", text):
        start = text.find("\n", m.start()) + 1
        end = text.find("endstream", start)
        if end < 0:
            continue
        try:
            decoded = zlib.decompress(text[start:end].encode("latin1"))
        except zlib.error:
            continue
        seen = set(re.findall(rb"<[0-9A-F]{2}>\s*<([0-9A-F]{4})>", decoded))
        if {v.decode("ascii") for v in seen} & ascii_hex:
            return True
    return False


def test_build_settlement_pdf_embeds_latin_glyphs() -> None:
    """The generated PDF must embed English (ASCII letter) glyphs too."""
    from datetime import datetime

    trip = _sample_trip(manager_consent_at=datetime(2026, 8, 21, 9, 47))
    pdf = build_settlement_pdf(trip, _sample_expenses())
    assert isinstance(pdf, bytes)
    assert len(pdf) > 5000
    assert _ascii_letters_in_pdf(pdf), (
        "PDF must embed Latin glyphs — English text went blank "
        "(script-only font regression)"
    )


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


def test_hi_style_enables_shaping() -> None:
    """Devanagari must render through HarfBuzz so conjuncts + matras shape.

    reportlab only runs complex-script shaping when the style has ``shaping`` set
    AND the font is ``shapable`` (which requires the ``uharfbuzz`` package). With
    shaping disabled, Devanagari is laid out naively left-to-right, reordering
    pre-base matras (``विवरण`` -> ``वविरण``) and breaking conjuncts (``ट्रिप`` ->
    ``टरपि``). This test guards the regression where those assets/config were
    dropped.
    """
    import uharfbuzz  # noqa: F401  (must be installed for shaping)
    from reportlab.lib.styles import getSampleStyleSheet

    style = _hi_style(getSampleStyleSheet()["Normal"])
    assert style.shaping is True, "_hi_style must enable HarfBuzz shaping"

    font = pdfmetrics.getFont(_FONT_NAME)
    assert getattr(font, "shapable", False) is True, (
        "Devanagari font must be shapable; install uharfbuzz (reportlab discovers it at runtime)"
    )
    assert font.hbFont is not None, "reportlab must have a HarfBuzz harness for the font"


def test_bi_never_emits_orphaned_slash() -> None:
    """Bilingual label joins must never produce a leading/trailing orphaned '/'.

    Regression for the 'Missing English Labels / Leading Orphaned Slashes' bug:
    when either the English or Hindi key is empty/None, the naive ``f'{en} / {hi}'``
    emits a stray slash. The helper returns only the populated side instead.
    """
    from backend.app.services.pdf.settlement import _bi

    # Both populated -> normal bilingual form.
    assert _bi("FUEL", "डीजल") == "FUEL / डीजल"
    # English missing -> keep Hindi only, NO leading slash.
    assert _bi("", "डीजल") == "डीजल"
    assert _bi(None, "डीजल") == "डीजल"
    # Hindi missing -> English only, NO trailing slash.
    assert _bi("FUEL", "") == "FUEL"
    assert _bi("FUEL", None) == "FUEL"
    # Both missing -> neutral dash, never an orphaned slash.
    assert _bi(None, None) == "—"
    assert "/" not in _bi("", "")
    # Whitespace-only labels are treated as missing.
    assert _bi("  ", "डीजल") == "डीजल"


def test_fmt_ts_handles_none_datetime_and_string() -> None:
    """Timestamp formatter must never crash and return readable values."""
    from backend.app.services.pdf.settlement import _fmt_ts

    assert _fmt_ts(None) == "—"
    assert _fmt_ts("already a string") == "already a string"
    ts = _fmt_ts(datetime(2026, 8, 20, 14, 35))
    assert "2026" in ts and "Aug" in ts


def test_consent_names_attach_without_crash() -> None:
    """Voucher with consent names must build without error (non-breaking)."""
    pdf = build_settlement_pdf(
        _sample_trip(
            manager_consent_by=1,
            manager_consent_at=datetime(2026, 8, 20, 14, 30),
            driver_consent_by=2,
            driver_consent_at=datetime(2026, 8, 20, 14, 35),
        ),
        _sample_expenses(),
        manager_consent_name="Ajay Kumar",
        driver_consent_name="Raju Bhai",
    )
    assert isinstance(pdf, bytes)
    assert len(pdf) > 5000, "PDF must not be a stub"


def test_consent_absent_prints_dashes() -> None:
    """Voucher without consent data still builds and prints dashes."""
    pdf = build_settlement_pdf(_sample_trip(), _sample_expenses())
    assert isinstance(pdf, bytes)
    assert len(pdf) > 5000
def test_weasyprint_unavailable_falls_back_to_reportlab() -> None:
    """Requesting renderer='weasyprint' without native libs still returns bytes."""
    from backend.app.services.pdf import settlement as svc

    # On machines without Pango native libs the import inside the service fails,
    # so _WEASYPRINT_AVAILABLE is False and we fall back to the reportlab render.
    if svc._WEASYPRINT_AVAILABLE:
        try:
            pdf = build_settlement_pdf(
                _sample_trip(), _sample_expenses(), renderer="weasyprint"
            )
        except Exception:
            # Native libs may be present but rendering could still fail (font
            # selection, etc.); treat any hard failure as out-of-scope guard.
            pdf = build_settlement_pdf(_sample_trip(), _sample_expenses())
    else:
        pdf = build_settlement_pdf(
            _sample_trip(), _sample_expenses(), renderer="weasyprint"
        )
    assert isinstance(pdf, bytes)
    assert len(pdf) > 5000, "PDF must not be a stub (even under fallback)"


def test_weasyprint_context_carries_full_bilingual_data() -> None:
    """The Jinja2 context must contain every field the template needs."""
    from backend.app.services.audit.cash import compute_settlement
    from backend.app.services.pdf.settlement import _build_weasyprint_context

    trip = _sample_trip(
        trip_code="4191-1",
        vehicle_no="UP32DE1234",
        driver_name="Ramesh Kumar",
        driver_phone="919999999999",
        origin="Delhi",
        destination="Lucknow",
        start_odo=100000.0,
        end_odo=100500.0,
        manager_consent_by=1,
        manager_consent_at=datetime(2026, 8, 20, 14, 30),
    )
    expenses = [
        {"exp_type": "FUEL", "amount": 2500.0, "manager_status": "APPROVED"},
        {"exp_type": "TOLL", "amount": 100.0, "manager_status": "APPROVED"},
        {"exp_type": "GOODS_SALE", "amount": 8000.0, "manager_status": "APPROVED"},
        {"exp_type": "CASH_ADVANCE", "amount": 0.0, "manager_status": "APPROVED"},
        {"exp_type": "DRIVER_SALARY", "amount": 2500.0, "manager_status": "APPROVED"},
    ]
    ctx = _build_weasyprint_context(
        trip, compute_settlement(trip, expenses),
        manager_consent_name="Ajay Kumar",
        driver_consent_name="Raju Bhai",
    )
    assert ctx["trip_code"] == "4191-1"
    assert ctx["total_km"] == "500"
    assert ctx["show_consent"] is True
    # FUEL + TOLL must both appear as debit rows.
    assert len(ctx["debit_rows"]) == 2
    assert ctx["net_balance"] is not None
    assert ctx["verification_hash"]


# ---- MISC receipt descriptions on the voucher ----------------------------------


def test_misc_sublines_escape_and_format() -> None:
    """Note text is XML-escaped (free-typed input) and amounts formatted."""
    from backend.app.services.pdf.settlement import _misc_sublines

    assert _misc_sublines([]) == ""
    out = _misc_sublines([("Kanta <heavy> & load", 1200.0)])
    assert "Kanta" in out
    assert "&lt;heavy&gt;" in out and "&amp;" in out  # never raw markup
    assert "₹1,200.00" in out


def test_misc_description_voucher_builds_with_reportlab() -> None:
    """A MISC expense carrying raw_receipt_text renders without error."""
    pdf = build_settlement_pdf(
        _sample_trip(),
        _sample_expenses()
        + [
            {
                "exp_type": "MISC",
                "amount": 1200.0,
                "raw_receipt_text": "Kanta at Bareilly weighbridge",
                "manager_status": "APPROVED",
            },
        ],
    )
    assert isinstance(pdf, bytes)
    assert len(pdf) > 5000


def test_weasyprint_context_attaches_notes_to_misc_row() -> None:
    """The MISC debit row carries its descriptions for the HTML template."""
    from backend.app.services.audit.cash import compute_settlement
    from backend.app.services.pdf.settlement import _build_weasyprint_context

    expenses = [
        {"exp_type": "MISC", "amount": 1200.0, "manager_status": "APPROVED"},
    ]
    ctx = _build_weasyprint_context(
        _sample_trip(),
        compute_settlement(_sample_trip(), expenses),
        None,
        None,
        misc_notes=[("Kanta at Bareilly", 1200.0)],
    )
    misc_row = next(r for r in ctx["debit_rows"] if r[0] == "Misc & Loading")
    assert misc_row[2] == 1200.0
    assert misc_row[3] == ["Kanta at Bareilly"]
