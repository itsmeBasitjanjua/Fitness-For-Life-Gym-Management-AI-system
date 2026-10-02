"""
Monthly PDF report: members & fees, payment ledger, staff salaries, expenses, profit.

Layout (landscape A4):
  1. Overview numbers
  2. All members with plan fee, fee status, last payment DATE + TIME + METHOD
  3. Payment ledger for the month (every payment with date, time and method)
  4. Staff salaries (paid/unpaid, date + time + method)
  5. Expenses
  6. Financial summary (income - expenses - salaries = net profit)
"""
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from gym_ai import config
from gym_ai.services import expenses, payments, reports, staff
from gym_ai.utils import now_str, validate_month

# ---------- look & feel ----------
DARK = colors.HexColor("#1f2937")
ACCENT = colors.HexColor("#0f766e")
ZEBRA = colors.HexColor("#f3f4f6")
GREEN, RED, AMBER = "#15803d", "#b91c1c", "#b45309"

_styles = getSampleStyleSheet()
CELL = ParagraphStyle("cell", parent=_styles["Normal"], fontSize=7.5, leading=9)
CELL_RIGHT = ParagraphStyle("cell_right", parent=CELL, alignment=2)
HEAD = ParagraphStyle("head", parent=CELL, textColor=colors.white, fontName="Helvetica-Bold")
SECTION = ParagraphStyle("section", parent=_styles["Heading2"], textColor=ACCENT, spaceBefore=14, spaceAfter=6)


def _fmt(amount) -> str:
    return f"{amount:,.0f}"


def _p(text, style=CELL) -> Paragraph:
    return Paragraph(escape(str(text)) if text not in (None, "") else "-", style)


def _status_cell(status: str) -> Paragraph:
    color = {"Paid": GREEN, "Prepaid": GREEN, "Unpaid": RED, "Inactive": AMBER}.get(status, "#000000")
    return Paragraph(f'<font color="{color}"><b>{status}</b></font>', CELL)


def _build_table(header: list[str], rows: list[list], widths: list[float], right_cols=(), total_row=False) -> Table:
    """Create a styled table. `rows` already contain Paragraph objects or strings."""
    data = [[Paragraph(h, HEAD) for h in header]] + rows
    table = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if total_row:
        style += [("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ccfbf1")),
                  ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]
    table.setStyle(TableStyle(style))
    return table


def _empty(message: str) -> Paragraph:
    return Paragraph(f"<i>{message}</i>", _styles["Normal"])


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.grey)
    canvas.drawString(30, 18, f"{config.GYM_NAME} - generated {now_str()}")
    canvas.drawRightString(landscape(A4)[0] - 30, 18, f"Page {doc.page}")
    canvas.restoreState()


# ---------- the sections ----------
def _overview(month, members, summary):
    paid = sum(1 for m in members if m["fee_status"] in ("Paid", "Prepaid"))
    unpaid = sum(1 for m in members if m["fee_status"] == "Unpaid")
    data = [
        [_p("Total members"), _p(len(members)), _p("Fees collected"), _p(f"{config.CURRENCY} {_fmt(summary['income_total'])}")],
        [_p("Paid / prepaid"), _p(paid), _p("Expenses"), _p(f"{config.CURRENCY} {_fmt(summary['expenses_total'])}")],
        [_p("Unpaid"), _p(unpaid), _p("Salaries paid"), _p(f"{config.CURRENCY} {_fmt(summary['salaries_paid'])}")],
    ]
    table = Table(data, colWidths=[110, 90, 110, 140])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                               ("BACKGROUND", (0, 0), (0, -1), ZEBRA), ("BACKGROUND", (2, 0), (2, -1), ZEBRA)]))
    return table


def _members_section(members):
    header = ["ID", "Name", "Phone", "Plan", f"Fee ({config.CURRENCY})", "Joined", "Expiry",
              "Fee status", f"Paid this month", "Last payment (date & time)", "Method"]
    widths = [30, 105, 82, 65, 55, 62, 62, 60, 62, 108, 91]
    rows = [[_p(m["id"]), _p(m["name"]), _p(m["phone"]), _p(m["plan_name"]),
             _p(_fmt(m["plan_fee"]) if m["plan_fee"] else "-", CELL_RIGHT),
             _p(m["join_date"]), _p(m["membership_expiry"]), _status_cell(m["fee_status"]),
             _p(_fmt(m["paid_in_month"]) if m["paid_in_month"] else "-", CELL_RIGHT),
             _p(m["last_paid_at"]), _p(m["last_method"])] for m in members]
    return _build_table(header, rows, widths) if rows else _empty("No members yet.")


