import os
import re
from datetime import date
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

GERMAN_MONTHS = {
    1: "Januar",    2: "Februar",  3: "März",      4: "April",
    5: "Mai",       6: "Juni",     7: "Juli",       8: "August",
    9: "September", 10: "Oktober", 11: "November",  12: "Dezember",
}

PAGE_W, PAGE_H = A4           # 595.27 x 841.89 pt
LEFT_M  = 25 * mm
RIGHT_M = 20 * mm
TOP_M   = 20 * mm
BOT_M   = 25 * mm
TW      = PAGE_W - LEFT_M - RIGHT_M   # usable text width


def _fmt_date(d: date) -> str:
    return f"{d.day}. {GERMAN_MONTHS[d.month]} {d.year}"


def safe_filename(text: str) -> str:
    return re.sub(r"[^\w\-]", "_", text)[:60]


def _styles() -> dict:
    base = getSampleStyleSheet()
    grey = colors.HexColor("#5a5a5a")
    dark = colors.black

    return {
        "sender_line": ParagraphStyle(
            "sender_line",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=grey,
            alignment=TA_LEFT,
        ),
        "date_right": ParagraphStyle(
            "date_right",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            alignment=TA_RIGHT,
        ),
        "address": ParagraphStyle(
            "address",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
        ),
        "subject": ParagraphStyle(
            "subject",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            leftIndent=12,
            bulletIndent=0,
            spaceAfter=2,
        ),
        "bold": ParagraphStyle(
            "bold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "footer",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=grey,
            alignment=TA_CENTER,
        ),
    }


def _draw_header(c: canvas.Canvas, sender: dict) -> None:
    """Draw sender line + rule at the top of each page."""
    c.saveState()
    c.setFont("Helvetica-Bold", 9)
    c.setFillColorRGB(0.35, 0.35, 0.35)
    sender_line = (
        f"{sender['company']}  ·  "
        f"{sender['address']}  ·  "
        f"{sender['zip_city']}"
    )
    y_top = PAGE_H - TOP_M
    c.drawString(LEFT_M, y_top, sender_line)
    c.setStrokeColorRGB(0.7, 0.7, 0.7)
    c.setLineWidth(0.5)
    c.line(LEFT_M, y_top - 3 * mm, PAGE_W - RIGHT_M, y_top - 3 * mm)
    c.restoreState()


def _draw_footer(c: canvas.Canvas, sender: dict, page_num: int) -> None:
    c.saveState()
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    parts = [sender.get("company", ""), sender.get("zip_city", "")]
    for key in ("phone", "email", "website"):
        if sender.get(key):
            parts.append(sender[key])
    text = "  |  ".join(p for p in parts if p)
    c.drawCentredString(PAGE_W / 2, BOT_M / 2, text)
    c.restoreState()


def _make_canvas_factory(sender: dict):
    """Return a canvas-maker that injects header/footer on every page."""

    class _HeaderFooterCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._page_count = 0

        def showPage(self):
            self._page_count += 1
            _draw_header(self, sender)
            _draw_footer(self, sender, self._page_count)
            super().showPage()

        def save(self):
            _draw_header(self, sender)
            _draw_footer(self, sender, self._page_count + 1)
            super().save()

    return _HeaderFooterCanvas


def generate_letter(
    company: dict,
    address: Optional[dict],
    sender: dict,
    output_path: str,
) -> None:
    """Generate a DIN-A4 PDF congratulation letter for a newly registered company."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    styles = _styles()
    company_name = company.get("name", "")
    today = date.today()

    city_prefix = (sender.get("zip_city") or "").split()[0]
    date_str = f"{city_prefix}, {_fmt_date(today)}"

    # Build recipient address lines
    addr_lines = [company_name]
    if address:
        street   = address.get("street", "")
        house_nr = address.get("houseNumber", "")
        zip_code = address.get("swissZipCode") or address.get("zipCode", "")
        city_nm  = address.get("city", "")
        if street:
            addr_lines.append(f"{street} {house_nr}".strip())
        if zip_code or city_nm:
            addr_lines.append(f"{zip_code} {city_nm}".strip())
    else:
        legal_seat = company.get("legalSeat", "")
        if legal_seat:
            addr_lines.append(legal_seat)

    def _p(text: str, style: str) -> Paragraph:
        return Paragraph(text, styles[style])

    story = [
        Spacer(1, 6 * mm),
        # Date
        _p(date_str, "date_right"),
        Spacer(1, 8 * mm),
        # Recipient
        *[_p(line, "address") for line in addr_lines],
        Spacer(1, 10 * mm),
        # Subject
        _p(f"Herzlichen Glückwunsch zur Gründung von «{company_name}»", "subject"),
        Spacer(1, 5 * mm),
        # Salutation
        _p("Sehr geehrte Damen und Herren", "body"),
        Spacer(1, 3 * mm),
        # Body 1
        _p(
            f"herzlichen Glückwunsch zur Eintragung Ihrer Firma «{company_name}» "
            f"im Handelsregister! Als regionale Buchhaltungsgesellschaft im Bezirk "
            f"Muri heissen wir Sie herzlich in der Unternehmerwelt willkommen.",
            "body",
        ),
        # Body 2
        _p(
            "Ein Unternehmensstart bringt viele spannende Möglichkeiten, aber auch "
            "Herausforderungen – gerade im Bereich Rechnungswesen und Buchhaltung. "
            "Genau hier möchten wir Ihnen zur Seite stehen: mit einer einfachen, "
            "unkomplizierten und regional zentralisierten externen Buchhaltung.",
            "body",
        ),
        Spacer(1, 2 * mm),
        _p("Unsere Leistungen für Ihr Unternehmen:", "bold"),
    ]

    for svc in (
        "Externe Buchführung und Jahresabschluss",
        "Lohnbuchhaltung und Sozialversicherungen",
        "Mehrwertsteuerabrechnungen (MWST)",
        "Steuerberatung und Steuererklärung",
        "Budgetplanung und Finanzberatung",
    ):
        story.append(_p(f"&#9632;  {svc}", "bullet"))

    story += [
        Spacer(1, 4 * mm),
        _p(
            "Wir sind regional verwurzelt und kennen die Gegebenheiten im Bezirk "
            "Muri bestens. Eine persönliche, unkomplizierte Zusammenarbeit liegt "
            "uns am Herzen.",
            "body",
        ),
        _p(
            "Gerne stellen wir Ihnen unsere Dienstleistungen in einem unverbindlichen "
            "Erstgespräch vor. Rufen Sie uns einfach an oder schreiben Sie uns – "
            "wir melden uns umgehend bei Ihnen!",
            "body",
        ),
        Spacer(1, 8 * mm),
        _p("Freundliche Grüsse", "body"),
        Spacer(1, 14 * mm),
        _p(f"<b>{sender.get('company', '')}</b>", "body"),
    ]

    if sender.get("name"):
        story.append(_p(sender["name"], "body"))

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=LEFT_M,
        rightMargin=RIGHT_M,
        topMargin=TOP_M + 10 * mm,   # extra room for header line
        bottomMargin=BOT_M,
    )
    doc.build(story, canvasmaker=_make_canvas_factory(sender))
