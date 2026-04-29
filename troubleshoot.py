"""
Troubleshoot-Script – prüft alle Systemkomponenten und sendet eine Test-E-Mail.
Sendet IMMER eine E-Mail: entweder mit Neueintragungen oder «Keine Neueintragungen».

Aufruf:
  RESEND_API_KEY=re_xxx python troubleshoot.py
"""

import os
import sys
import requests
from datetime import datetime, date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

OK  = "\033[92m✓\033[0m"
ERR = "\033[91m✗\033[0m"
INF = "\033[94m→\033[0m"

def check(label, fn):
    try:
        result = fn()
        print(f"  {OK}  {label}" + (f": {result}" if result else ""))
        return True
    except Exception as exc:
        print(f"  {ERR}  {label}: {exc}")
        return False

print()
print("=" * 55)
print("  Advisia SHAB-Checker Kanton AG – Troubleshoot")
print("=" * 55)

print(f"\n{INF} 1. Python-Module")
for mod in ("requests", "reportlab"):
    check(f"import {mod}", lambda m=mod: __import__(m) and None)

print(f"\n{INF} 2. Konfiguration (src/config.py)")
from config import SENDER_INFO, CANTON_ID
check("Absender Firma",   lambda: SENDER_INFO["company"])
check("Absender Adresse", lambda: f"{SENDER_INFO['address']}, {SENDER_INFO['zip_city']}")
check("Absender E-Mail",  lambda: SENDER_INFO["email"])
check("Kanton",           lambda: f"Kanton {CANTON_ID}")

print(f"\n{INF} 3. SHAB API – Verbindungstest")
def test_shab():
    today = date.today().isoformat()
    resp = requests.get(
        "https://www.shab.ch/api/eshab/entries",
        params={
            "publicationStates": "PUBLISHED",
            "cantons": CANTON_ID,
            "since": today,
            "until": today,
            "pageRequest.page": 0,
            "pageRequest.size": 1,
        },
        headers={"Accept": "application/json"},
        timeout=15,
    )
    if resp.status_code == 200:
        data = resp.json()
        total = data.get("totalElements", "?") if isinstance(data, dict) else len(data)
        return f"HTTP 200 – {total} Einträge heute in AG"
    return f"HTTP {resp.status_code}"
check("SHAB API erreichbar", test_shab)

print(f"\n{INF} 4. SHAB NE-Suche (heute)")
from shab_client import get_new_registrations
def test_shab_ne():
    firms = get_new_registrations(canton=CANTON_ID, check_date=date.today())
    return f"{len(firms)} NE-Einträge heute gefunden"
check("SHAB NE-Einträge abrufen", test_shab_ne)

print(f"\n{INF} 5. PDF-Briefgenerierung")
from letter_generator import generate_letter
import tempfile, pathlib
DEMO_FIRM = {"uid": "CHE-999.000.001", "name": "Beispiel Handels GmbH",
             "legalSeat": "Aarau", "registrationDate": datetime.now().strftime("%Y-%m-%d")}
DEMO_ADDR = {"street": "Bahnhofstrasse", "houseNumber": "10",
             "swissZipCode": "5000", "city": "Aarau"}
with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
    tmp_pdf = tf.name
check("PDF generieren", lambda: (
    generate_letter(DEMO_FIRM, DEMO_ADDR, SENDER_INFO, tmp_pdf),
    f"{pathlib.Path(tmp_pdf).stat().st_size:,} Bytes"
)[1])

print(f"\n{INF} 6. E-Mail-Tagesbericht (wird IMMER gesendet)")
from reporter import _html_report, _subject
now = datetime.now()
check("Betreff mit Firma",  lambda: _subject([DEMO_FIRM]))
check("Betreff ohne Firma", lambda: _subject([]))
check("HTML generieren",    lambda: f"{len(_html_report([DEMO_FIRM], now)):,} Zeichen")

api_key = os.getenv("RESEND_API_KEY", "")
if not api_key:
    print(f"  {ERR}  RESEND_API_KEY fehlt – als GitHub Secret hinterlegen")
else:
    print(f"  {OK}  RESEND_API_KEY gesetzt")
    def test_send():
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "from":    "Advisia SHAB-Checker <onboarding@resend.dev>",
                "to":      ["migmar.nyima@gmail.com"],
                "subject": f"[TEST] {_subject([DEMO_FIRM])}",
                "html":    _html_report([DEMO_FIRM], now),
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return f"Gesendet – ID: {resp.json().get('id','?')}"
        raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    check("Test-E-Mail an migmar.nyima@gmail.com", test_send)

print()
print("=" * 55)
print("  Fertig.")
print("=" * 55)
print()
