from __future__ import annotations

import html
import io
import logging
import os
import re
import zlib

from jinja2 import Environment, FileSystemLoader, select_autoescape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.app.services.audit.cash import (
    ROAD_EXPENSE_BUCKETS,
    SettlementResult,
    compute_settlement,
)

# ---------------------------------------------------------------------------#
# Devanagari-capable font registration.
#
# reportlab's built-in Helvetica has NO Devanagari glyphs, so any Hindi text
# renders as ▓ (blank boxes). We register a bundled TrueType font that carries
# the full Devanagari block (Noto Sans Devanagari, SIL OFL) so both the Latin
# and Devanagari scripts render correctly on every deploy target (Linux/macOS/
# Windows). The font is resolved relative to this module so it travels with the
# package and needs no system font dependency.
# ---------------------------------------------------------------------------#
_FONT_NAME = "VK-Devanagari"
_FONT_FILE = "NotoSansDevanagari-Regular.ttf"
_FONTS_DIR = os.path.dirname(__file__)
_FONT_PATH = os.path.join(_FONTS_DIR, _FONT_FILE)

pdfmetrics.registerFont(TTFont(_FONT_NAME, _FONT_PATH))

_HI_STYLE_CTR = [0]


def _hi_style(parent, **kwargs) -> ParagraphStyle:
    """Return a ParagraphStyle using the Devanagari font (for bilingual text).

    Sets ``fontName``/``boldFontName`` so reportlab's inline ``<b>`` markup
    keeps using the same font instead of falling back to Helvetica-Bold (which
    would drop Devanagari glyphs). Also enables ``shaping`` so reportlab routes
    Devanagari through HarfBuzz (via ``uharfbuzz``), which performs the complex
    GSUB/GPOS shaping (conjunct ligatures + pre-base matra repositioning) that
    a naive left-to-right codepoint layout cannot produce. Without this, Hindi
    renders broken (e.g. ``विवरण`` -> ``वविरण``, ``ट्रिप`` -> ``टरपि``).
    """
    kwargs.setdefault("fontName", _FONT_NAME)
    kwargs.setdefault("boldFontName", _FONT_NAME)
    kwargs.setdefault("shaping", True)
    _HI_STYLE_CTR[0] += 1
    name = kwargs.pop("name", None) or f"HiStyle_{_HI_STYLE_CTR[0]}"
    return ParagraphStyle(name, parent=parent, **kwargs)


# Bucket -> bilingual label (dr side). Debit rows follow ROAD_EXPENSE_BUCKETS order.
BUCKET_LABELS: dict[str, tuple[str, str]] = {
    "FUEL": ("Diesel Refills", "स्वीकृत डीजल खर्च"),
    "DEF": ("DEF (AdBlue)", "यूरिया खर्च"),
    "TOLL": ("Tolls & FASTag", "टोल पर्ची खर्च"),
    "REPAIR": ("Maintenance & Repairs", "मरम्मत खर्च"),
    "CHALLAN": ("Challans", "चालान खर्च"),
    "MISC": ("Misc & Loading", "अन्य खर्चे"),
    "GOODS_BUY": ("Goods Purchased", "माल खरीद"),
}

def _rs(value: float) -> str:
    return f"₹{value:,.2f}"


def _fmt_ts(ts) -> str:
    """Format a DB timestamp (datetime or str) into a human-readable local string.

    If *ts* is a datetime the output uses ``%d-%b-%Y %H:%M`` (e.g.
    ``20-Aug-2026 14:35``). If it is a string (e.g. from a test fixture or
    pre-formatted value), it is returned verbatim (never crash for parsing).
    ``None`` / missing returns ``"—"``.
    """
    if ts is None:
        return "—"
    if isinstance(ts, str):
        return ts
    try:
        return ts.strftime("%d-%b-%Y %H:%M")
    except (AttributeError, TypeError):
        return str(ts)


