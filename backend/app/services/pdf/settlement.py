from __future__ import annotations

import io
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.app.services.audit.cash import compute_settlement

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

pdfmetrics.registerFont(TTFont(_FONT_NAME, os.path.join(_FONTS_DIR, _FONT_FILE)))

_HI_STYLE_CTR = [0]


def _hi_style(parent, **kwargs) -> ParagraphStyle:
    """Return a ParagraphStyle using the Devanagari font (for bilingual text).

    Sets both ``fontName`` and ``boldFontName`` so reportlab's inline ``<b>``
    markup keeps using the same font instead of falling back to Helvetica-Bold
    (which would drop the Devanagari glyphs again).
    """
    kwargs.setdefault("fontName", _FONT_NAME)
    kwargs.setdefault("boldFontName", _FONT_NAME)
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


def build_settlement_pdf(trip: dict, expenses: list[dict]) -> bytes:
    """Render the bilingual Dr/Cr settlement voucher PDF.

    Delegates all arithmetic to `compute_settlement` (single source). Emits a
    double-entry ledger (Goods Sale + Advance on Cr; expense buckets + Driver
    Batta on Dr), a net-settlement card, and a verification fingerprint footer.
    """
    s = compute_settlement(trip, expenses)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontName=_FONT_NAME, boldFontName=_FONT_NAME, fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"))
    sub_style = _hi_style(styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#0284c7"))
    meta_style = _hi_style(styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#334155"))
    cell_style = _hi_style(styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#1e293b"))
    hi_style = _hi_style(styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#64748b"))

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

    return _render_pdf(doc, buffer, story, styles, s)


def _render_pdf(doc, buffer, story, styles, s) -> bytes:
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
        ledger_rows.append([
            Paragraph(f"{en} / {hi}", cell_style),
            Paragraph(f"<b>{_rs(amount)}</b>", cell_style),
            Paragraph("—", cell_style),
        ])
    ledger_rows.append([
        Paragraph("<b>Driver Trip Salary / चालक ट्रिप भत्ता</b>", cell_style),
        Paragraph(f"<b>{_rs(s.driver_batta)}</b>", cell_style),
        Paragraph("—", cell_style),
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

    # ---- Verification fingerprint -----------------------------------------
    story.append(Paragraph(
        f"<b>Verification Code:</b> VHK-{s.verification_hash}",
        cell_style,
    ))
    story.append(Spacer(1, 35))

    story.append(Paragraph(
        "Driver Signature: ___________________     Fleet Manager Sign-off: ___________________",
        cell_style,
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
