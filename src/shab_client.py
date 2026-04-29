"""SHAB (Schweizerisches Handelsamtsblatt) API client.

Ruft Neueintragungen (Mutationstyp NE) aus dem amtlichen Handelsblatt ab.
SHAB veröffentlicht neue Firmeneintragungen direkt am Tag der Eintragung –
es wird daher kein Vergleich mit einem historischen Firmenstamm benötigt.
"""

import logging
import time
from datetime import date
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SHAB_URL = "https://www.shab.ch/api/eshab/entries"
TIMEOUT  = 30
PAGE_SIZE = 100
DELAY     = 0.3   # Sekunden zwischen Seitenabfragen

_session = requests.Session()
_session.headers.update({
    "Accept":     "application/json",
    "User-Agent": "AdvisiaChecker/1.0",
})


def get_new_registrations(canton: str = "AG",
                          check_date: Optional[date] = None) -> list[dict]:
    """Gibt alle NE-Einträge (Neueintragung) aus SHAB für Kanton und Datum zurück."""
    check_date = check_date or date.today()
    date_str   = check_date.isoformat()
    all_firms: list[dict] = []
    page = 0

    while True:
        params = {
            "publicationStates":  "PUBLISHED",
            "cantons":            canton,
            "since":              date_str,
            "until":              date_str,
            "pageRequest.page":   page,
            "pageRequest.size":   PAGE_SIZE,
        }
        try:
            resp = _session.get(SHAB_URL, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            logger.error("SHAB API Fehler (Seite %d): %s", page, exc)
            break

        # Spring-Page-Format: {"content": [...], "totalPages": N, ...}
        if isinstance(data, dict):
            entries     = data.get("content", [])
            total_pages = data.get("totalPages", 1)
        elif isinstance(data, list):
            entries     = data
            total_pages = 1
        else:
            logger.error("Unbekanntes SHAB-Antwortformat: %s", type(data))
            break

        logger.info("SHAB Seite %d/%d: %d Einträge", page + 1, total_pages, len(entries))

        for entry in entries:
            firm = _parse_entry(entry)
            if firm:
                all_firms.append(firm)

        if page + 1 >= total_pages or not entries:
            break
        page += 1
        time.sleep(DELAY)

    logger.info("SHAB gesamt: %d NE-Einträge für %s am %s", len(all_firms), canton, date_str)
    return all_firms


def _parse_entry(entry: dict) -> Optional[dict]:
    """Wandelt einen rohen SHAB-Eintrag in ein Firmen-Dict um.
    Gibt None zurück wenn der Eintrag kein Neueintrag (NE) ist.
    """
    sub_rubric = entry.get("subRubric", "")

    # Nur Handelsregister-Einträge verarbeiten
    if not sub_rubric.upper().startswith("HR"):
        return None

    meta = entry.get("meta") or {}

    # Mutationstyp prüfen – SHAB liefert 'NE' für Neueintrag
    mutation_type = (
        meta.get("mutationType")
        or meta.get("typeOfMutation")
        or meta.get("mutationCode")
        or ""
    ).strip().upper()

    # Wenn Mutationstyp bekannt ist und nicht NE → überspringen
    if mutation_type and mutation_type != "NE":
        return None

    # Firmenname
    name = (
        meta.get("legalName")
        or meta.get("name")
        or entry.get("title", "")
    ).strip()
    if not name:
        return None

    uid        = (meta.get("uid") or "").strip()
    legal_seat = (
        meta.get("legalSeat")
        or meta.get("domicile")
        or meta.get("town")
        or ""
    ).strip()
    pub_date   = entry.get("publicationDate", "")
    shab_id    = str(entry.get("id", ""))

    return {
        "name":             name,
        "uid":              uid,
        "legalSeat":        legal_seat,
        "registrationDate": pub_date,
        "shabId":           shab_id,
        "subRubric":        sub_rubric,
        "address":          _parse_address(meta),
    }


def _parse_address(meta: dict) -> Optional[dict]:
    street   = (meta.get("street")        or meta.get("streetName")   or "").strip()
    house    = (meta.get("houseNumber")   or meta.get("streetNumber") or "").strip()
    zip_code = (meta.get("swissZipCode")  or meta.get("zipCode")      or "").strip()
    city     = (meta.get("city")          or meta.get("town")         or "").strip()
    if not (street or city):
        return None
    return {
        "street":       street,
        "houseNumber":  house,
        "swissZipCode": zip_code,
        "city":         city,
    }
