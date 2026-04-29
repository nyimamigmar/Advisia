"""
SHAB Checker – tägliche Prüfung auf Neueintragungen (NE) im Kanton Aargau.

Ablauf:
  1. Heutige NE-Einträge aus SHAB laden (Mutationstyp Neueintrag).
  2. Bereits verarbeitete SHAB-IDs aus Statusdatei ausschliessen.
  3. Adresse: aus SHAB-Metadaten, Fallback auf Zefix-Detail-API.
  4. PDF-Gratulationsbrief generieren.
  5. Tagesbericht per E-Mail senden.
  6. Statusdatei aktualisieren.
"""

import json
import logging
import os
import sys
from datetime import date, datetime

from config import CANTON_ID, LETTERS_DIR, SENDER_INFO, STATE_FILE
from letter_generator import generate_letter, safe_filename
from reporter import send_report
from shab_client import get_new_registrations
from zefix_client import get_firm_details

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"last_check": None, "seen_shab_ids": []}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def main() -> None:
    state    = load_state()
    seen_ids = set(state.get("seen_shab_ids", []))
    today    = date.today()

    logger.info("Starte SHAB-Prüfung für Kanton %s (%s) …", CANTON_ID, today)

    all_new = get_new_registrations(canton=CANTON_ID, check_date=today)
    logger.info("SHAB: %d NE-Einträge heute gefunden.", len(all_new))

    new_firms = [f for f in all_new if f.get("shabId") not in seen_ids]
    logger.info("Davon neu (noch nicht verarbeitet): %d", len(new_firms))

    today_dir = os.path.join(LETTERS_DIR, str(today))
    if new_firms:
        os.makedirs(today_dir, exist_ok=True)

    for firm in new_firms:
        name    = firm.get("name", "Unbekannt")
        uid     = firm.get("uid", "")
        seat    = firm.get("legalSeat", "")
        shab_id = firm.get("shabId", "")

        logger.info("  Verarbeite: %s (%s) in %s", name, uid or f"SHAB-{shab_id}", seat)

        address = firm.get("address")
        if not address and uid:
            details = get_firm_details(uid)
            if details:
                address = details.get("address")

        uid_safe  = (uid or shab_id).replace("-", "").replace(".", "")
        name_safe = safe_filename(name)
        out_path  = os.path.join(today_dir, f"{uid_safe}_{name_safe}.pdf")

        try:
            generate_letter(firm, address, SENDER_INFO, out_path)
            logger.info("    Brief erstellt: %s", out_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("    Fehler bei Briefgenerierung für %s: %s", name, exc)

        seen_ids.add(shab_id)

    check_time = datetime.now()
    send_report(new_firms, check_time)

    state["last_check"]    = check_time.isoformat()
    state["seen_shab_ids"] = list(seen_ids)
    save_state(state)
    logger.info("Statusdatei gespeichert: %s", STATE_FILE)

    if new_firms:
        logger.info("FERTIG – %d neue Firma(en) verarbeitet, Briefe in: %s",
                    len(new_firms), today_dir)
    else:
        logger.info("FERTIG – keine neuen Firmen heute.")


if __name__ == "__main__":
    main()
