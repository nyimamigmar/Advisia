"""
Zefix Checker – tägliche Prüfung auf neue Firmen im Bezirk Muri (AG)

Ablauf:
  1. Alle aktiven Firmen im Kanton AG von Zefix laden.
  2. Auf Gemeinden des Bezirks Muri filtern.
  3. Neue Firmen (UID nicht in Statusdatei) erkennen.
  4. Adresse via Zefix-Detail-API abrufen.
  5. PDF-Gratulationsbrief generieren.
  6. Tagesbericht per E-Mail senden.
  7. Statusdatei aktualisieren (für den nächsten Lauf).
"""

import json
import logging
import os
import sys
from datetime import date, datetime, timedelta

from config import (
    BEZIRK_MURI_MUNICIPALITIES,
    FIRST_RUN_DAYS_LOOKBACK,
    LETTERS_DIR,
    SENDER_INFO,
    STATE_FILE,
)
from letter_generator import generate_letter, safe_filename
from reporter import send_report
from zefix_client import get_firm_details, search_firms_in_canton

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"first_run": True, "last_check": None, "seen_uids": {}}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def in_bezirk_muri(firm: dict) -> bool:
    return firm.get("legalSeat", "") in BEZIRK_MURI_MUNICIPALITIES


def parse_registration_date(firm: dict) -> date:
    raw = firm.get("registrationDate")
    if raw:
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            pass
    return date.today()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    state     = load_state()
    first_run = state.get("first_run", True)
    seen_uids: dict = state.get("seen_uids", {})

    logger.info("Starte Zefix-Prüfung für Bezirk Muri …")

    # 1. Alle Firmen im Kanton AG laden
    all_ag = search_firms_in_canton(canton_id="AG", active_only=True)
    logger.info("AG gesamt: %d aktive Firmen gefunden.", len(all_ag))

    # 2. Auf Bezirk Muri filtern
    muri_firms = [f for f in all_ag if in_bezirk_muri(f)]
    logger.info("Bezirk Muri: %d Firmen gefunden.", len(muri_firms))

    # 3. Neue Firmen ermitteln
    cutoff = date.today() - timedelta(days=FIRST_RUN_DAYS_LOOKBACK)
    new_firms: list[dict] = []

    for firm in muri_firms:
        uid = firm.get("uid")
        if not uid:
            continue

        if uid in seen_uids:
            continue

        if first_run:
            reg_date = parse_registration_date(firm)
            if reg_date < cutoff:
                seen_uids[uid] = _seen_entry(firm, letter=False)
                continue

        new_firms.append(firm)

    logger.info("Neue Firmen (Brief wird generiert): %d", len(new_firms))

    # 4 & 5. Details abrufen und Briefe generieren
    today_dir = os.path.join(LETTERS_DIR, str(date.today()))
    if new_firms:
        os.makedirs(today_dir, exist_ok=True)

    for firm in new_firms:
        uid  = firm.get("uid", "")
        name = firm.get("name", "Unbekannt")
        seat = firm.get("legalSeat", "")

        logger.info("  Verarbeite: %s (%s) in %s", name, uid, seat)

        details = get_firm_details(uid)
        address = details.get("address") if details else None

        uid_safe  = uid.replace("-", "").replace(".", "")
        name_safe = safe_filename(name)
        out_path  = os.path.join(today_dir, f"{uid_safe}_{name_safe}.pdf")

        try:
            generate_letter(firm, address, SENDER_INFO, out_path)
            logger.info("    Brief erstellt: %s", out_path)
            seen_uids[uid] = _seen_entry(firm, letter=True, path=out_path)
        except Exception as exc:  # noqa: BLE001
            logger.error("    Fehler bei Briefgenerierung für %s: %s", name, exc)
            seen_uids[uid] = _seen_entry(firm, letter=False)

    # Alle Muri-Firmen als gesehen markieren (auch ohne Brief)
    for firm in muri_firms:
        uid = firm.get("uid")
        if uid and uid not in seen_uids:
            seen_uids[uid] = _seen_entry(firm, letter=False)

    # 6. Tagesbericht per E-Mail senden
    check_time = datetime.now()
    send_report(new_firms, check_time)

    # 7. Status speichern
    state["first_run"]  = False
    state["last_check"] = check_time.isoformat()
    state["seen_uids"]  = seen_uids
    save_state(state)
    logger.info("Statusdatei gespeichert: %s", STATE_FILE)

    if new_firms:
        logger.info("FERTIG – %d neue Firma(en) verarbeitet, Briefe in: %s",
                    len(new_firms), today_dir)
    else:
        logger.info("FERTIG – keine neuen Firmen heute.")


def _seen_entry(firm: dict, *, letter: bool, path: str = "") -> dict:
    entry: dict = {
        "name":       firm.get("name", ""),
        "legal_seat": firm.get("legalSeat", ""),
        "reg_date":   firm.get("registrationDate", ""),
        "first_seen": str(date.today()),
        "letter":     letter,
    }
    if path:
        entry["letter_path"] = path
    return entry


if __name__ == "__main__":
    main()