def _bi(label_en: str | None, label_hi: str | None) -> str:
    """Join English and Hindi labels with `` / `` without producing an orphaned slash.

    The voucher renders every bilingual line as ``{en} / {hi}`` or ``{key}: {val}``.
    If either language key is unset (``None``/empty), a naive concatenation emits a
    leading/trailing orphaned slash (e.g. ``/ यात्रा हिसाब पर्ची``). This helper
    drops the missing side and returns only the populated label (falling back to the
    other language, or a neutral ``—`` if both are empty) so the PDF never shows a
    stray leading ``/``.
    """
    en = (label_en or "").strip()
    hi = (label_hi or "").strip()
    if en and hi:
        return f"{en} / {hi}"
    if en:
        return en
    if hi:
        return hi
    return "—"


def _misc_sublines(misc_notes: list[tuple[str, float]]) -> str:
    """Format MISC descriptions as escaped ``<br/>`` bullet sub-lines.

    *misc_notes* is ``(raw_receipt_text, amount)`` pairs collected from the
    trip's MISC expenses; empty input yields ``""`` so callers append nothing.
    The text is free-typed driver input embedded into reportlab Paragraph
    markup, so it is XML-escaped first (never raw ``<``/``&``).
    """
    if not misc_notes:
        return ""
    lines = "<br/>".join(
        f"&nbsp;&nbsp;&nbsp;• {html.escape(note, quote=False)} ({_rs(amount)})"
        for note, amount in misc_notes
    )
    return f"<br/>{lines}"


# ---------------------------------------------------------------------------#
# Optional WeasyPrint renderer.
#
# reportlab (the default) already shapes Devanagari correctly via HarfBuzz and
# requires no external binaries. WeasyPrint provides a second, HTML/CSS-based
# renderer for users who want to maintain the voucher as a web-safe template.
# It needs Pango/HarfBuzz native libs (Linux: `apt-get install libpango-1.0-0
# libharfbuzz0b`); on boxes where those DLLs are absent `import weasyprint`
# raises OSError, so we degrade gracefully back to reportlab.
# ---------------------------------------------------------------------------#
logger = logging.getLogger(__name__)

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
_jinja_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)

try:
    from weasyprint import HTML as _WP_HTML  # noqa: E402

    _WEASYPRINT_AVAILABLE = True
except Exception as _wp_err:  # pragma: no cover - environment dependent
    _WEASYPRINT_AVAILABLE = False
    logger.warning("[pdf] weasyprint unavailable, using reportlab: %s", _wp_err)


def _render_weasyprint(context: dict) -> bytes:
    """Render the Jinja2 settlement voucher HTML into PDF bytes via WeasyPrint."""
    template = _jinja_env.get_template("settlement_voucher.html")
    rendered_html = template.render(**context)

    pdf_buffer = io.BytesIO()
    _WP_HTML(string=rendered_html).write_pdf(target=pdf_buffer)
    return pdf_buffer.getvalue()


