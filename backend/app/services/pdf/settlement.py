"""Settlement PDF builder — reportlab, no GTK/system deps.

Extracted from `fleetflow_interactive_demo.py`'s `/generate-settlement-pdf` route
so the router stays a thin HTTP wrapper. Pure function: takes the trip row +
its expenses, returns the PDF bytes.
"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GOODS_EXPENSE_TYPES = ("GOODS_BUY", "GOODS_SALE")


def _is_approved(expense: dict) -> bool:
    return expense["manager_status"] == "APPROVED"


def _approved_cash_impact(expense: dict) -> float:
    if not _is_approved(expense):
        return 0.0
    return expense["amount"] if expense["exp_type"] == "GOODS_SALE" else -expense["amount"]


def build_settlement_pdf(trip: dict, expenses: list[dict]) -> bytes:
    """Render the settlement/reconciliation PDF for a settled (or active) trip."""
    total_approved = sum(
        e["amount"] for e in expenses if _is_approved(e) and e["exp_type"] != "GOODS_SALE"
    )
    total_income = sum(
        e["amount"] for e in expenses if _is_approved(e) and e["exp_type"] == "GOODS_SALE"
    )
    total_flagged = sum(e["amount"] for e in expenses if e["is_flagged"])
    trip_profit = sum(_approved_cash_impact(e) for e in expenses)
    net_returnable = trip["advance_amount"] + trip_profit

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("TitleStyle", parent=styles["Heading1"], fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"))
    sub_style = ParagraphStyle("SubStyle", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#0284c7"))
    meta_style = ParagraphStyle("MetaStyle", parent=styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#334155"))
    cell_style = ParagraphStyle("CellStyle", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#1e293b"))
    flag_style = ParagraphStyle("FlagStyle", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#dc2626"))

    story.append(Paragraph("<b>VahanKhata</b>", title_style))
    story.append(Paragraph("Official Trip Settlement & Advance Reconciliation Ledger", sub_style))
    story.append(Spacer(1, 10))

    odo_dist = trip["current_odo"] - trip["start_odo"]
    meta_text = (
        f"<b>Trip Code:</b> {trip['trip_code']} &nbsp;|&nbsp; <b>Vehicle No:</b> {trip['vehicle_no']} "
        f"&nbsp;|&nbsp; <b>Driver:</b> {trip['driver_name']} &nbsp;|&nbsp; <b>Distance Run:</b> {odo_dist:,.0f} KM"
    )
    story.append(Paragraph(meta_text, meta_style))
    story.append(Spacer(1, 12))

    summary_data = [
        [
            Paragraph("<b>Advance Issued</b>", cell_style),
            Paragraph("<b>Approved Expenses</b>", cell_style),
            Paragraph("<b>Approved Goods Income</b>", cell_style),
            Paragraph("<b>Flagged Deductions</b>", cell_style),
            Paragraph("<b>Cash Settlement</b>", cell_style),
        ],
        [
            Paragraph(f"<b>Rs. {trip['advance_amount']:,.2f}</b>", cell_style),
            Paragraph(f"<b>Rs. {total_approved:,.2f}</b>", cell_style),
            Paragraph(f"<b>Rs. {total_income:,.2f}</b>", cell_style),
            Paragraph(f"<font color='#dc2626'><b>Rs. {total_flagged:,.2f}</b></font>", cell_style),
            Paragraph(f"<font color='#16a34a'><b>Rs. {net_returnable:,.2f}</b></font>", cell_style),
        ],
    ]
    t_summary = Table(summary_data, colWidths=[104, 104, 104, 104, 104])
    t_summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>Itemized Expense Audit Trail</b>", styles["Heading3"]))
    story.append(Spacer(1, 6))

    table_data = [["Expense", "Claim Amount", "Operational Metrics", "Audit Verification", "Status"]]
    for e in expenses:
        details = (
            f"{e['liters']}L @ Rs. {e['rate']}/L (Odo: {e['odometer']} KM)"
            if e["exp_type"] in ("FUEL", "DEF")
            else f"Odo: {e['odometer']} KM"
        )
        audit_para = (
            Paragraph(f"<font color='#dc2626'><b>[FLAG]</b> {e['flag_reason']}</font>", flag_style)
            if e["is_flagged"]
            else Paragraph("<font color='#16a34a'><b>[VERIFIED]</b></font>", cell_style)
        )
        table_data.append([
            Paragraph(f"<b>{e['exp_type']}</b>", cell_style),
            Paragraph(f"Rs. {e['amount']:,.2f}", cell_style),
            Paragraph(details, cell_style),
            audit_para,
            Paragraph(f"<b>{e['manager_status']}</b>", cell_style),
        ])

    t_expenses = Table(table_data, colWidths=[60, 75, 170, 150, 65])
    t_expenses.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(t_expenses)
    story.append(Paragraph(f"<b>Net trip profit / loss after approved expenses:</b> Rs. {trip_profit:,.2f}", meta_style))

    story.append(Spacer(1, 35))
    sign_data = [["Driver Signature: ___________________", "Fleet Manager Sign-off: ___________________"]]
    story.append(Table(sign_data, colWidths=[260, 260]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
