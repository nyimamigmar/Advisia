"""
Demo-Script: Simuliert einen kompletten Zefix-Prüflauf mit realistischen Testdaten.

Ablauf:
  1. Simulierte Zefix-Antwort mit 3 «neuen» Firmen im Bezirk Muri
  2. Adressrecherche (ebenfalls simuliert)
  3. PDF-Briefgenerierung für jede neue Firma
  4. Tagesbericht-HTML-Vorschau (E-Mail-Versand nur wenn SMTP_USER/SMTP_PASS gesetzt)
  5. Ausgabe der Statusdatei

Aufruf:  python demo.py
"""

import json
import logging
import os
import sys

# Damit die Imports aus src/ funktionieren
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from letter_generator import generate_letter, safe_filename
from config import SENDER_INFO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Simulierte Zefix-Daten – so würde die echte API antworten
# ---------------------------------------------------------------------------

MOCK_NEW_FIRMS = [
    {
        "uid": "CHE-498.231.104",
        "name": "Handwerk & Holz Zimmermann GmbH",
        "legalSeat": "Muri (AG)",
        "cantonId": "AG",
        "registrationDate": "2026-04-25",
        "status": "ACTIVE",
        "address": {
            "street": "Industriestrasse",
            "houseNumber": "12",
            "swissZipCode": "5630",
            "city": "Muri AG",
        },
    },
    {
        "uid": "CHE-501.884.772",
        "name": "Müller Digital Solutions AG",
        "legalSeat": "Sins",
        "cantonId": "AG",
        "registrationDate": "2026-04-24",
        "status": "ACTIVE",
        "address": {
            "street": "Dorfstrasse",
            "houseNumber": "3",
            "swissZipCode": "5643",
            "city": "Sins",
        },
    },
    {
        "uid": "CHE-503.012.558",
        "name": "Bergmann Immobilien & Verwaltung GmbH",
        "legalSeat": "Villmergen",
        "cantonId": "AG",
        "registrationDate": "2026-04-26",
        "status": "ACTIVE",
        "address": {
            "street": "Hauptstrasse",
            "houseNumber": "47a",
            "swissZipCode": "5612",
            "city": "Villmergen",
        },
    },
]

# ---------------------------------------------------------------------------
# Demo-Lauf
# ---------------------------------------------------------------------------

def run_demo():
    output_dir = os.path.join("letters", "demo")
    os.makedirs(output_dir, exist_ok=True)

    logger.info("=" * 60)
    logger.info("DEMO-LAUF – Zefix Bezirk Muri Checker")
    logger.info("=" * 60)
    logger.info("Simulierte Zefix-Abfrage: %d neue Firmen gefunden.", len(MOCK_NEW_FIRMS))
    logger.info("")

    generated = []

    for firm in MOCK_NEW_FIRMS:
        uid      = firm["uid"]
        name     = firm["name"]
        seat     = firm["legalSeat"]
        reg_date = firm["registrationDate"]
        address  = firm["address"]

        logger.info("Neue Firma erkannt:")
        logger.info("  Name:        %s", name)
        logger.info("  UID:         %s", uid)
        logger.info("  Gemeinde:    %s", seat)
        logger.info("  Eingetragen: %s", reg_date)
        logger.info("  Adresse:     %s %s, %s %s",
                    address["street"], address["houseNumber"],
                    address["swissZipCode"], address["city"])

        uid_safe  = uid.replace("-", "").replace(".", "")
        name_safe = safe_filename(name)
        out_path  = os.path.join(output_dir, f"{uid_safe}_{name_safe}.pdf")

        generate_letter(firm, address, SENDER_INFO, out_path)
        size = os.path.getsize(out_path)
        logger.info("  → Brief generiert: %s  (%d Bytes)", out_path, size)
        logger.info("")
        generated.append(out_path)

    from datetime import date, datetime
    from reporter import send_report, _html_report

    check_time = datetime.now()
    state_preview = {
        "first_run":  False,
        "last_check": check_time.isoformat(),
        "seen_uids": {
            f["uid"]: {
                "name":       f["name"],
                "legal_seat": f["legalSeat"],
                "reg_date":   f["registrationDate"],
                "first_seen": str(date.today()),
                "letter":     True,
                "letter_path": os.path.join(
                    output_dir,
                    f"{f['uid'].replace('-','').replace('.','')}_"
                    f"{safe_filename(f['name'])}.pdf"
                ),
            }
            for f in MOCK_NEW_FIRMS
        },
    }

    # E-Mail HTML-Vorschau speichern
    firms_with_addr = [dict(f, **{"address": f["address"]}) for f in MOCK_NEW_FIRMS]
    html_preview = _html_report(firms_with_addr, check_time)
    preview_path = os.path.join(output_dir, "email_vorschau.html")
    with open(preview_path, "w", encoding="utf-8") as fh:
        fh.write(html_preview)
    logger.info("E-Mail HTML-Vorschau gespeichert: %s", preview_path)

    # E-Mail senden (nur wenn SMTP konfiguriert)
    send_report(firms_with_addr, check_time)

    logger.info("=" * 60)
    logger.info("ZUSAMMENFASSUNG")
    logger.info("=" * 60)
    logger.info("Absender:       %s", SENDER_INFO["company"])
    logger.info("Adresse:        %s, %s", SENDER_INFO["address"], SENDER_INFO["zip_city"])
    logger.info("Kontakt:        %s  |  %s", SENDER_INFO["phone"], SENDER_INFO["email"])
    logger.info("Bericht an:     migmar.nyima@gmail.com (täglich 08:15 Uhr)")
    logger.info("")
    logger.info("Generierte Briefe (%d):", len(generated))
    for p in generated:
        logger.info("  %s", p)
    logger.info("")
    logger.info("Statusdatei (Vorschau):")
    print(json.dumps(state_preview, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_demo()