def _ledger_section(ledger):
    header = ["Receipt", "Member", f"Amount ({config.CURRENCY})", "Method", "Date & time"]
    widths = [140, 220, 100, 120, 200]
    rows = [[_p(p["receipt_no"]), _p(f"{p['member_name']} (ID {p['member_id']})"),
             _p(_fmt(p["amount"]), CELL_RIGHT), _p(p["method"]), _p(p["paid_at"])] for p in ledger]
    if not rows:
        return _empty("No payments received this month.")
    rows.append([_p("TOTAL"), _p(""), _p(_fmt(sum(p["amount"] for p in ledger)), CELL_RIGHT), _p(""), _p("")])
    return _build_table(header, rows, widths, total_row=True)


def _salary_section(salaries):
    header = ["ID", "Staff member", "Role", f"Monthly salary ({config.CURRENCY})", "Status", "Paid on (date & time)", "Method"]
    widths = [30, 150, 110, 120, 70, 160, 140]
    rows = [[_p(s["id"]), _p(s["name"]), _p(s["role"]), _p(_fmt(s["monthly_salary"]), CELL_RIGHT),
             _status_cell(s["status"]), _p(s["paid_at"]), _p(s["method"])] for s in salaries]
    if not rows:
        return _empty("No staff registered.")
    paid = sum(s["paid_amount"] for s in salaries if s["paid_amount"])
    rows.append([_p(""), _p("TOTAL PAID"), _p(""), _p(_fmt(paid), CELL_RIGHT), _p(""), _p(""), _p("")])
    return _build_table(header, rows, widths, total_row=True)


def _expense_section(items):
    header = ["Date & time", "Category", "Description", f"Amount ({config.CURRENCY})"]
    widths = [140, 130, 360, 150]
    rows = [[_p(e["spent_at"]), _p(e["category"]), _p(e["description"]), _p(_fmt(e["amount"]), CELL_RIGHT)] for e in items]
    if not rows:
        return _empty("No expenses recorded this month.")
    rows.append([_p("TOTAL"), _p(""), _p(""), _p(_fmt(sum(e["amount"] for e in items)), CELL_RIGHT)])
    return _build_table(header, rows, widths, total_row=True)


def _summary_section(summary):
    net = summary["net_profit"]
    net_color = GREEN if net >= 0 else RED
    rows = [
        [_p("Fees collected (income)"), _p(_fmt(summary["income_total"]), CELL_RIGHT)],
        [_p("Less: expenses"), _p(f"- {_fmt(summary['expenses_total'])}", CELL_RIGHT)],
        [_p("Less: staff salaries paid"), _p(f"- {_fmt(summary['salaries_paid'])}", CELL_RIGHT)],
        [Paragraph("<b>NET PROFIT / (LOSS)</b>", CELL),
         Paragraph(f'<font color="{net_color}"><b>{_fmt(net)}</b></font>', CELL_RIGHT)],
        [_p("Salaries still unpaid"), _p(_fmt(summary["salaries_still_unpaid"]), CELL_RIGHT)],
    ]
    table = Table(rows, colWidths=[250, 130])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                               ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#ccfbf1"))]))
    return table


# ---------- public function ----------
def generate_monthly_pdf(month: str | None = None, output_path: str | None = None) -> str:
    """Build the report and return the PDF file path."""
    month = validate_month(month)
    summary = reports.monthly_financial_summary(month)
    members = reports.members_fee_table(month)

    out = Path(output_path) if output_path else config.REPORTS_DIR / f"gym_report_{month}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(str(out), pagesize=landscape(A4), leftMargin=30, rightMargin=30,
                            topMargin=30, bottomMargin=34, title=f"{config.GYM_NAME} report {month}")
    title = ParagraphStyle("title", parent=_styles["Title"], textColor=DARK, alignment=0, fontSize=20)
    story = [
        Paragraph(config.GYM_NAME, title),
        Paragraph(f"Members, Fees &amp; Finance Report - <b>{month}</b>", _styles["Heading3"]),
        Spacer(1, 6),
        _overview(month, members, summary),
        Paragraph("1. All members and fees", SECTION), _members_section(members),
        Paragraph("2. Payments received this month", SECTION), _ledger_section(payments.payments_in_month(month)),
        Paragraph("3. Staff salaries", SECTION), _salary_section(staff.salary_status(month)),
        Paragraph("4. Expenses", SECTION), _expense_section(expenses.list_expenses(month)),
        Paragraph("5. Financial summary", SECTION), _summary_section(summary),
    ]
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return str(out)