def _build_weasyprint_context(
    trip: dict,
    s: SettlementResult,
    manager_consent_name: str | None,
    driver_consent_name: str | None,
    misc_notes: list[tuple[str, float]] | None = None,
) -> dict:
    """Assemble the template context from a trip + computed settlement."""
    odo_dist = (trip.get("end_odo") or trip.get("current_odo") or 0) - (trip.get("start_odo") or 0)
    mileage_text = f"{s.avg_kml:.2f} km/L" if s.avg_kml is not None else "N/A"

    # Debit rows: every non-zero expense bucket in the canonical order. The
    # MISC row carries its raw_receipt_text descriptions for sub-line printing.
    debit_rows = []
    for bucket in ROAD_EXPENSE_BUCKETS:
        amount = s.expense_buckets.get(bucket, 0.0)
        if amount != 0.0:
            en, hi = BUCKET_LABELS[bucket]
            notes = (
                [text for text, _amt in (misc_notes or [])]
                if bucket == "MISC"
                else []
            )
            debit_rows.append((en, hi, amount, notes))

    return {
        "trip_code": trip.get("trip_code"),
        "vehicle_no": trip.get("vehicle_no"),
        "driver_name": trip.get("driver_name"),
        "driver_phone": trip.get("driver_phone"),
        "origin": trip.get("origin") or "Origin",
        "destination": trip.get("destination") or "Destination",
        "total_km": f"{odo_dist:,.0f}",
        "mileage_text": mileage_text,
        "advance_amount": s.advance_amount,
        "goods_income": s.goods_income,
        "debit_rows": debit_rows,
        "driver_batta": s.driver_batta,
        "settlement_transfer": s.settlement_transfer,
        "settlement_transfer_side": s.settlement_transfer_side,
        "total_driver_credits": s.total_driver_credits,
        "total_cr": s.total_cr,
        "net_balance": s.net_balance,
        "status_label_en": s.status_label_en,
        "status_label_hi": s.status_label_hi,
        "verification_hash": s.verification_hash,
        "show_consent": bool(
            manager_consent_name or driver_consent_name
            or trip.get("manager_consent_at") or trip.get("driver_consent_at")
        ),
        "manager_consent_name": manager_consent_name,
        "driver_consent_name": driver_consent_name,
        "manager_consent_at": _fmt_ts(trip.get("manager_consent_at")),
        "driver_consent_at": _fmt_ts(trip.get("driver_consent_at")),
    }


# ---------------------------------------------------------------------------#
# Post-process the ToUnicode CMap to replace PUA fallback glyphs.
#
# When reportlab uses HarfBuzz for complex-script shaping (shaping=True),
# ligature/conjunct glyphs are emitted for sequences like "क्त" or "त्र".
# Those glyphs don't correspond to a single Unicode codepoint, so reportlab
# maps them to the Private Use Area (U+E000–U+E0FF) in the ToUnicode CMap.
# The PDF *renders* correctly visually, but copy-pasting text from the PDF
# produces garbled PUA characters (e.g. ``याा`` instead of ``यात्रा``).
#
# We intercept the raw PDF bytes, decompress every FlateDecode stream that
# looks like a ToUnicode CMap, and strip out the PUA bfchar entries so that
# PDF text-extraction tools fall back to glyph-name heuristics (which map
# the short glyph names to the correct Unicode decomposition).  This is safe
# because PUA glyphs are *only* a text-extraction hint — the visual rendering
# is driven exclusively by the glyph program, not the ToUnicode CMap.
# ---------------------------------------------------------------------------#
_PUA_RE = re.compile(rb"<([0-9A-F]{2})>\s*<E0[0-9A-F]{2}>", re.IGNORECASE)


