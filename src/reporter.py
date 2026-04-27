"""E-Mail-Tagesbericht nach jedem Zefix-Prüflauf."""

import logging
import os
import smtplib
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

REPORT_TO   = os.getenv("REPORT_TO",   "migmar.nyima@gmail.com")
SMTP_HOST   = os.getenv("SMTP_HOST",   "smtp.gmail.com")
SMTP_PORT   = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER   = os.getenv("SMTP_USER",   "")       # GitHub Secret: SMTP_USER
SMTP_PASS   = os.getenv("SMTP_PASS",   "")       # GitHub Secret: SMTP_PASS


# ---------------------------------------------------------------------------
# HTML-Template
# ---------------------------------------------------------------------------

_STYLE = """
  body  { font-family: Helvetica, Arial, sans-serif; color: #2c2c2c; margin: 0; padding: 0; }
  .wrap { max-width: 640px; margin: 0 auto; }
  .hdr  { background: #1a3a5c; color: #fff; padding: 24px 28px; }
  .hdr h2 { margin: 0 0 4px; font-size: 20px; }
  .hdr p  { margin: 0; font-size: 13px; opacity: .8; }
  .body { padding: 24px 28px; }
  .badge-ok  { background:#e8f8f0; border-left:4px solid #27ae60;
               padding:14px 18px; border-radius:3px; margin-bottom:20px; }
  .badge-ok h3  { color:#1e8449; margin:0 0 4px; font-size:16px; }
  .badge-nil { background:#f4f6f7; border-left:4px solid #aab7b8;
               padding:14px 18px; border-radius:3px; margin-bottom:20px; }
  .badge-nil h3 { color:#717d7e; margin:0 0 4px; font-size:16px; }
  table  { width:100%; border-collapse:collapse; font-size:13px; margin-top:12px; }
  th     { background:#1a3a5c; color:#fff; padding:9px 11px; text-align:left; }
  td     { padding:8px 11px; border-bottom:1px solid #eaecee; vertical-align:top; }
  tr:last-child td { border-bottom:none; }
  .ftr   { font-size:11px; color:#aaa; padding:16px 28px 24px;
           border-top:1px solid #eaecee; }
"""

_MONTHS = [
    "Januar","Februar","März","April","Mai","Juni",
    "Juli","August","September","Oktober","November","Dezember",
]

def _html_report(new_firms: list[dict], check_time: datetime) -> str:
    today_str = f"{check_time.day}. {_MONTHS[check_time.month - 1]} {check_time.year}"

    if new_firms:
        count    = len(new_firms)
        firma_pl = "Firmen" if count > 1 else "Firma"
        badge  = f"""
        <div class=\"badge-ok\">
          <h3>&#10003; {count} neue {firma_pl} eingetragen</h3>
          <p style=\"margin:0;font-size:13px;\">
            Im Bezirk Muri wurden heute {count} neue {firma_pl}
            im Handelsregister eingetragen. Die entsprechenden Briefe wurden generiert.
          </p>
        </div>"""

        rows = "".join(
            f"<tr>"
            f"<td><strong>{f['name']}</strong></td>"
            f"<td>{f.get('legalSeat','–')}</td>"
            f"<td>{f.get('registrationDate','–')}</td>"
            f"<td>{_fmt_addr(f.get('address'))}</td>"
            f"</tr>"
            for f in new_firms
        )
        table = f"""
        <table>
          <tr>
            <th>Firma</th>
            <th>Gemeinde</th>
            <th>Eingetragen</th>
            <th>Adresse</th>
          </tr>
          {rows}
        </table>"""
        main_block = badge + table
    else:
        main_block = """
        <div class=\"badge-nil\">
          <h3>Keine Neueintragungen heute</h3>
          <p style=\"margin:0;font-size:13px;\">
            Im Bezirk Muri wurden heute keine neuen Firmen im Handelsregister
            eingetragen. Morgen wird erneut geprüft.
          </p>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang=\"de\">
<head>
  <meta charset=\"UTF-8\">
  <style>{_STYLE}</style>
</head>
<body>
<div class=\"wrap\">
  <div class=\"hdr\">
    <h2>Zefix Tagesbericht &ndash; Bezirk Muri</h2>
    <p>Advisia &nbsp;|&nbsp; {today_str}</p>
  </div>
  <div class=\"body\">
    {main_block}
  </div>
  <div class=\"ftr\">
    Automatisch generiert von Advisia Zefix-Checker &nbsp;&bull;&nbsp;
    {check_time.strftime('%d.%m.%Y %H:%M:%S')} &nbsp;&bull;&nbsp;
    <a href=\"mailto:info@advisia.ch\" style=\"color:#aaa;\">info@advisia.ch</a>
  </div>
</div>
</body>
</html>"""


def _fmt_addr(addr: dict | None) -> str:
    if not addr:
        return "–"
    parts = []
    street = addr.get("street", "")
    hnr    = addr.get("houseNumber", "")
    if street:
        parts.append(f"{street} {hnr}".strip())
    zip_   = addr.get("swissZipCode") or addr.get("zipCode", "")
    city   = addr.get("city", "")
    if zip_ or city:
        parts.append(f"{zip_} {city}".strip())
    return ", ".join(parts) or "–"


def _subject(new_firms: list[dict]) -> str:
    today = date.today().strftime("%d.%m.%Y")
    if new_firms:
        n = len(new_firms)
        return f"Zefix Bezirk Muri {today} – {n} neue {'Firmen' if n > 1 else 'Firma'} eingetragen"
    return f"Zefix Bezirk Muri {today} – Keine Neueintragungen"


# ---------------------------------------------------------------------------
# Senden
# ---------------------------------------------------------------------------

def send_report(new_firms: list[dict], check_time: datetime | None = None) -> bool:
    """Tagesbericht per E-Mail senden. Gibt True zurück bei Erfolg."""
    if not SMTP_USER or not SMTP_PASS:
        logger.warning(
            "SMTP_USER / SMTP_PASS nicht gesetzt – E-Mail-Versand übersprungen."
        )
        return False

    check_time = check_time or datetime.now()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = _subject(new_firms)
    msg["From"]    = f"Advisia Zefix-Checker <{SMTP_USER}>"
    msg["To"]      = REPORT_TO

    html = _html_report(new_firms, check_time)
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [REPORT_TO], msg.as_bytes())
        logger.info("Tagesbericht gesendet an %s", REPORT_TO)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("E-Mail-Versand fehlgeschlagen: %s", exc)
        return False