def _fix_pua_tounicode(pdf_bytes: bytes) -> bytes:
    """Remove Private Use Area fallback entries from every ToUnicode CMap in *pdf_bytes*.

    Returns the modified PDF (a new bytes object).  If no PUA entries are
    found the original bytes are returned unchanged so there is zero cost
    when the PDF already has a clean CMap.
    """
    # Quick rejection: scan for "<E0" which only appears inside compressed
    # streams (not as literal bytes), so we must decompress first.  Since
    # this is cheap for typical PDFs (a few streams, small sizes), we skip
    # the byte-level pre-check and always walk through FlateDecode streams.

    result = bytearray(pdf_bytes)
    text = pdf_bytes.decode("latin1")
    modified = False

    # Find every FlateDecode stream and check if it contains beginbfchar with
    # PUA destination values.  We operate on raw bytes so we never risk
    # corrupting Devanagari by going through a text codec.
    for m in re.finditer(r"/Filter\s*\[?\s*/FlateDecode", text):
        # Walk forward to find the stream content
        obj_start = m.start()
        stream_marker = text.find("stream", obj_start)
        if stream_marker < 0:
            continue
        data_start = stream_marker + len("stream")
        # Skip optional \r\n or \n after "stream"
        if data_start < len(result) and result[data_start : data_start + 1] == b"\r":
            data_start += 1
        if data_start < len(result) and result[data_start : data_start + 1] == b"\n":
            data_start += 1
        stream_end = text.find("endstream", data_start)
        if stream_end < 0:
            continue
        # Trim trailing whitespace that is part of the PDF structure, not the
        # compressed data payload.
        raw = bytes(result[data_start:stream_end]).rstrip()

        # Try to decompress
        try:
            decoded = zlib.decompress(raw)
        except zlib.error:
            continue

        # Only process CMap streams (they contain "beginbfchar")
        if b"beginbfchar" not in decoded:
            continue

        # Strip PUA entries: replace each "<XX> <E0YY>" line with nothing
        cleaned = _PUA_RE.sub(b"", decoded)
        if cleaned == decoded:
            continue  # no PUA entries in this CMap

        # Re-compress
        compressed = zlib.compress(cleaned)
        # Replace the original stream data in-place, padding to keep
        # the byte offsets of later objects intact.
        orig_len = len(raw)
        new_len = len(compressed)
        if new_len <= orig_len:
            # Pad with spaces (0x20) which are whitespace in PDF and thus ignored
            compressed = compressed + b" " * (orig_len - new_len)
            result[data_start : data_start + orig_len] = compressed
            modified = True
        else:
            # Re-compressed data is larger — very unlikely for this operation,
            # but if it happens we can't fix this stream without rewriting the
            # xref table.  Log a warning and skip this stream.
            logger.warning(
                "[pdf] _fix_pua_tounicode: compressed size grew from %d to %d; skipping stream",
                orig_len, new_len,
            )

    return bytes(result) if modified else pdf_bytes


def build_settlement_pdf(
    trip: dict,
    expenses: list[dict],
    manager_consent_name: str | None = None,
    driver_consent_name: str | None = None,
    renderer: str = "reportlab",
) -> bytes:
    """Render the bilingual Dr/Cr settlement voucher PDF.

    Delegates all arithmetic to `compute_settlement` (single source). Emits a
    double-entry ledger (Goods Sale + Advance on Cr; expense buckets + Driver
    Batta on Dr), a net-settlement card, a verification fingerprint footer, and
    when consent data are present (Option 1) a bilingual consent block with the
    manager's and driver's acceptance names + DB-authoritative timestamps.

    *renderer* selects the backend: ``reportlab`` (default, pure-Python, always
    available) or ``weasyprint`` (Jinja2 HTML/CSS template via Pango/HarfBuzz).
    If WeasyPrint is requested but its native libs are absent, it transparently
    falls back to reportlab.
    """
    s = compute_settlement(trip, expenses)

    # MISC free-text ("what was it for") printed as sub-lines of the
    # Misc & Loading ledger row on the voucher (both renderers).
    misc_notes = [
        (str(e.get("raw_receipt_text") or "").strip(), float(e.get("amount") or 0.0))
        for e in expenses
        if e.get("exp_type") == "MISC"
        and str(e.get("raw_receipt_text") or "").strip()
    ]

    if renderer == "weasyprint" and _WEASYPRINT_AVAILABLE:
        try:
            return _render_weasyprint(
                _build_weasyprint_context(
                    trip, s, manager_consent_name, driver_consent_name,
                    misc_notes=misc_notes,
                )
            )
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("[pdf] weasyprint render failed, using reportlab: %s", exc)
    elif renderer == "weasyprint":
        logger.warning("[pdf] renderer='weasyprint' requested but unavailable; using reportlab")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontName=_FONT_NAME, boldFontName=_FONT_NAME, fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"), shaping=True)
    sub_style = _hi_style(styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#0284c7"))
    meta_style = _hi_style(styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#334155"))

    story.append(Paragraph("<b>VahanKhata</b>", title_style))
    story.append(Paragraph("Official Trip Settlement & Advance Reconciliation Ledger", sub_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph("TRIP SETTLEMENT VOUCHER / यात्रा हिसाब पर्ची", meta_style))
    story.append(Spacer(1, 10))

    odo_dist = (trip.get("end_odo") or trip.get("current_odo") or 0) - (trip.get("start_odo") or 0)
    km_text = f"{odo_dist:,.0f} KM"
    km_avg = f"Avg: {s.avg_kml:.2f} km/L" if s.avg_kml is not None else "Avg: N/A"
    meta_text = (
        f"<b>Trip Code:</b> {trip.get('trip_code')} &nbsp;|&nbsp; <b>Vehicle No:</b> {trip.get('vehicle_no')}"
        f" &nbsp;|&nbsp; <b>Driver:</b> {trip.get('driver_name')} ({trip.get('driver_phone')})"
    )
    story.append(Paragraph(meta_text, meta_style))
    route_text = (
        f"{trip.get('origin') or 'Origin'} ➔ {trip.get('destination') or 'Destination'}"
        f" &nbsp;|&nbsp; <b>Distance:</b> {km_text} &nbsp;|&nbsp; {km_avg}"
    )
    story.append(Paragraph(route_text, meta_style))
    story.append(Spacer(1, 12))

    return _fix_pua_tounicode(_render_pdf(doc, buffer, story, styles, s, trip, manager_consent_name, driver_consent_name))


def _render_pdf(
    doc, buffer, story, styles, s, trip,
    manager_consent_name, driver_consent_name,
    misc_notes: list[tuple[str, float]] | None = None,
) -> bytes:
    """Build the body flowables for a `SettlementResult` ledger + footer."""
    cell_style = _hi_style(styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#1e293b"))

    # ---- Double-entry Dr/Cr ledger ---------------------------------------
    story.append(Paragraph("<b>Bilingual Double-Entry Ledger / दोहरी प्रविष्टि हिसाब</b>", _hi_style(styles["Heading3"])))
    story.append(Spacer(1, 6))

    ledger_rows = [[
        Paragraph("<b>Particulars / विवरण</b>", cell_style),
        Paragraph("<b>Debit Dr / खर्चे</b>", cell_style),
        Paragraph("<b>Credit Cr / प्राप्ति</b>", cell_style),
    ]]

    # Credit side: Advance + Goods Sale.
    ledger_rows.append([
        Paragraph("Trip Cash Advance Issued / प्रारंभिक अग्रिम राशि", cell_style),
        Paragraph("—", cell_style),
        Paragraph(f"<b>{_rs(s.advance_amount)}</b>", cell_style),
    ])
    ledger_rows.append([
        Paragraph("Goods Sales Income / माल विक्री आय", cell_style),
        Paragraph("—", cell_style),
        Paragraph(_rs(s.goods_income), cell_style),
    ])

    # Debit side: itemize every non-zero expense bucket, then Driver Batta.
    for bucket in ("FUEL", "DEF", "TOLL", "REPAIR", "CHALLAN", "MISC", "GOODS_BUY"):
        amount = s.expense_buckets.get(bucket, 0.0)
        if amount == 0.0:
            continue
        en, hi = BUCKET_LABELS[bucket]
        label = _bi(en, hi)
        if bucket == "MISC":
            label += _misc_sublines(misc_notes or [])
        ledger_rows.append([
            Paragraph(label, cell_style),
            Paragraph(f"<b>{_rs(amount)}</b>", cell_style),
            Paragraph("—", cell_style),
        ])
    ledger_rows.append([
        Paragraph("<b>Driver Trip Salary / चालक ट्रिप भत्ता</b>", cell_style),
        Paragraph(f"<b>{_rs(s.driver_batta)}</b>", cell_style),
        Paragraph("—", cell_style),
    ])

    # Closing entry: the approved cash handover that zeroes Dr/Cr.
    if s.settlement_transfer:
        dr = s.settlement_transfer_side == "DR"
        ledger_rows.append([
            Paragraph(_bi("Cash Settlement Transfer", "निपटान रोकड़ भुगतान"), cell_style),
            Paragraph(f"<b>{_rs(s.settlement_transfer)}</b>" if dr else "—", cell_style),
            Paragraph("—" if dr else f"<b>{_rs(s.settlement_transfer)}</b>", cell_style),
        ])

    # Subtotal row.
    ledger_rows.append([
        Paragraph("<b>Subtotal / कुल योग</b>", cell_style),
        Paragraph(f"<b>{_rs(s.total_driver_credits)}</b>", cell_style),
        Paragraph(f"<b>{_rs(s.total_cr)}</b>", cell_style),
    ])

    t_ledger = Table(ledger_rows, colWidths=[300, 90, 90])
    t_ledger.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
    ]))
    story.append(t_ledger)
    story.append(Spacer(1, 15))

    # ---- Closing-entry callout (driver acceptance evidence) ----------------
    if s.settlement_transfer:
        direction = (
            "Driver returned to Fleet / चालक द्वारा वापसी"
            if s.settlement_transfer_side == "DR"
            else "Paid to Driver / चालक को भुगतान"
        )
        story.append(Paragraph(
            f"<b>Cash Settlement Paid &amp; Accepted / निपटान रोकड़ भुगतान स्वीकृत:</b> "
            f"{_rs(s.settlement_transfer)} &nbsp;({direction})",
            cell_style,
        ))
        story.append(Spacer(1, 8))

    # ---- Net settlement card ---------------------------------------------
    net_color = colors.HexColor("#16a34a") if s.net_balance >= 0 else colors.HexColor("#dc2626")
    net_box = Table(
        [[Paragraph(
            f"<b>NET SETTLEMENT / अंतिम शेष राशि:</b> {_rs(abs(s.net_balance))}",
            cell_style,
        ),
          Paragraph(f"[ {s.status_label_en} / {s.status_label_hi} ]", cell_style)]],
        colWidths=[200, 200],
    )
    net_box.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1.5, net_color),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(net_box)
    story.append(Spacer(1, 12))

    # ---- Consent block (Option 1): manager + driver acceptance ---------
    if manager_consent_name or driver_consent_name or trip.get("manager_consent_at") or trip.get("driver_consent_at"):
        story.append(Paragraph(
            "<b>CONSENT &amp; ACCEPTANCE / स्वीकृति एवं स्वीकार</b>",
            _hi_style(styles["Heading3"]),
        ))
        story.append(Spacer(1, 4))
        consent_rows = [
            [
                Paragraph("<b>Fleet Manager Acceptance / प्रबंधक स्वीकृति</b>", cell_style),
                Paragraph(
                    f"{manager_consent_name or '—'} &nbsp;|&nbsp; {_fmt_ts(trip.get('manager_consent_at'))}",
                    cell_style,
                ),
                Paragraph("☐" if manager_consent_name else "—", cell_style),
            ],
            [
                Paragraph("<b>Driver Acceptance / चालक स्वीकृति</b>", cell_style),
                Paragraph(
                    f"{driver_consent_name or '—'} &nbsp;|&nbsp; {_fmt_ts(trip.get('driver_consent_at'))}",
                    cell_style,
                ),
                Paragraph("☐" if driver_consent_name else "—", cell_style),
            ],
        ]
        t_consent = Table(consent_rows, colWidths=[200, 250, 30])
        t_consent.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t_consent)
        story.append(Spacer(1, 12))

    # ---- Verification fingerprint -----------------------------------------
    story.append(Paragraph(
        f"<b>Verification Code:</b> VHK-{s.verification_hash}",
        cell_style,
    ))
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "Driver Signature: ___________________     Fleet Manager Sign-off: ___________________",
        cell_style,
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
